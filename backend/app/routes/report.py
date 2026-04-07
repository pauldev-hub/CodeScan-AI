from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.report_service import ReportService
from app.services.scan_service import ScanService
from app.utils.responses import error_response, success_response


report_bp = Blueprint("report", __name__, url_prefix="/api/report")


@report_bp.post("/<scan_id>/share")
@jwt_required()
def share_scan(scan_id):
    user_id = int(get_jwt_identity())
    payload = request.get_json(silent=True) or {}
    raw_expiration_days = payload.get("expiration_days", 30)
    try:
        expiration_days = int(raw_expiration_days)
    except (TypeError, ValueError):
        return error_response("expiration_days must be an integer", "validation_error", 400)
    if expiration_days < 1 or expiration_days > 365:
        return error_response("expiration_days must be between 1 and 365", "validation_error", 400)

    scan = ScanService.get_scan_by_api_id(user_id, scan_id)
    if not scan:
        return error_response("Scan not found", "not_found", 404)

    report = ReportService.share_scan(scan, user_id, expiration_days)
    return success_response(
        {
            "share_uuid": report.share_uuid,
            "share_link": f"/api/report/shared/{report.share_uuid}",
            "is_public": report.is_public,
            "expires_at": report.expires_at.isoformat() if report.expires_at else None,
        }
    )


@report_bp.get("/shared/<share_uuid>")
def shared_report(share_uuid):
    scan, error_type = ReportService.get_public_report(share_uuid)
    if error_type == "not_found":
        return error_response("Share link not found", "not_found", 404)
    if error_type in {"revoked", "expired"}:
        return error_response("Share link expired or revoked", "gone", 410)

    return success_response(ScanService.build_results_payload(scan))


@report_bp.post("/<scan_id>/revoke")
@jwt_required()
def revoke_share(scan_id):
    user_id = int(get_jwt_identity())
    scan = ScanService.get_scan_by_api_id(user_id, scan_id)
    if not scan:
        return error_response("Scan not found", "not_found", 404)

    report = ReportService.revoke_share(scan)
    if not report:
        return error_response("Share link not found", "not_found", 404)

    return success_response({"message": "Share link revoked"})
