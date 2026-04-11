import asyncio

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


@report_bp.get("/shared/<share_uuid>/summary")
def shared_report_summary(share_uuid):
    scan, error_type = ReportService.get_public_report(share_uuid)
    if error_type == "not_found":
        return error_response("Share link not found", "not_found", 404)
    if error_type in {"revoked", "expired"}:
        return error_response("Share link expired or revoked", "gone", 410)

    payload = ScanService.build_results_payload(scan)
    return success_response(
        {
            "scan_id": payload["scan_id"],
            "health_score": payload["health_score"],
            "summary": payload["summary"],
            "executive_summary": payload["executive_summary"],
            "pros": payload["pros"],
            "cons": payload["cons"],
        }
    )


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


@report_bp.post("/<scan_id>/share-card")
@jwt_required()
def generate_share_card(scan_id):
    user_id = int(get_jwt_identity())
    scan = ScanService.get_scan_by_api_id(user_id, scan_id)
    if not scan:
        return error_response("Scan not found", "not_found", 404)
    if scan.status != "complete":
        return error_response("Results not ready", "not_found", 404)

    payload = ScanService.build_results_payload(scan)
    summary = payload["executive_summary"]
    top_risk = summary["top_risks"][0] if summary["top_risks"] else None
    ai_copy = None
    provider_used = "local_fallback"
    try:
        from app.services.ai_provider import get_ai_provider_service

        prompt = (
            "Create a concise share card summary for a code scan. Return plain text only in 2 short sentences.\n"
            f"Headline: {summary['headline']}\n"
            f"Verdict: {summary['verdict']}\n"
            f"Plain English: {summary['plain_english']}\n"
            f"Top risk: {top_risk['title'] if top_risk else 'No top risk'}\n"
        )
        ai_copy, provider_used = asyncio.run(
            get_ai_provider_service().generate_text(
                user_prompt="Write a stakeholder-friendly score share card.",
                system_prompt=prompt,
                preferred_order=["groq", "gemini"],
            )
        )
    except Exception:
        ai_copy = f"{summary['headline']}. {summary['plain_english']}"

    return success_response(
        {
            "scan_id": payload["scan_id"],
            "headline": summary["headline"],
            "verdict": summary["verdict"],
            "plain_english": summary["plain_english"],
            "top_risk": top_risk,
            "ai_copy": ai_copy,
            "provider_used": provider_used,
        }
    )
