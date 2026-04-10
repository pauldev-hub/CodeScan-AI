import threading
import time
import uuid

from flask import Blueprint, current_app, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.scan_service import ScanService
from app.tasks.scan_tasks import process_scan_task
from app.utils.constants import (
    MAX_PASTE_CODE_CHARS,
    MAX_TOTAL_UPLOAD_BYTES,
    MAX_UPLOAD_FILE_BYTES,
    RATE_LIMIT_SCAN_MAX_REQUESTS,
    RATE_LIMIT_SCAN_WINDOW_SECONDS,
    SCAN_STATUS_COMPLETE,
)
from app.utils.responses import error_response, success_response
from app.utils.security import enforce_rate_limit
from app.utils.validators import is_allowed_upload, is_valid_github_url


scan_bp = Blueprint("scan", __name__, url_prefix="/api/scan")


def _start_pending_scan_watchdog(scan_id):
    if not current_app.config.get("SCAN_WATCHDOG_INLINE_ON_PENDING", False):
        return

    delay_seconds = max(5, int(current_app.config.get("SCAN_PENDING_WATCHDOG_DELAY_SECONDS", 20)))
    flask_app = current_app._get_current_object()

    def _watch_pending_scan_then_run_inline(target_scan_id):
        time.sleep(delay_seconds)
        with flask_app.app_context():
            from app.models.scan import Scan

            scan = Scan.query.get(target_scan_id)
            if not scan:
                return
            if scan.status != "pending":
                return

            flask_app.logger.warning(
                "Scan watchdog detected pending scan_id=%s after %ss; running inline fallback.",
                target_scan_id,
                delay_seconds,
            )
            try:
                ScanService.process_scan(target_scan_id)
            except Exception:
                flask_app.logger.exception(
                    "Scan watchdog inline fallback failed for scan_id=%s",
                    target_scan_id,
                )

    watcher = threading.Thread(
        target=_watch_pending_scan_then_run_inline,
        args=(scan_id,),
        daemon=True,
        name=f"codescan-watchdog-{scan_id}",
    )
    watcher.start()


def _enqueue_scan(scan):
    try:
        task = process_scan_task.delay(scan.id)
        scan.celery_task_id = task.id
        _start_pending_scan_watchdog(scan.id)
        return True, "celery"
    except Exception as exc:
        if not current_app.config.get("SCAN_INLINE_FALLBACK_ON_QUEUE_FAILURE", False):
            return False, None

        current_app.logger.warning(
            "Falling back to inline scan execution for scan_id=%s after Celery enqueue failure: %s",
            scan.id,
            exc,
        )

        try:
            if current_app.config.get("TESTING", False):
                task = process_scan_task.apply(args=[scan.id], throw=True)
                scan.celery_task_id = task.id
                return True, "inline_fallback"

            flask_app = current_app._get_current_object()
            fallback_task_id = f"inline-{uuid.uuid4()}"

            def _run_inline_scan_background(scan_id):
                with flask_app.app_context():
                    try:
                        ScanService.process_scan(scan_id)
                    except Exception:
                        flask_app.logger.exception(
                            "Inline background fallback failed for scan_id=%s",
                            scan_id,
                        )

            worker = threading.Thread(
                target=_run_inline_scan_background,
                args=(scan.id,),
                daemon=True,
                name=f"codescan-inline-{scan.id}",
            )
            worker.start()

            scan.celery_task_id = fallback_task_id
            return True, "inline_background"
        except Exception as fallback_exc:
            current_app.logger.exception(
                "Inline scan fallback failed for scan_id=%s: %s", scan.id, fallback_exc
            )
            return False, None


@scan_bp.post("/url")
@jwt_required()
def submit_url_scan():
    user_id = int(get_jwt_identity())
    payload = request.get_json(silent=True) or {}
    github_url = (payload.get("github_url") or "").strip()

    if not enforce_rate_limit(
        f"scan:url:{user_id}",
        RATE_LIMIT_SCAN_MAX_REQUESTS,
        RATE_LIMIT_SCAN_WINDOW_SECONDS,
    ):
        return error_response("Scan rate limit exceeded", "rate_limited", 429)

    if not is_valid_github_url(github_url):
        return error_response("Invalid GitHub URL", "validation_error", 400)

    scan = ScanService.create_scan(user_id, "url", github_url)
    enqueued, queue_mode = _enqueue_scan(scan)
    if not enqueued:
        ScanService.mark_scan_enqueue_failed(scan, "Scan worker is unavailable. Please retry.")
        return error_response("Scan worker unavailable", "service_unavailable", 503)

    from app import db

    db.session.commit()

    return success_response(
        {
            "scan_id": scan.api_scan_id,
            "status": scan.status,
            "celery_task_id": scan.celery_task_id,
            "queue_mode": queue_mode,
            "created_at": scan.created_at.isoformat(),
        },
        202,
    )


