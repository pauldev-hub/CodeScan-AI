from app.models.scan import Scan
from app.services.scan_service import ScanService


def test_persist_analysis_stores_summary_arrays(app_instance, create_user):
    user_id = create_user(email="summary-store@example.com")

    from app import db

    scan = Scan(
        user_id=user_id,
        input_type="paste",
        input_value="print('hello')",
        status="running",
        api_scan_id="summary-scan-id",
    )
    db.session.add(scan)
    db.session.commit()

    analysis = {
        "issues": [],
        "health_score": 91,
        "pros": ["Has clear error handling"],
        "cons": ["Missing auth checks"],
        "refactor_suggestions": ["Extract scanner service"],
    }

    ScanService._persist_analysis(scan, analysis)
    db.session.commit()

    assert scan.pros_json == '["Has clear error handling"]'
    assert scan.cons_json == '["Missing auth checks"]'
    assert scan.refactor_suggestions_json == '["Extract scanner service"]'


def test_build_results_payload_returns_summary_arrays(app_instance, create_user):
    user_id = create_user(email="summary-read@example.com")

    from app import db

    scan = Scan(
        user_id=user_id,
        input_type="paste",
        input_value="print('hello')",
        status="complete",
        api_scan_id="summary-read-id",
        pros_json='["Strong validation"]',
        cons_json='["Weak token hygiene"]',
        refactor_suggestions_json='["Split route and service"]',
    )
    db.session.add(scan)
    db.session.commit()

    payload = ScanService.build_results_payload(scan)

    assert payload["pros"] == ["Strong validation"]
    assert payload["cons"] == ["Weak token hygiene"]
    assert payload["refactor_suggestions"] == ["Split route and service"]
