from app.models.scan import Scan


def test_export_requires_completed_scan(client, auth_headers):
    headers, user_id = auth_headers(email="export-user@example.com")

    from app import db

    scan = Scan(
        user_id=user_id,
        input_type="paste",
        input_value="print('x')",
        status="pending",
        api_scan_id="export-pending-scan",
    )
    db.session.add(scan)
    db.session.commit()

    response = client.get(f"/api/export/{scan.api_scan_id}/json", headers=headers)

    assert response.status_code == 404
    payload = response.get_json()
    assert payload["status"] == "not_found"
