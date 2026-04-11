from app.models.chat import ChatConversation, ChatMessage
from app.models.scan import Finding, Scan
from app.utils.constants import SCAN_STATUS_COMPLETE


def test_chat_conversation_crud(client, auth_headers):
    headers, _user_id = auth_headers(email="chat-crud@example.com")

    create_response = client.post("/api/chat/conversations", json={"title": "Security thread"}, headers=headers)
    assert create_response.status_code == 201
    conversation = create_response.get_json()
    assert conversation["title"] == "Security thread"

    list_response = client.get("/api/chat/conversations", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.get_json()["items"]) == 1

    get_response = client.get(f"/api/chat/conversations/{conversation['id']}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.get_json()["id"] == conversation["id"]

    delete_response = client.delete(f"/api/chat/conversations/{conversation['id']}", headers=headers)
    assert delete_response.status_code == 200


def test_chat_message_socket_flow_persists_messages(app_instance, client, auth_headers, socket_client):
    headers, user_id = auth_headers(email="chat-socket@example.com")

    with app_instance.app_context():
        from app import db

        scan = Scan(
            user_id=user_id,
            input_type="paste",
            input_value="query = f\"SELECT * FROM users WHERE id = {user_input}\"",
            status=SCAN_STATUS_COMPLETE,
            api_scan_id="chat-scan-id",
            health_score=42,
        )
        db.session.add(scan)
        db.session.flush()
        db.session.add(
            Finding(
                scan_id=scan.id,
                title="Potential SQL injection",
                description="desc",
                plain_english="plain",
                severity="critical",
                category="security",
                file_path="app.py",
                line_number=3,
                code_snippet="query = ...",
                fix_suggestion="Use parameterized queries",
                exploit_risk=95,
            )
        )
        db.session.commit()

    create_response = client.post("/api/chat/conversations", json={"title": "Scan chat", "scan_id": "chat-scan-id"}, headers=headers)
    conversation = create_response.get_json()
    token = headers["Authorization"].split(" ", 1)[1]
    sock = socket_client(token)

    sock.emit("chat_start", {"conversation_id": conversation["id"], "scan_id": "chat-scan-id"})
    sock.emit("chat_message", {"conversation_id": conversation["id"], "scan_id": "chat-scan-id", "message": "What should I fix first?"})
    received = sock.get_received()

    assert any(packet["name"] == "chat_response_done" for packet in received)

    with app_instance.app_context():
        stored_conversation = ChatConversation.query.get(conversation["id"])
        assert stored_conversation is not None
        stored_messages = ChatMessage.query.filter_by(conversation_id=conversation["id"]).all()
        assert len(stored_messages) >= 2


def test_health_endpoint_exposes_runtime_status(client):
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.get_json()
    assert "redis" in payload
    assert "celery" in payload
    assert "ai_providers" in payload