@scan_bp.post("/paste")
@jwt_required()
def submit_paste_scan():
    user_id = int(get_jwt_identity())
    payload = request.get_json(silent=True) or {}
    code = payload.get("code") or ""
    language = (payload.get("language") or "text").strip()

    if not enforce_rate_limit(
        f"scan:paste:{user_id}",
        RATE_LIMIT_SCAN_MAX_REQUESTS,
        RATE_LIMIT_SCAN_WINDOW_SECONDS,
    ):
        return error_response("Scan rate limit exceeded", "rate_limited", 429)

    if not code.strip():
        return error_response("Code is required", "validation_error", 400)
    if len(code) > MAX_PASTE_CODE_CHARS:
        return error_response("Code too long", "validation_error", 400)

    input_value = f"// language: {language}\n{code}"
    scan = ScanService.create_scan(user_id, "paste", input_value, file_count=1, code_size_bytes=len(code.encode("utf-8")))
    enqueued, queue_mode = _enqueue_scan(scan)
    if not enqueued:
        ScanService.mark_scan_enqueue_failed(scan, "Scan worker is unavailable. Please retry.")
        return error_response("Scan worker unavailable", "service_unavailable", 503)

    from app import db

    db.session.commit()

    return success_response(
        {
            "scan_id": scan.api_scan_id,
            "status": scan.status,
            "celery_task_id": scan.celery_task_id,
            "queue_mode": queue_mode,
        },
        202,
    )


@scan_bp.post("/upload")
@jwt_required()
def submit_upload_scan():
    user_id = int(get_jwt_identity())

    if "file" not in request.files:
        return error_response("At least one file is required", "validation_error", 400)

    files = request.files.getlist("file")
    if not files:
        return error_response("At least one file is required", "validation_error", 400)

    total_size = 0
    chunks = []
    for file_obj in files:
        if not is_allowed_upload(file_obj.filename):
            return error_response("Unsupported file type", "validation_error", 400)

        content = file_obj.read()
        file_size = len(content)
        if file_size > MAX_UPLOAD_FILE_BYTES:
            return error_response("File too large", "validation_error", 400)

        total_size += file_size
        if total_size > MAX_TOTAL_UPLOAD_BYTES:
            return error_response("Total upload size exceeded", "validation_error", 400)

        chunks.append(f"\n# File: {file_obj.filename}\n{content.decode('utf-8', errors='ignore')}")

    combined = "\n".join(chunks)
    scan = ScanService.create_scan(user_id, "upload", combined, file_count=len(files), code_size_bytes=total_size)
    enqueued, queue_mode = _enqueue_scan(scan)
    if not enqueued:
        ScanService.mark_scan_enqueue_failed(scan, "Scan worker is unavailable. Please retry.")
        return error_response("Scan worker unavailable", "service_unavailable", 503)

    from app import db

    db.session.commit()

    return success_response(
        {
            "scan_id": scan.api_scan_id,
            "status": scan.status,
            "file_count": len(files),
            "celery_task_id": scan.celery_task_id,
            "queue_mode": queue_mode,
        },
        202,
    )


@scan_bp.get("/history")
@jwt_required()
def scan_history():
    user_id = int(get_jwt_identity())
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(50, max(1, int(request.args.get("per_page", 10))))

    from app.models.scan import Scan

    pagination = (
        Scan.query.filter_by(user_id=user_id)
        .order_by(Scan.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    items = [
        {
            "scan_id": scan.api_scan_id,
            "status": scan.status,
            "health_score": scan.health_score,
            "total_findings": scan.total_findings,
            "input_type": scan.input_type,
            "created_at": scan.created_at.isoformat() if scan.created_at else None,
            "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
        }
        for scan in pagination.items
    ]

    return success_response(
        {
            "items": items,
            "page": page,
            "per_page": per_page,
            "total": pagination.total,
            "pages": pagination.pages,
        }
    )


@scan_bp.get("/<scan_id>/status")
@jwt_required()
def scan_status(scan_id):
    user_id = int(get_jwt_identity())
    scan = ScanService.get_scan_by_api_id(user_id, scan_id)
    if not scan:
        return error_response("Scan not found", "not_found", 404)
    return success_response(ScanService.build_status_payload(scan))


@scan_bp.get("/<scan_id>/results")
@jwt_required()
def scan_results(scan_id):
    user_id = int(get_jwt_identity())
    scan = ScanService.get_scan_by_api_id(user_id, scan_id)
    if not scan:
        return error_response("Scan not found", "not_found", 404)
    if scan.status != SCAN_STATUS_COMPLETE:
        return error_response("Results not ready", "not_found", 404)
    return success_response(ScanService.build_results_payload(scan))


@scan_bp.post("/<scan_id>/fix-preview")
@jwt_required()
def scan_fix_preview(scan_id):
    user_id = int(get_jwt_identity())
    scan = ScanService.get_scan_by_api_id(user_id, scan_id)
    if not scan:
        return error_response("Scan not found", "not_found", 404)
    if scan.status != SCAN_STATUS_COMPLETE:
        return error_response("Results not ready", "not_found", 404)

    payload = request.get_json(silent=True) or {}
    finding_id = payload.get("finding_id")
    if not finding_id:
        return error_response("finding_id is required", "validation_error", 400)

    try:
        finding_id = int(finding_id)
    except (TypeError, ValueError):
        return error_response("finding_id must be an integer", "validation_error", 400)

    finding = scan.findings.filter_by(id=finding_id).first()
    if not finding:
        return error_response("Finding not found for this scan", "not_found", 404)

    preview = ScanService.build_fix_preview(scan, finding, payload.get("suggestion"))
    return success_response(preview)


@scan_bp.delete("/<scan_id>")
@jwt_required()
def delete_scan(scan_id):
    user_id = int(get_jwt_identity())
    deleted = ScanService.delete_scan(user_id, scan_id)
    if not deleted:
        return error_response("Scan not found", "not_found", 404)
    return success_response({"message": "Scan deleted"}, 200)
