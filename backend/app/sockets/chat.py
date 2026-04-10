import asyncio
from typing import Any, Dict, List, Optional

from flask import request, session
from flask_jwt_extended import decode_token
from flask_socketio import disconnect, emit, join_room

from app.models.scan import Finding, Scan
from app.utils.security import get_session_revoke_marker


CHAT_SYSTEM_PROMPT = (
    "You are a helpful code review assistant. Return a JSON object with issues, health_score, pros, cons, "
    "and refactor_suggestions. Keep issue plain_english easy for beginners. Prefer actionable fixes over abstract advice."
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
            provider_used = "local_fallback"
            analysis = _build_local_chat_fallback_analysis(scan, message)

        reply_text = _build_reply_text(message, analysis, scan)
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


def _build_reply_text(question: str, analysis: Dict[str, Any], scan: Scan) -> str:
    question_text = (question or "").strip()
    ranked_findings = scan.findings.order_by(Finding.exploit_risk.desc(), Finding.id.asc()).limit(3).all()
    issues = analysis.get("issues") or []

    if not ranked_findings and not issues:
        return (
            f"Question: {question_text}\n\n"
            "This scan does not currently contain recorded findings.\n"
            "If you rerun the scan with more code context, I can explain the results in detail."
        )

    answer_lines = [f"Question: {question_text}", ""]
    answer_lines.append(
        f"Scan summary: health score {scan.health_score if scan.health_score is not None else 'n/a'}/100 with {scan.total_findings or len(ranked_findings)} finding(s)."
    )

    lower_question = question_text.lower()
    wants_fix = any(term in lower_question for term in ("fix", "solve", "patch", "change"))
    wants_priority = any(term in lower_question for term in ("important", "priority", "first", "urgent"))

    selected_findings = ranked_findings or []
    if wants_priority:
        answer_lines.append("Focus first on the findings with the highest exploit risk or severity.")
    elif wants_fix:
        answer_lines.append("Here are the most practical fixes to start with.")
    else:
        answer_lines.append("Here is the clearest explanation of the highest-risk findings in this scan.")

    for index, finding in enumerate(selected_findings[:3], start=1):
        answer_lines.extend(
            [
                "",
                f"{index}. {finding.title} ({finding.severity})",
                f"Why it matters: {finding.plain_english or finding.description}",
                f"Where: {finding.file_path}:{finding.line_number or 'n/a'}",
                f"Fix: {finding.fix_suggestion or 'Review the surrounding code and remove the unsafe pattern.'}",
            ]
        )

    if issues and not selected_findings:
        top_issue = issues[0]
        answer_lines.extend(
            [
                "",
                f"Top issue: {top_issue.get('title') or 'Potential issue'} ({top_issue.get('severity') or 'medium'})",
                f"Why it matters: {top_issue.get('plain_english') or top_issue.get('description') or 'This issue increases security risk.'}",
                f"Fix: {top_issue.get('fix_suggestion') or 'Review the code path and apply the safer alternative.'}",
            ]
        )

    answer_lines.extend(
        [
            "",
            "Next step: open the finding card you want to work on, then use the fix preview and ask a follow-up like 'show me the safest fix for finding 2'.",
        ]
    )

    return "\n".join(answer_lines)


def _build_local_chat_fallback_analysis(scan: Scan, question: str) -> Dict[str, Any]:
    del question
    top_finding = scan.findings.order_by(Finding.exploit_risk.desc(), Finding.id.desc()).first()
    if not top_finding:
        return {
            "issues": [],
            "health_score": scan.health_score,
        }

    issue = {
        "title": top_finding.title,
        "severity": top_finding.severity,
        "plain_english": top_finding.plain_english or top_finding.description,
        "description": top_finding.description,
        "fix_suggestion": top_finding.fix_suggestion,
        "file_path": top_finding.file_path,
        "line_number": top_finding.line_number,
    }
    return {
        "issues": [issue],
        "health_score": scan.health_score,
    }


def _chunk_text(text: str, chunk_size: int = 180) -> List[str]:
    if not text:
        return [""]
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]
