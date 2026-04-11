from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.models.chat import ChatMessage
from app.services.chat_service import ChatService
from app.utils.responses import error_response, success_response


chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")


@chat_bp.get("/conversations")
@jwt_required()
def list_conversations():
    user_id = int(get_jwt_identity())
    conversations = [ChatService.serialize_conversation(item) for item in ChatService.list_conversations(user_id)]
    return success_response({"items": conversations})


@chat_bp.post("/conversations")
@jwt_required()
def create_conversation():
    user_id = int(get_jwt_identity())
    payload = request.get_json(silent=True) or {}
    conversation = ChatService.create_conversation(
        user_id=user_id,
        title=(payload.get("title") or "New Chat"),
        scan_api_id=payload.get("scan_id"),
    )
    return success_response(ChatService.serialize_conversation(conversation), 201)


@chat_bp.get("/conversations/<int:conversation_id>")
@jwt_required()
def get_conversation(conversation_id):
    user_id = int(get_jwt_identity())
    conversation = ChatService.get_conversation(user_id, conversation_id)
    if not conversation:
        return error_response("Conversation not found", "not_found", 404)
    messages = [
        ChatService.serialize_message(item)
        for item in conversation.messages.order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc()).all()
    ]
    return success_response({**ChatService.serialize_conversation(conversation), "messages": messages})


@chat_bp.delete("/conversations/<int:conversation_id>")
@jwt_required()
def delete_conversation(conversation_id):
    user_id = int(get_jwt_identity())
    if not ChatService.delete_conversation(user_id, conversation_id):
        return error_response("Conversation not found", "not_found", 404)
    return success_response({"message": "Conversation deleted"})


@chat_bp.get("/conversations/<int:conversation_id>/messages")
@jwt_required()
def get_messages(conversation_id):
    user_id = int(get_jwt_identity())
    conversation = ChatService.get_conversation(user_id, conversation_id)
    if not conversation:
        return error_response("Conversation not found", "not_found", 404)

    page = max(1, int(request.args.get("page", 1)))
    per_page = min(100, max(1, int(request.args.get("per_page", 50))))
    pagination = ChatService.list_messages(conversation, page=page, per_page=per_page)
    items = [ChatService.serialize_message(item) for item in reversed(pagination.items)]
    return success_response(
        {
            "items": items,
            "page": page,
            "per_page": per_page,
            "pages": pagination.pages,
            "total": pagination.total,
        }
    )
