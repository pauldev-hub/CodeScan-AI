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
        normalized = (message or "").strip()
        lowered = normalized.lower()
        if conversation.scan:
            top_finding = (
                conversation.scan.findings.order_by(Finding.exploit_risk.desc(), Finding.id.asc()).first()
            )
            if top_finding:
                plain = top_finding.plain_english or top_finding.description or "This code path trusts input too early."
                fix = top_finding.fix_suggestion or "Remove the unsafe pattern and add validation."
                location = f"{top_finding.file_path}:{top_finding.line_number or 'n/a'}"

                if any(keyword in lowered for keyword in ("simulate", "attack", "exploit")):
                    payload = "<script>alert(1)</script>" if "xss" in top_finding.title.lower() else "' OR '1'='1"
                    return (
                        "Local assistant reply:\n\n"
                        f"Target finding: {top_finding.title} at {location}\n"
                        f"Plain English: {plain}\n\n"
                        "Attack walk-through:\n"
                        f"1. Reach the vulnerable input that flows into {location}.\n"
                        f"2. Send a payload such as {payload}.\n"
                        "3. Observe whether the app changes query logic, rendering, or authorization behavior.\n\n"
                        f"Safest fix direction: {fix}"
                    )

                if any(keyword in lowered for keyword in ("fix", "patch", "remed", "secure")):
                    return (
                        "Local assistant reply:\n\n"
                        f"Highest-value fix: {top_finding.title} at {location}\n"
                        "Recommended path:\n"
                        f"1. {fix}\n"
                        "2. Add a regression test that proves attacker-controlled input no longer changes behavior.\n"
                        "3. Re-scan the snippet and confirm the finding disappears.\n\n"
                        f"Why this first: {plain}"
                    )

                return (
                    "Local assistant reply:\n\n"
                    f"Plain English: The highest-risk issue in this scan is '{top_finding.title}'. It matters because {plain}\n\n"
                    f"Technical note: Look at {location} and apply this fix direction: {fix}\n\n"
                    f"Question received: {normalized}"
                )
        return (
            "Local assistant reply:\n\n"
            "The external AI providers were unavailable, so I switched to a built-in assistant mode.\n"
            "Share a specific vulnerability, bug, or code snippet and I will still explain the risk, simulate the attack path, and suggest the safest next fix."
        )
