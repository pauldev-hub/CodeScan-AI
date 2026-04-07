from flask import Blueprint, Response, send_file
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.export_service import ExportService
from app.services.scan_service import ScanService
from app.utils.constants import SCAN_STATUS_COMPLETE
from app.utils.responses import error_response


export_bp = Blueprint("export", __name__, url_prefix="/api/export")


def _get_completed_scan(user_id, scan_id):
    scan = ScanService.get_scan_by_api_id(user_id, scan_id)
    if not scan:
        return None, error_response("Scan not found", "not_found", 404)
    if scan.status != SCAN_STATUS_COMPLETE:
        return None, error_response("Results not ready", "not_found", 404)
    return scan, None


@export_bp.get("/<scan_id>/json")
@jwt_required()
def export_json(scan_id):
    user_id = int(get_jwt_identity())
    scan, error = _get_completed_scan(user_id, scan_id)
    if error:
        return error
    content = ExportService.build_json(scan)
    return Response(
        content,
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename=scan-{scan_id}.json"},
    )


@export_bp.get("/<scan_id>/csv")
@jwt_required()
def export_csv(scan_id):
    user_id = int(get_jwt_identity())
    scan, error = _get_completed_scan(user_id, scan_id)
    if error:
        return error
    content = ExportService.build_csv(scan)
    return Response(
        content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=scan-{scan_id}.csv"},
    )


@export_bp.get("/<scan_id>/md")
@jwt_required()
def export_md(scan_id):
    user_id = int(get_jwt_identity())
    scan, error = _get_completed_scan(user_id, scan_id)
    if error:
        return error
    content = ExportService.build_md(scan)
    return Response(
        content,
        mimetype="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=scan-{scan_id}.md"},
    )


@export_bp.get("/<scan_id>/pdf")
@jwt_required()
def export_pdf(scan_id):
    user_id = int(get_jwt_identity())
    scan, error = _get_completed_scan(user_id, scan_id)
    if error:
        return error
    pdf_buffer = ExportService.build_pdf(scan)
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"scan-{scan_id}.pdf",
    )
