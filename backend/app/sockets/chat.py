import asyncio
from typing import Any, Dict, List, Optional

from flask import request, session
from flask_jwt_extended import decode_token
from flask_socketio import disconnect, emit, join_room

from app.models.scan import Finding, Scan
from app.utils.security import get_session_revoke_marker


CHAT_SYSTEM_PROMPT = (
    "You are a friendly security assistant helping a beginner understand their code scan results. "
    "Answer in plain English. No jargon. Be concise. When referencing issues from the scan, "
    "explain what they mean in real-world terms and suggest simple fixes. "
    "Context about their scan will be provided with each message."
)


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
            token_type = decoded.get("type")
            if token_type != "access":
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
        if not scan_id:
            emit("error", {"msg": "scan_id is required"})
            return

        user_id = _get_authenticated_user_id()
        if user_id is None:
            emit("error", {"msg": "Unauthorized"})
            disconnect()
            return

        scan = _resolve_scan(scan_id, user_id)
        if not scan:
            emit("error", {"msg": "Scan not found"})
            return

        room_name = str(scan.api_scan_id)
        join_room(room_name)
        emit("room_joined", {"scan_id": room_name})

    @socketio.on("join_chat")
    def join_chat(payload):
        join_scan_room(payload)

    @socketio.on("chat_message")
    def chat_message(payload):
        payload = payload or {}
        scan_id_raw = str(payload.get("scan_id") or "").strip()
        message = (payload.get("message") or "").strip()
        if not scan_id_raw or not message:
            emit("error", {"msg": "scan_id and message are required"})
            return

        user_id = _get_authenticated_user_id()
        if user_id is None:
            emit("error", {"msg": "Unauthorized"})
            disconnect()
            return

        if ChatSessionGuard.is_session_revoked(str(user_id)):
            emit("error", {"msg": "Session revoked. Please login again."})
            disconnect()
            return

        scan = _resolve_scan(scan_id_raw, user_id)
        if not scan:
            emit("error", {"msg": "Scan not found"})
            return

        room_name = str(scan.api_scan_id)
        join_room(room_name)

        context_blob = _build_scan_context(scan, message)

        try:
            from app.services.ai_provider import get_ai_provider_service

            service = get_ai_provider_service()
            analysis, provider_used = asyncio.run(
                service.analyze_code(context_blob, CHAT_SYSTEM_PROMPT, scan.id)
            )
        except Exception:
            emit("error", {"msg": "Chat analysis failed"})
            return

        reply_text = _build_reply_text(message, analysis)
        chunks = _chunk_text(reply_text)
        for chunk in chunks[:-1]:
            emit(
                "chat_response",
                {
                    "chunk": chunk,
                    "is_final": False,
                    "provider_used": provider_used,
                },
                room=room_name,
            )

        emit(
            "chat_response",
            {
                "chunk": chunks[-1] if chunks else "",
                "is_final": True,
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


def _resolve_scan(scan_id_raw: str, user_id: Optional[Any]):
    if user_id is None:
        return None

    scan = Scan.query.filter_by(api_scan_id=scan_id_raw).first()
    if not scan and scan_id_raw.isdigit():
        scan = Scan.query.get(int(scan_id_raw))

    if not scan:
        return None

    try:
        owner_id = int(user_id)
    except (TypeError, ValueError):
        return None

    return scan if scan.user_id == owner_id else None


def _get_authenticated_user_id() -> Optional[int]:
    user_id = session.get("user_id")
    if not user_id:
        return None
    try:
        return int(user_id)
    except (TypeError, ValueError):
        return None


def _build_scan_context(scan, question: str) -> str:
    findings = scan.findings.order_by(Finding.id.desc()).limit(20).all()
    issues = []
    finding_lines = []
    for finding in findings:
        issues.append(
            {
                "title": finding.title,
                "severity": finding.severity,
                "plain_english": finding.plain_english,
                "file_path": finding.file_path,
                "line_number": finding.line_number,
            }
        )
        finding_lines.append(
            (
                f"- [{finding.severity}] {finding.title}"
                f" ({finding.file_path}:{finding.line_number or 'n/a'})"
                f" | plain_english={finding.plain_english}"
            )
        )

    summary_blob = build_chat_message(
        {
            "health_score": scan.health_score,
            "issues": issues,
        },
        question,
    )
    findings_blob = "\n".join(finding_lines) if finding_lines else "- No findings yet"
    return (
        f"Scan id: {scan.api_scan_id}\n"
        f"Scan status: {scan.status}\n"
        f"{summary_blob}\n\n"
        f"Known findings:\n{findings_blob}"
    )


def build_chat_message(scan_results: Dict[str, Any], user_message: str) -> str:
    issues = scan_results.get("issues") or []
    top_issues = [issue.get("title") or "Untitled issue" for issue in issues[:3]]
    health_score = scan_results.get("health_score")
    health_score_text = "n/a" if health_score is None else str(health_score)

    context = f"Scan health score: {health_score_text}/100. "
    context += f"Issues found: {len(issues)}. "
    context += f"Top issues: {top_issues}."
    return f"{context}\n\nUser question: {user_message}"


def _build_reply_text(question: str, analysis: Dict[str, Any]) -> str:
    issues = analysis.get("issues") or []
    if not issues:
        return (
            f"You asked: {question}\n"
            "I did not detect new issues from the current scan context. "
            "If you share a specific file/line, I can explain it in more detail."
        )

    top_issue = issues[0]
    title = top_issue.get("title") or "Potential issue"
    severity = top_issue.get("severity") or "medium"
    plain = top_issue.get("plain_english") or top_issue.get("description") or ""
    fix = top_issue.get("fix_suggestion") or "No fix suggestion provided"

    return (
        f"You asked: {question}\n"
        f"Top risk: {title} ({severity}).\n"
        f"Why it matters: {plain}\n"
        f"Recommended fix: {fix}"
    )


def _chunk_text(text: str, chunk_size: int = 120) -> List[str]:
    if not text:
        return [""]
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]
