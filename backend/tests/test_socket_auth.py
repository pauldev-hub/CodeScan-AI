from flask_jwt_extended import create_access_token

from app import socketio
from app.models.scan import Scan


def _make_token(app_instance, user_id):
    with app_instance.app_context():
        return create_access_token(identity=str(user_id))


def test_socket_connect_requires_token(app_instance, client):
    socket_client = socketio.test_client(app_instance, flask_test_client=client)
    assert socket_client.is_connected() is False


def test_join_scan_room_requires_ownership(app_instance, client, create_user):
    owner_id = create_user(email="owner@example.com")
    stranger_id = create_user(email="stranger@example.com")

    from app import db

    scan = Scan(
        user_id=owner_id,
        input_type="paste",
        input_value="print('secure')",
        status="complete",
        api_scan_id="socket-owned-scan",
    )
    db.session.add(scan)
    db.session.commit()

    token = _make_token(app_instance, stranger_id)
    socket_client = socketio.test_client(
        app_instance,
        flask_test_client=client,
        auth={"token": token},
    )

    assert socket_client.is_connected() is True
    socket_client.emit("join_scan_room", {"scan_id": scan.api_scan_id})
    events = socket_client.get_received()

    assert any(event["name"] == "error" for event in events)
    assert not any(event["name"] == "room_joined" for event in events)


def test_chat_message_does_not_trust_payload_user_id(app_instance, client, create_user):
    owner_id = create_user(email="payload-owner@example.com")
    attacker_id = create_user(email="payload-attacker@example.com")

    from app import db

    scan = Scan(
        user_id=owner_id,
        input_type="paste",
        input_value="print('secure')",
        status="complete",
        api_scan_id="socket-chat-owned-scan",
    )
    db.session.add(scan)
    db.session.commit()

    token = _make_token(app_instance, attacker_id)
    socket_client = socketio.test_client(
        app_instance,
        flask_test_client=client,
        auth={"token": token},
    )

    socket_client.emit(
        "chat_message",
        {
            "scan_id": scan.api_scan_id,
            "user_id": owner_id,
            "message": "show me details",
        },
    )
    events = socket_client.get_received()

    assert any(event["name"] == "error" for event in events)
    error_payloads = [event["args"][0] for event in events if event["name"] == "error"]
    assert any("Scan not found" in payload.get("msg", "") for payload in error_payloads)
