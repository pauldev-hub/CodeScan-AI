from unittest.mock import patch

from app.models.scan import Scan
from app.utils.constants import SCAN_STATUS_COMPLETE


def test_submit_url_scan_enqueue_failure_returns_503(client, auth_headers):
    headers, _user = auth_headers(email="scan-enqueue@example.com")

    with patch("app.routes.scan.enforce_rate_limit", return_value=True), patch(
        "app.routes.scan.process_scan_task.delay", side_effect=RuntimeError("broker down")
    ):
        response = client.post(
            "/api/scan/url",
            json={"github_url": "https://github.com/octocat/Hello-World"},
            headers=headers,
        )

    assert response.status_code == 503
    payload = response.get_json()
    assert payload["status"] == "service_unavailable"

    scan = Scan.query.order_by(Scan.id.desc()).first()
    assert scan is not None
    assert scan.status == "error"
    assert "worker" in (scan.error_message or "").lower()


def test_submit_url_scan_accepted_with_task_id(client, auth_headers):
    headers, _user = auth_headers(email="scan-success@example.com")

    class DummyTask:
        id = "task-123"

    with patch("app.routes.scan.enforce_rate_limit", return_value=True), patch(
        "app.routes.scan.process_scan_task.delay", return_value=DummyTask()
    ):
        response = client.post(
            "/api/scan/url",
            json={"github_url": "https://github.com/octocat/Hello-World"},
            headers=headers,
        )

    assert response.status_code == 202
    payload = response.get_json()
    assert payload["celery_task_id"] == "task-123"


def test_results_include_summary_arrays(client, auth_headers):
    headers, user_id = auth_headers(email="scan-results@example.com")

    scan = Scan(
        user_id=user_id,
        input_type="paste",
        input_value="print('hi')",
        status=SCAN_STATUS_COMPLETE,
        api_scan_id="results-scan-id",
        health_score=88,
        pros_json='["Input validation exists"]',
        cons_json='["No rate limiting on endpoint"]',
        refactor_suggestions_json='["Extract auth checks"]',
    )
    from app import db

    db.session.add(scan)
    db.session.commit()

    response = client.get(f"/api/scan/{scan.api_scan_id}/results", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["pros"] == ["Input validation exists"]
    assert payload["cons"] == ["No rate limiting on endpoint"]
    assert payload["refactor_suggestions"] == ["Extract auth checks"]
