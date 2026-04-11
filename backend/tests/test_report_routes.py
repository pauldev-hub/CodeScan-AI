from app.models.scan import Scan
from app.services.report_service import ReportService


def test_share_scan_rejects_invalid_expiration_days(client, auth_headers):
    headers, user_id = auth_headers(email="report-invalid@example.com")

    scan = Scan(
        user_id=user_id,
        input_type="paste",
        input_value="x=1",
        status="complete",
        api_scan_id="report-scan-id",
    )
    from app import db

    db.session.add(scan)
    db.session.commit()

    response = client.post(
        f"/api/report/{scan.api_scan_id}/share",
        json={"expiration_days": "not-a-number"},
        headers=headers,
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["status"] == "validation_error"


def test_share_scan_rejects_out_of_range_expiration_days(client, auth_headers):
    headers, user_id = auth_headers(email="report-range@example.com")

    scan = Scan(
        user_id=user_id,
        input_type="paste",
        input_value="x=1",
        status="complete",
        api_scan_id="report-scan-range-id",
    )
    from app import db

    db.session.add(scan)
    db.session.commit()

    response = client.post(
        f"/api/report/{scan.api_scan_id}/share",
        json={"expiration_days": 366},
        headers=headers,
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["status"] == "validation_error"


def test_shared_summary_returns_executive_summary(client, auth_headers):
    headers, user_id = auth_headers(email="report-summary@example.com")

    scan = Scan(
        user_id=user_id,
        input_type="paste",
        input_value="password = 'secret'",
        input_language="python",
        status="complete",
        api_scan_id="report-summary-id",
        health_score=64,
    )
    from app import db

    db.session.add(scan)
    db.session.commit()
    report = ReportService.share_scan(scan, user_id, 30)

    response = client.get(f"/api/report/shared/{report.share_uuid}/summary")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["executive_summary"]["headline"]
