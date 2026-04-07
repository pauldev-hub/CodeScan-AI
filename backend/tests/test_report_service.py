from app.models.scan import Scan
from app.services.report_service import ReportService


def test_share_and_revoke_report_flow(app_instance, create_user):
    user_id = create_user(email="report-service@example.com")

    from app import db

    scan = Scan(
        user_id=user_id,
        input_type="paste",
        input_value="print('x')",
        status="complete",
        api_scan_id="report-service-scan",
    )
    db.session.add(scan)
    db.session.commit()

    report = ReportService.share_scan(scan, user_id, expiration_days=5)
    assert report.is_public is True
    assert report.share_uuid

    public_scan, error_type = ReportService.get_public_report(report.share_uuid)
    assert error_type is None
    assert public_scan.id == scan.id

    revoked = ReportService.revoke_share(scan)
    assert revoked is not None
    assert revoked.is_public is False
