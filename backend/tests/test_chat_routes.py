from app.models.chat import ChatConversation, ChatMessage
from app.models.scan import Finding, Scan
from app.services.chat_service import ChatService
from app.utils.constants import SCAN_STATUS_COMPLETE
from unittest.mock import patch


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


def test_chat_message_feedback_update(client, auth_headers, app_instance):
    headers, _user_id = auth_headers(email="chat-feedback@example.com")

    create_response = client.post("/api/chat/conversations", json={"title": "Feedback thread"}, headers=headers)
    assert create_response.status_code == 201
    conversation = create_response.get_json()

    with app_instance.app_context():
        from app import db

        assistant_message = ChatMessage(
            conversation_id=conversation["id"],
            role="assistant",
            content="Try using parameterized queries.",
        )
        db.session.add(assistant_message)
        db.session.commit()
        message_id = assistant_message.id

    like_response = client.patch(
        f"/api/chat/conversations/{conversation['id']}/messages/{message_id}/feedback",
        json={"feedback": "like"},
        headers=headers,
    )
    assert like_response.status_code == 200
    assert like_response.get_json()["message"]["feedback"] == "like"

    clear_response = client.patch(
        f"/api/chat/conversations/{conversation['id']}/messages/{message_id}/feedback",
        json={"feedback": None},
        headers=headers,
    )
    assert clear_response.status_code == 200
    assert clear_response.get_json()["message"]["feedback"] is None


def test_local_fallback_handles_weather_queries(client, auth_headers):
    headers, user_id = auth_headers(email="chat-weather@example.com")
    create_response = client.post("/api/chat/conversations", json={"title": "General"}, headers=headers)
    conversation = create_response.get_json()

    with client.application.app_context():
        stored = ChatConversation.query.filter_by(id=conversation["id"], user_id=user_id).first()
        reply = ChatService.build_local_fallback_reply(stored, "what is the weather today?")
        assert "weather" in reply.lower()
        assert "city" in reply.lower()


def test_local_fallback_handles_news_queries(client, auth_headers):
    headers, user_id = auth_headers(email="chat-news@example.com")
    create_response = client.post("/api/chat/conversations", json={"title": "General"}, headers=headers)
    conversation = create_response.get_json()

    with client.application.app_context():
        stored = ChatConversation.query.filter_by(id=conversation["id"], user_id=user_id).first()
        reply = ChatService.build_local_fallback_reply(stored, "give me some good news")
        assert "news" in reply.lower()
        assert "summarize" in reply.lower() or "briefing" in reply.lower()


def test_local_tool_code_search_uses_scan_context(client, auth_headers, app_instance):
    headers, user_id = auth_headers(email="chat-code-search@example.com")

    with app_instance.app_context():
        from app import db

        scan = Scan(
            user_id=user_id,
            input_type="upload",
            input_value="\n# File: src/auth.py\ndef login_user(token):\n    return token\n",
            status=SCAN_STATUS_COMPLETE,
            api_scan_id="code-search-scan-id",
            health_score=72,
        )
        db.session.add(scan)
        db.session.flush()
        conversation = ChatConversation(user_id=user_id, title="Search", scan_id=scan.id)
        db.session.add(conversation)
        db.session.commit()

        reply = ChatService.try_local_tool_response(conversation, "search code for login_user")
        assert reply is not None
        assert "src/auth.py" in reply
        assert "login_user" in reply


