from unittest.mock import patch

from sqlalchemy.exc import OperationalError

from app.models.scan import Finding, Scan
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


def test_submit_url_scan_uses_inline_fallback_when_enabled(client, auth_headers):
    headers, _user = auth_headers(email="scan-inline-fallback@example.com")
    client.application.config["SCAN_INLINE_FALLBACK_ON_QUEUE_FAILURE"] = True

    class DummyTask:
        id = "inline-task-456"

    with patch("app.routes.scan.enforce_rate_limit", return_value=True), patch(
        "app.routes.scan.process_scan_task.delay", side_effect=RuntimeError("broker down")
    ), patch("app.routes.scan.process_scan_task.apply", return_value=DummyTask()):
        response = client.post(
            "/api/scan/url",
            json={"github_url": "https://github.com/octocat/Hello-World"},
            headers=headers,
        )

    assert response.status_code == 202
    payload = response.get_json()
    assert payload["celery_task_id"] == "inline-task-456"
    assert payload["queue_mode"] == "inline_fallback"


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
    assert payload["queue_mode"] == "celery"


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
    assert payload["input_language"] == "text"
    assert "tabs" in payload
    assert "overview" in payload["tabs"]


def test_submit_paste_scan_persists_input_language(client, auth_headers):
    headers, _user = auth_headers(email="scan-language@example.com")

    class DummyTask:
        id = "task-paste-123"

    with patch("app.routes.scan.enforce_rate_limit", return_value=True), patch(
        "app.routes.scan.process_scan_task.delay", return_value=DummyTask()
    ):
        response = client.post(
            "/api/scan/paste",
            json={"code": "print('hi')", "language": "python"},
            headers=headers,
        )

    assert response.status_code == 202
    scan = Scan.query.order_by(Scan.id.desc()).first()
    assert scan.input_language == "python"


def test_fix_preview_returns_finding_based_preview(client, auth_headers):
    headers, user_id = auth_headers(email="scan-fix-preview@example.com")

    scan = Scan(
        user_id=user_id,
        input_type="paste",
        input_value="print('hi')",
        status=SCAN_STATUS_COMPLETE,
        api_scan_id="fix-preview-scan-id",
    )
    from app import db

    db.session.add(scan)
    db.session.flush()

    finding = Finding(
        scan_id=scan.id,
        title="Unsanitized input",
        description="desc",
        plain_english="plain",
        severity="high",
        category="security",
        file_path="app.py",
        line_number=12,
        code_snippet="query = f\"SELECT * FROM users WHERE id = {user_input}\"",
        fix_suggestion="Use parameterized queries.",
        exploit_risk=90,
    )
    db.session.add(finding)
    db.session.commit()

    response = client.post(
        f"/api/scan/{scan.api_scan_id}/fix-preview",
        json={"finding_id": finding.id},
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["finding_id"] == finding.id
    assert "SELECT * FROM users WHERE id = %s" in payload["after"]
    assert payload["source"] == "generated_fix_preview"
    assert payload["language"] == "python"
    assert payload["change_summary"]
    assert payload["diff_stats"]["changed_lines"] >= 1


def test_fix_preview_requires_finding_id(client, auth_headers):
    headers, user_id = auth_headers(email="scan-fix-validation@example.com")

    scan = Scan(
        user_id=user_id,
        input_type="paste",
        input_value="print('hi')",
        status=SCAN_STATUS_COMPLETE,
        api_scan_id="fix-preview-validation-id",
    )
    from app import db

    db.session.add(scan)
    db.session.commit()

    response = client.post(f"/api/scan/{scan.api_scan_id}/fix-preview", json={}, headers=headers)

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["status"] == "validation_error"


def test_scan_history_returns_migration_required_on_schema_mismatch(client, auth_headers):
    headers, _user = auth_headers(email="scan-history-migration@example.com")

    with patch.object(
        type(Scan.query),
        "paginate",
        side_effect=OperationalError("SELECT scans.input_language FROM scans", {}, Exception("no such column: scans.input_language")),
    ):
        response = client.get("/api/scan/history?page=1&per_page=8", headers=headers)

    assert response.status_code == 500
    payload = response.get_json()
    assert payload["status"] == "migration_required"
    assert "migration" in payload["message"].lower()


def test_regenerate_learn_content_returns_structured_payload(client, auth_headers):
    headers, user_id = auth_headers(email="scan-learn@example.com")

    scan = Scan(
        user_id=user_id,
        input_type="paste",
        input_value="print('hi')",
        status=SCAN_STATUS_COMPLETE,
        api_scan_id="learn-scan-id",
        health_score=91,
    )
    from app import db

    db.session.add(scan)
    db.session.flush()
    db.session.add(
        Finding(
            scan_id=scan.id,
            title="Unsanitized input",
            description="desc",
            plain_english="plain",
            severity="high",
            category="security",
            file_path="app.py",
            line_number=12,
            code_snippet="danger(user_input)",
            fix_suggestion="Validate user input",
            exploit_risk=90,
        )
    )
    db.session.commit()

    response = client.post(f"/api/scan/{scan.api_scan_id}/learn/regenerate", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["micro_lessons"]
    assert payload["quiz"]
    assert payload["fix_it_yourself"]
    assert payload["debate_starters"]
    assert payload["hacker_challenges"]
    assert payload["code_roasts"]
    assert payload["live_attack_labs"]
    assert payload["source"]
