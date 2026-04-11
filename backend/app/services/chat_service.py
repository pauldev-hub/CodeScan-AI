from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from app import db
from app.models.chat import ChatConversation, ChatMessage
from app.models.scan import Finding, Scan


class ChatService:
    @staticmethod
    def list_conversations(user_id: int) -> List[ChatConversation]:
        return (
            ChatConversation.query.filter_by(user_id=user_id)
            .order_by(ChatConversation.updated_at.desc(), ChatConversation.id.desc())
            .all()
        )

    @staticmethod
    def get_conversation(user_id: int, conversation_id: int) -> Optional[ChatConversation]:
        return ChatConversation.query.filter_by(id=conversation_id, user_id=user_id).first()

    @staticmethod
    def create_conversation(user_id: int, title: str = "New Chat", scan_api_id: Optional[str] = None) -> ChatConversation:
        scan = None
        if scan_api_id:
            scan = Scan.query.filter_by(api_scan_id=scan_api_id, user_id=user_id).first()
        conversation = ChatConversation(
            user_id=user_id,
            title=(title or "New Chat").strip()[:100] or "New Chat",
            scan_id=scan.id if scan else None,
        )
        db.session.add(conversation)
        db.session.commit()
        return conversation

    @staticmethod
    def delete_conversation(user_id: int, conversation_id: int) -> bool:
        conversation = ChatService.get_conversation(user_id, conversation_id)
        if not conversation:
            return False
        db.session.delete(conversation)
        db.session.commit()
        return True

    @staticmethod
    def list_messages(conversation: ChatConversation, page: int = 1, per_page: int = 50):
        return (
            conversation.messages.order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .paginate(page=page, per_page=per_page, error_out=False)
        )

    @staticmethod
    def add_message(conversation: ChatConversation, role: str, content: str) -> ChatMessage:
        message = ChatMessage(conversation_id=conversation.id, role=role, content=content.strip())
        db.session.add(message)
        conversation.updated_at = datetime.now(timezone.utc)
        if role == "user" and (conversation.title == "New Chat" or not conversation.title.strip()):
            conversation.title = content.strip()[:100] or "New Chat"
        db.session.commit()
        return message

    @staticmethod
    def serialize_conversation(conversation: ChatConversation) -> Dict[str, object]:
        first_message = conversation.messages.order_by(ChatMessage.created_at.asc()).first()
        return {
            "id": conversation.id,
            "title": conversation.title,
            "scan_id": conversation.scan.api_scan_id if conversation.scan else None,
            "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
            "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
            "preview": (first_message.content[:80] if first_message else ""),
            "message_count": conversation.messages.count(),
        }

    @staticmethod
    def serialize_message(message: ChatMessage) -> Dict[str, object]:
        return {
            "id": message.id,
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at.isoformat() if message.created_at else None,
        }

    @staticmethod
    def build_chat_prompt(conversation: ChatConversation, message: str) -> Tuple[str, str]:
        system_prompt = (
            "You are DevChat, an AI assistant built into CodeScan AI.\n"
            "Help developers understand vulnerabilities, code bugs, debugging steps, and secure fixes.\n"
            "Always explain in plain English first, then add technical depth.\n"
            "Keep responses actionable, accurate, and concise.\n"
        )

        scan_context = ""
        if conversation.scan:
            findings = conversation.scan.findings.order_by(Finding.exploit_risk.desc(), Finding.id.asc()).limit(8).all()
            lines = [
                f"- [{finding.severity}] {finding.title} at {finding.file_path}:{finding.line_number or 'n/a'} | fix={finding.fix_suggestion}"
                for finding in findings
            ]
            scan_context = (
                f"Current scan: {conversation.scan.api_scan_id}\n"
                f"Health score: {conversation.scan.health_score or 'n/a'}\n"
                f"Known findings:\n{chr(10).join(lines) if lines else '- No stored findings'}\n"
            )

        history_rows = (
            conversation.messages.order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc()).limit(10).all()
        )
        history_rows.reverse()
        history = "\n".join([f"{item.role}: {item.content}" for item in history_rows]) or "No previous messages."
        user_prompt = f"{scan_context}\nRecent conversation:\n{history}\n\nUser message: {message}"
        return system_prompt, user_prompt

    @staticmethod
    def build_local_fallback_reply(conversation: ChatConversation, message: str) -> str:
        if conversation.scan:
            top_finding = (
                conversation.scan.findings.order_by(Finding.exploit_risk.desc(), Finding.id.asc()).first()
            )
            if top_finding:
                return (
                    f"Plain English: The highest-risk issue in this scan is '{top_finding.title}'. "
                    f"It matters because {top_finding.plain_english or top_finding.description}\n\n"
                    f"Technical note: Look at {top_finding.file_path}:{top_finding.line_number or 'n/a'} and apply this fix direction: "
                    f"{top_finding.fix_suggestion or 'Remove the unsafe pattern and add validation.'}\n\n"
                    f"Your question was: {message}"
                )
        return (
            "I could not reach the primary AI providers, so I am replying with a local fallback.\n\n"
            "Ask about a specific vulnerability, bug, or code snippet and I will explain the likely risk and the safest next step."
        )