def test_local_tool_roast_mode_uses_findings(client, auth_headers, app_instance):
    headers, user_id = auth_headers(email="chat-roast@example.com")

    with app_instance.app_context():
        from app import db

        scan = Scan(
            user_id=user_id,
            input_type="paste",
            input_value="query = f\"SELECT * FROM users WHERE id = {user_input}\"",
            status=SCAN_STATUS_COMPLETE,
            api_scan_id="roast-scan-id",
            health_score=33,
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
        conversation = ChatConversation(user_id=user_id, title="Roast", scan_id=scan.id)
        db.session.add(conversation)
        db.session.commit()

        reply = ChatService.try_local_tool_response(conversation, "roast this code gently")
        assert reply is not None
        assert "roast mode" in reply.lower()
        assert "Potential SQL injection" in reply


def test_build_chat_prompt_includes_memory_notes(client, auth_headers, app_instance):
    headers, user_id = auth_headers(email="chat-memory@example.com")

    first = client.post("/api/chat/conversations", json={"title": "Memory A"}, headers=headers).get_json()
    second = client.post("/api/chat/conversations", json={"title": "Memory B"}, headers=headers).get_json()

    with app_instance.app_context():
        from app import db

        db.session.add(
            ChatMessage(
                conversation_id=first["id"],
                role="user",
                content="my name is alex and i live in lagos",
            )
        )
        db.session.add(
            ChatMessage(
                conversation_id=first["id"],
                role="user",
                content="i prefer concise answers",
            )
        )
        db.session.commit()

        target_conversation = ChatConversation.query.filter_by(id=second["id"], user_id=user_id).first()
        assert target_conversation is not None

        _system_prompt, user_prompt = ChatService.build_chat_prompt(target_conversation, "help me fix this bug")

        lowered = user_prompt.lower()
        assert "memory notes from earlier conversations with this user" in lowered
        assert "user name preference: alex" in lowered
        assert "user location context: lagos" in lowered
        assert "user preference: i prefer concise answers" in lowered
        assert "memory signals are currently sparse" not in lowered


def test_local_fallback_rewrites_buggy_code_request(client, auth_headers, app_instance):
    headers, user_id = auth_headers(email="chat-rewrite@example.com")
    create_response = client.post("/api/chat/conversations", json={"title": "Rewrite"}, headers=headers)
    conversation = create_response.get_json()

    buggy_code = """
import os
import pickle
import sqlite3
import subprocess
from flask import Flask, request

app = Flask(__name__)

@app.post('/login')
def login():
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    conn = sqlite3.connect('users.db')
    cur = conn.cursor()
    cur.execute(f\"SELECT id FROM users WHERE username='{username}' AND password='{password}'\")
    return {'ok': True}

@app.post('/run')
def run():
    cmd = request.form.get('cmd', '')
    return {'output': subprocess.check_output(cmd, shell=True, text=True)}

@app.post('/import')
def import_data():
    payload = request.files['file'].read()
    obj = pickle.loads(payload)
    return {'saved': str(obj)}
""".strip()

    with app_instance.app_context():
        convo = ChatConversation.query.filter_by(id=conversation["id"], user_id=user_id).first()
        assert convo is not None
        ChatMessage.query.filter_by(conversation_id=convo.id).delete()
        from app import db

        db.session.add(ChatMessage(conversation_id=convo.id, role="user", content=buggy_code))
        db.session.commit()

        reply = ChatService.build_local_fallback_reply(convo, "rewrite full code and fix security bugs")
        lowered = reply.lower()
        assert "rewritten code" in lowered
        assert "@app.post('/login')" in reply
        assert "debug=false" in lowered


@patch("app.services.ai_provider.get_ai_provider_service")
def test_socket_chat_uses_fallback_when_provider_returns_blank(mock_get_provider, app_instance, client, auth_headers, socket_client):
    class _BlankProvider:
        async def generate_text(self, **kwargs):
            del kwargs
            return "   ", "groq"

    mock_get_provider.return_value = _BlankProvider()

    headers, _user_id = auth_headers(email="chat-blank-provider@example.com")
    create_response = client.post("/api/chat/conversations", json={"title": "Blank provider"}, headers=headers)
    conversation = create_response.get_json()
    token = headers["Authorization"].split(" ", 1)[1]
    sock = socket_client(token)

    sock.emit("chat_start", {"conversation_id": conversation["id"]})
    sock.emit("chat_message", {"conversation_id": conversation["id"], "message": "rewrite this code"})
    received = sock.get_received()

    done_events = [packet for packet in received if packet["name"] == "chat_response_done"]
    assert done_events
    payload = done_events[-1]["args"][0]
    assert payload["provider_used"] == "local_fallback"
    assert payload["full_content"].strip()
