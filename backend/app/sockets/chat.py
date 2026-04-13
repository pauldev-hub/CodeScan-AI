import asyncio
import logging
from typing import Optional

from flask import request, session
from flask_jwt_extended import decode_token
from flask_socketio import disconnect, emit, join_room

from app.models.scan import Scan
from app.services.chat_service import ChatService
from app.utils.security import get_session_revoke_marker


logger = logging.getLogger(__name__)


class ChatSessionGuard:
    @staticmethod
    def is_session_revoked(user_id):
        return get_session_revoke_marker(str(user_id)) is not None


def register_socket_handlers(socketio):
    @socketio.on("connect")
    def on_connect(auth=None):
        token = None
        if isinstance(auth, dict):
            token = auth.get("token") or auth.get("access_token")
        if not token:
            token = request.args.get("token")

        if not token:
            emit("error", {"msg": "Authentication token required"})
            return False

        try:
            decoded = decode_token(token)
            if decoded.get("type") != "access":
                emit("error", {"msg": "Access token required"})
                return False

            user_id = str(decoded.get("sub") or "").strip()
            if not user_id:
                emit("error", {"msg": "Invalid token subject"})
                return False
            if ChatSessionGuard.is_session_revoked(user_id):
                emit("error", {"msg": "Session revoked. Please login again."})
                return False
            session["user_id"] = user_id
        except Exception:
            emit("error", {"msg": "Invalid token"})
            return False
        return True

    @socketio.on("join_scan_room")
    def join_scan_room(payload):
        payload = payload or {}
        scan_id = str(payload.get("scan_id") or "").strip()
        user_id = _get_authenticated_user_id()
        if not scan_id or user_id is None:
            emit("error", {"msg": "scan_id is required"})
            return
        scan = _resolve_scan(scan_id, user_id)
        if not scan:
            emit("error", {"msg": "Scan not found"})
            return
        room_name = str(scan.api_scan_id)
        join_room(room_name)
        emit("room_joined", {"scan_id": room_name})

    @socketio.on("chat_start")
    def chat_start(payload):
        payload = payload or {}
        user_id = _get_authenticated_user_id()
        if user_id is None:
            emit("chat_error", {"error": "Unauthorized"})
            disconnect()
            return

        conversation_id = payload.get("conversation_id")
        scan_id = payload.get("scan_id")
        if conversation_id:
            conversation = ChatService.get_conversation(user_id, int(conversation_id))
        else:
            conversation = ChatService.create_conversation(user_id=user_id, scan_api_id=scan_id)

        if not conversation:
            emit("chat_error", {"error": "Conversation not found"})
            return

        room_name = _conversation_room(conversation.id)
        join_room(room_name)
        emit("room_joined", {"conversation_id": conversation.id, "room": room_name})

    @socketio.on("join_chat")
    def join_chat(payload):
        chat_start(payload)

    @socketio.on("chat_message")
    def chat_message(payload):
        payload = payload or {}
        user_id = _get_authenticated_user_id()
        if user_id is None:
            emit("chat_error", {"error": "Unauthorized"})
            disconnect()
            return
        if ChatSessionGuard.is_session_revoked(str(user_id)):
            emit("chat_error", {"error": "Session revoked. Please login again."})
            disconnect()
            return

        message = (payload.get("message") or "").strip()
        conversation_id = payload.get("conversation_id")
        scan_id = payload.get("scan_id")
        if not message:
            emit("chat_error", {"error": "Message is required"})
            return

        conversation = None
        if conversation_id:
            conversation = ChatService.get_conversation(user_id, int(conversation_id))
        if conversation is None:
            conversation = ChatService.create_conversation(user_id=user_id, scan_api_id=scan_id)

        if not conversation:
            emit("chat_error", {"error": "Conversation not found"})
            return

        room_name = _conversation_room(conversation.id)
        join_room(room_name)
        user_message = ChatService.add_message(conversation, "user", message)
        emit(
            "chat_message_saved",
            {"conversation_id": conversation.id, "message": ChatService.serialize_message(user_message)},
            room=room_name,
        )

        local_tool_reply = ChatService.try_local_tool_response(conversation, message)
        if local_tool_reply:
            provider_used = "local_tool"
            text = ChatService.normalize_assistant_reply(local_tool_reply)
            assistant_message = ChatService.add_message(conversation, "assistant", text)
            chunks = _chunk_text(text)
            for chunk in chunks:
                emit(
                    "chat_response_chunk",
                    {"conversation_id": conversation.id, "chunk": chunk, "provider_used": provider_used},
                    room=room_name,
                )
            emit(
                "chat_response_done",
                {
                    "conversation_id": conversation.id,
                    "message_id": assistant_message.id,
                    "full_content": text,
                    "provider_used": provider_used,
                },
                room=room_name,
            )
            return

        try:
            system_prompt, user_prompt = ChatService.build_chat_prompt(conversation, message)
            from app.services.ai_provider import get_ai_provider_service

            text, provider_used = asyncio.run(
                get_ai_provider_service().generate_text(
                    user_prompt=user_prompt,
                    system_prompt=system_prompt,
                    preferred_order=["gemini", "groq", "cerebras", "llama"],
                )
            )
        except Exception as exc:
            logger.warning(
                "Chat provider fallback activated. conversation_id=%s error=%s",
                conversation.id,
                exc,
            )
            provider_used = "local_fallback"
            text = ChatService.build_local_fallback_reply(conversation, message)

        text = ChatService.normalize_assistant_reply(text)
        if not text.strip():
            provider_used = "local_fallback"
            text = ChatService.build_local_fallback_reply(conversation, message)
            text = ChatService.normalize_assistant_reply(text)

        assistant_message = ChatService.add_message(conversation, "assistant", text)
        chunks = _chunk_text(text)
        for chunk in chunks:
            emit(
                "chat_response_chunk",
                {"conversation_id": conversation.id, "chunk": chunk, "provider_used": provider_used},
                room=room_name,
            )
        emit(
            "chat_response_done",
            {
                "conversation_id": conversation.id,
                "message_id": assistant_message.id,
                "full_content": text,
                "provider_used": provider_used,
            },
            room=room_name,
        )


def emit_scan_complete(scan, provider_used=None):
    from app import socketio

    payload = {
        "scan_id": scan.api_scan_id,
        "status": "complete",
        "health_score": scan.health_score,
        "ai_provider_used": provider_used,
    }
    socketio.emit("scan_complete", payload, room=str(scan.api_scan_id))


def _resolve_scan(scan_id_raw: str, user_id: Optional[int]):
    if user_id is None:
        return None
    scan = Scan.query.filter_by(api_scan_id=scan_id_raw, user_id=user_id).first()
    if not scan and scan_id_raw.isdigit():
        scan = Scan.query.filter_by(id=int(scan_id_raw), user_id=user_id).first()
    return scan


def _get_authenticated_user_id() -> Optional[int]:
    user_id = session.get("user_id")
    if not user_id:
        return None
    try:
        return int(user_id)
    except (TypeError, ValueError):
        return None


def _chunk_text(text: str, chunk_size: int = 180):
    if not text:
        return [""]
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


def _conversation_room(conversation_id: int) -> str:
    return f"conversation:{conversation_id}"
