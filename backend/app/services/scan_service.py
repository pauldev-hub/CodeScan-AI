import asyncio
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import List

from app import db
from app.models.scan import Finding, Scan
from app.services.github_service import GitHubRateLimitError, GitHubService
from app.utils.constants import SCAN_STATUS_COMPLETE, SCAN_STATUS_ERROR, SCAN_STATUS_PENDING, SCAN_STATUS_RUNNING
from app.utils.security import get_redis_client


SYSTEM_PROMPT = """
You are a security-focused code analyzer. Return ONLY valid JSON with keys:
issues, health_score, pros, cons, refactor_suggestions.
""".strip()

logger = logging.getLogger(__name__)


class ScanService:
    @staticmethod
    def create_scan(user_id, input_type, input_value, file_count=None, code_size_bytes=None):
        scan = Scan(
            user_id=user_id,
            input_type=input_type,
            input_value=input_value,
            status=SCAN_STATUS_PENDING,
            api_scan_id=str(uuid.uuid4()),
            file_count=file_count,
            code_size_bytes=code_size_bytes,
        )
        db.session.add(scan)
        db.session.commit()
        return scan

    @staticmethod
    def get_scan_by_api_id(user_id, api_scan_id):
        return Scan.query.filter_by(user_id=user_id, api_scan_id=api_scan_id).first()

    @staticmethod
    def delete_scan(user_id, api_scan_id):
        scan = ScanService.get_scan_by_api_id(user_id, api_scan_id)
        if not scan:
            return False
        db.session.delete(scan)
        db.session.commit()
        return True

    @staticmethod
    def mark_scan_enqueue_failed(scan, message):
        scan.status = SCAN_STATUS_ERROR
        scan.error_message = message
        scan.completed_at = datetime.now(timezone.utc)
        scan.analysis_time_seconds = 0
        db.session.commit()

    @staticmethod
    def process_scan(scan_id):
        scan = Scan.query.get(scan_id)
        if not scan:
            return

        provider_used = None
        started = datetime.now(timezone.utc)
        scan.status = SCAN_STATUS_RUNNING
        scan.started_at = started
        db.session.commit()

        try:
            source_text = ScanService._resolve_scan_input(scan)
            analysis = ScanService._analyze_with_cache(scan, source_text)
            ScanService._persist_analysis(scan, analysis)
            provider_used = analysis.get("provider_used")
            scan.status = SCAN_STATUS_COMPLETE
            scan.error_message = None
        except GitHubRateLimitError as exc:
            scan.status = SCAN_STATUS_ERROR
            scan.error_message = f"GitHub rate limit reached: {exc}"
        except Exception as exc:
            scan.status = SCAN_STATUS_ERROR
            scan.error_message = f"Analysis failed: {exc}"

        completed = datetime.now(timezone.utc)
        scan.completed_at = completed
        scan.analysis_time_seconds = int((completed - started).total_seconds())
        db.session.commit()

        if scan.status == SCAN_STATUS_COMPLETE:
            try:
                from app.sockets import emit_scan_complete

                emit_scan_complete(scan, provider_used)
            except Exception as exc:
                logger.warning("Failed to emit scan_complete for scan %s: %s", scan.id, exc)

    @staticmethod
    def build_status_payload(scan):
        return {
            "scan_id": scan.api_scan_id,
            "status": scan.status,
            "progress": 100 if scan.status == SCAN_STATUS_COMPLETE else 50 if scan.status == SCAN_STATUS_RUNNING else 0,
            "message": scan.error_message if scan.status == SCAN_STATUS_ERROR else None,
            "error": scan.error_message if scan.status == SCAN_STATUS_ERROR else None,
        }

    @staticmethod
    def build_results_payload(scan):
        findings = [
            {
                "id": finding.id,
                "title": finding.title,
                "description": finding.description,
                "plain_english": finding.plain_english,
                "severity": finding.severity,
                "category": finding.category,
                "file_path": finding.file_path,
                "line_number": finding.line_number,
                "fix_suggestion": finding.fix_suggestion,
                "exploit_risk": finding.exploit_risk,
                "cwe_id": finding.cwe_id,
            }
            for finding in scan.findings.order_by(Finding.id.asc()).all()
        ]

        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for finding in findings:
            severity_counts[finding["severity"]] = severity_counts.get(finding["severity"], 0) + 1

        return {
            "scan_id": scan.api_scan_id,
            "health_score": scan.health_score,
            "analysis_time_seconds": scan.analysis_time_seconds,
            "findings": findings,
            "summary": {
                "total_findings": len(findings),
                "critical_count": severity_counts["critical"],
                "high_count": severity_counts["high"],
                "medium_count": severity_counts["medium"],
                "low_count": severity_counts["low"],
            },
            "pros": ScanService._json_list_field(scan.pros_json),
            "cons": ScanService._json_list_field(scan.cons_json),
            "refactor_suggestions": ScanService._json_list_field(scan.refactor_suggestions_json),
        }

    @staticmethod
    def _resolve_scan_input(scan):
        if scan.input_type == "paste":
            return scan.input_value or ""

        if scan.input_type == "url":
            github_service = GitHubService(token=os.getenv("GITHUB_TOKEN"))
            snapshot = github_service.fetch_repository_snapshot(scan.input_value)
            return snapshot["content"]

        return scan.input_value or ""

    @staticmethod
    def _analyze_with_cache(scan, source_text):
        cache_key = hashlib.sha256(source_text.encode("utf-8", errors="ignore")).hexdigest()
        redis_client = get_redis_client()
        if redis_client:
            cached = redis_client.get(f"scan:analysis:{cache_key}")
            if cached:
                return json.loads(cached)

        from app.services.ai_provider import get_ai_provider_service

        service = get_ai_provider_service()
        result, provider_used = asyncio.run(service.analyze_code(source_text, SYSTEM_PROMPT, scan.id))
        result["provider_used"] = provider_used

        if redis_client:
            redis_client.setex(f"scan:analysis:{cache_key}", 3600, json.dumps(result))

        return result

    @staticmethod
    def _persist_analysis(scan, analysis):
        scan.findings.delete()

        issues = analysis.get("issues", [])
        for issue in issues:
            finding = Finding(
                scan_id=scan.id,
                title=issue.get("title") or "Untitled issue",
                description=issue.get("description") or "",
                plain_english=issue.get("plain_english") or "",
                severity=issue.get("severity") or "medium",
                category=issue.get("category") or "security",
                file_path=issue.get("file_path") or "unknown",
                line_number=issue.get("line_number"),
                code_snippet=issue.get("code_snippet"),
                fix_suggestion=issue.get("fix_suggestion") or "",
                exploit_risk=issue.get("exploit_risk") or 0,
                cwe_id=issue.get("cwe_id"),
            )
            db.session.add(finding)

        scan.health_score = analysis.get("health_score")
        scan.total_findings = len(issues)
        scan.pros_json = json.dumps(ScanService._coerce_string_list(analysis.get("pros")))
        scan.cons_json = json.dumps(ScanService._coerce_string_list(analysis.get("cons")))
        scan.refactor_suggestions_json = json.dumps(
            ScanService._coerce_string_list(analysis.get("refactor_suggestions"))
        )

    @staticmethod
    def _coerce_string_list(values) -> List[str]:
        if not isinstance(values, list):
            return []

        cleaned = []
        for value in values:
            text = str(value or "").strip()
            if text:
                cleaned.append(text)
        return cleaned

    @staticmethod
    def _json_list_field(value) -> List[str]:
        if not value:
            return []
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return []
        return ScanService._coerce_string_list(parsed)
