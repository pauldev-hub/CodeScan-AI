import asyncio
import hashlib
import json
import logging
import os
import re
import tomllib
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from statistics import mean
from typing import Dict, List, Optional, Tuple

from app import db
from app.models.scan import Finding, Scan
from app.services.ai_provider import AIProviderService
from app.services.github_service import GitHubRateLimitError, GitHubService
from app.utils.constants import (
    ANALYSIS_CHUNK_CHAR_SIZE,
    ANALYSIS_MAX_CHUNKS,
    SCAN_STATUS_COMPLETE,
    SCAN_STATUS_ERROR,
    SCAN_STATUS_PENDING,
    SCAN_STATUS_RUNNING,
)
from app.utils.security import get_redis_client


SYSTEM_PROMPT = """
You are a security-focused code analyzer. Return ONLY valid JSON with keys:
issues, health_score, pros, cons, refactor_suggestions.
""".strip()

logger = logging.getLogger(__name__)


class ScanService:
    MANIFEST_FILENAMES = {
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "requirements.txt",
        "pyproject.toml",
        "poetry.lock",
        "pipfile",
        "pipfile.lock",
        "cargo.toml",
        "cargo.lock",
        "go.mod",
        "go.sum",
        "pom.xml",
        "composer.json",
        "gemfile",
        "gemfile.lock",
    }

    @staticmethod
    def create_scan(user_id, input_type, input_value, file_count=None, code_size_bytes=None, input_language=None):
        scan = Scan(
            user_id=user_id,
            input_type=input_type,
            input_value=input_value,
            input_language=ScanService.normalize_language(input_language),
            status=SCAN_STATUS_PENDING,
            api_scan_id=str(uuid.uuid4()),
            file_count=file_count,
            code_size_bytes=code_size_bytes,
            queue_mode="pending",
        )
        db.session.add(scan)
        db.session.commit()
        return scan

    @staticmethod
    def serialize_scan_input(payload: object) -> str:
        if isinstance(payload, str):
            return payload
        return json.dumps(payload or {})

    @staticmethod
    def serialize_datetime(value: Optional[datetime]) -> Optional[str]:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()

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
        scan = db.session.get(Scan, scan_id)
        if not scan:
            return

        provider_used = None
        started = datetime.now(timezone.utc)
        scan.status = SCAN_STATUS_RUNNING
        scan.started_at = started
        db.session.commit()

        try:
            source_text = ScanService._resolve_scan_input(scan)
            scan.input_language = ScanService.detect_language_for_scan(scan, source_text)
            analysis = ScanService._analyze_with_cache(scan, source_text)
            ScanService._persist_analysis(scan, analysis)
            provider_used = analysis.get("provider_used")
            scan.ai_provider_used = provider_used
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
            "progress": 100 if scan.status == SCAN_STATUS_COMPLETE else 55 if scan.status == SCAN_STATUS_RUNNING else 0,
            "message": scan.error_message if scan.status == SCAN_STATUS_ERROR else None,
            "error": scan.error_message if scan.status == SCAN_STATUS_ERROR else None,
            "queue_mode": scan.queue_mode,
            "provider_used": scan.ai_provider_used,
        }

    @staticmethod
    def _resolve_scan_input(scan):
        if scan.input_type == "paste":
            return scan.input_value or ""

        if scan.input_type == "url":
            payload = ScanService._parse_url_scan_input(scan.input_value)
            github_service = GitHubService(token=os.getenv("GITHUB_TOKEN"))
            snapshot = github_service.fetch_repository_snapshot(
                payload["github_url"],
                selected_paths=payload["selected_paths"],
            )
            scan.file_count = snapshot.get("file_count")
            scan.code_size_bytes = snapshot.get("total_bytes")
            return snapshot["content"]

        return scan.input_value or ""

    @staticmethod
    def _parse_url_scan_input(raw_value: Optional[str]) -> Dict[str, object]:
        text = str(raw_value or "").strip()
        if not text:
            return {"github_url": "", "selected_paths": [], "scan_entire": True}

        try:
            parsed = json.loads(text)
        except (TypeError, ValueError):
            return {"github_url": text, "selected_paths": [], "scan_entire": True}

        if not isinstance(parsed, dict):
            return {"github_url": text, "selected_paths": [], "scan_entire": True}

        github_url = str(parsed.get("github_url") or "").strip()
        selected_paths = [
            str(item or "").strip().strip("/")
            for item in (parsed.get("selected_paths") or [])
            if str(item or "").strip()
        ]
        scan_entire = bool(parsed.get("scan_entire", not selected_paths))
        return {
            "github_url": github_url,
            "selected_paths": [] if scan_entire else selected_paths,
            "scan_entire": scan_entire,
        }

    @staticmethod
    def normalize_language(raw_language: Optional[str]) -> str:
        normalized = str(raw_language or "").strip().lower()
        aliases = {
            "py": "python",
            "js": "javascript",
            "ts": "typescript",
            "tsx": "typescript",
            "golang": "go",
            "node": "javascript",
            "c#": "csharp",
            "cs": "csharp",
            "rb": "ruby",
            "auto": "text",
        }
        return aliases.get(normalized, normalized or "text")

    @staticmethod
    def detect_language_from_filename(filename: Optional[str]) -> str:
        lowered = os.path.basename(str(filename or "").strip()).lower()
        extension = os.path.splitext(lowered)[1]
        explicit = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".php": "php",
            ".cs": "csharp",
            ".cpp": "cpp",
            ".json": "json",
            ".yml": "yaml",
            ".yaml": "yaml",
            ".toml": "toml",
            ".sql": "sql",
            ".html": "html",
            ".css": "css",
        }
        named = {
            "package.json": "javascript",
            "package-lock.json": "javascript",
            "pnpm-lock.yaml": "javascript",
            "yarn.lock": "javascript",
            "requirements.txt": "python",
            "pyproject.toml": "python",
            "poetry.lock": "python",
            "pipfile": "python",
            "pipfile.lock": "python",
            "cargo.toml": "rust",
            "cargo.lock": "rust",
            "go.mod": "go",
            "go.sum": "go",
            "pom.xml": "java",
            "composer.json": "php",
            "gemfile": "ruby",
            "gemfile.lock": "ruby",
        }
        return named.get(lowered, explicit.get(extension, "text"))

    @staticmethod
    def detect_language(source_text: str, filename: Optional[str] = None) -> str:
        filename_language = ScanService.detect_language_from_filename(filename)
        if filename_language != "text":
            return filename_language

        text = str(source_text or "")
        lowered = text.lower()
        heuristics = [
            ("python", ["def ", "import ", "from ", "if __name__ == '__main__':", "elif "]),
            ("javascript", ["const ", "let ", "=>", "console.log", "function ", "module.exports"]),
            ("typescript", ["interface ", "type ", ": string", ": number", "implements "]),
            ("java", ["public class ", "system.out.println", "public static void main"]),
            ("go", ["package main", "func main()", "fmt.", "import ("]),
            ("rust", ["fn main()", "println!", "let mut ", "impl "]),
            ("php", ["<?php", "echo ", "$_post", "$_get"]),
            ("csharp", ["using system", "namespace ", "public class ", "console.writeline"]),
            ("sql", ["select ", "insert into ", "update ", "delete from "]),
            ("html", ["<!doctype html", "<html", "<div", "<body"]),
            ("css", ["{", "}", "color:", "display:", "@media"]),
            ("json", ['"{', '":', '"dependencies"', '"name"']),
        ]
        scores = Counter()
        for language, tokens in heuristics:
            for token in tokens:
                if token in lowered:
                    scores[language] += 1
        return scores.most_common(1)[0][0] if scores else "text"

    @staticmethod
    def _split_source_files(source_text: str) -> List[Dict[str, str]]:
        text = str(source_text or "")
        if "# File:" not in text:
            return [{"path": "snippet", "content": text.strip()}]

        chunks = re.split(r"\n# File: ", text)
        files = []
        for index, chunk in enumerate(chunks):
            if index == 0 and not chunk.strip():
                continue
            if index == 0 and "# File:" not in text:
                continue
            if "\n" not in chunk:
                path = chunk.strip()
                content = ""
            else:
                path, content = chunk.split("\n", 1)
            files.append({"path": path.strip(), "content": content.strip()})
        return [item for item in files if item["path"]]

    @staticmethod
    def detect_language_for_scan(scan: Scan, source_text: str) -> str:
        current = ScanService.normalize_language(getattr(scan, "input_language", None))
        if current != "text":
            return current

        url_payload = ScanService._parse_url_scan_input(scan.input_value) if scan.input_type == "url" else None
        split_files = ScanService._split_source_files(source_text)
        candidates = Counter()
        for item in split_files:
            language = ScanService.detect_language(item["content"], item["path"])
            if language != "text":
                candidates[language] += 1
        if url_payload and url_payload["selected_paths"]:
            for path in url_payload["selected_paths"]:
                language = ScanService.detect_language_from_filename(path)
                if language != "text":
                    candidates[language] += 1

        if candidates:
            return candidates.most_common(1)[0][0]
        return ScanService.detect_language(source_text)

    @staticmethod
    def _analyze_with_cache(scan, source_text):
        language = ScanService.normalize_language(scan.input_language)
        cache_key = hashlib.sha256(f"{language}:{source_text}".encode("utf-8", errors="ignore")).hexdigest()
        redis_client = get_redis_client()
        if redis_client:
            cached = redis_client.get(f"scan:analysis:{cache_key}")
            if cached:
                return json.loads(cached)

        chunks = ScanService._chunk_source(source_text)
        provider_used_list = []
        chunk_results = []
        for index, chunk in enumerate(chunks):
            prompt = f"{SYSTEM_PROMPT}\nLanguage: {language}\nChunk {index + 1} of {len(chunks)}."
            try:
                from app.services.ai_provider import get_ai_provider_service

                service = get_ai_provider_service()
                result, provider_used = asyncio.run(service.analyze_code(chunk, prompt, scan.id))
                provider_used_list.append(provider_used)
                chunk_results.append(result)
            except Exception as exc:
                logger.warning(
                    "Scan %s AI analysis failed on chunk %s; using local fallback analyzer: %s",
                    scan.id,
                    index + 1,
                    exc,
                )
                chunk_results.append(ScanService._build_local_fallback_analysis(chunk, str(exc), language))
                provider_used_list.append("local_fallback")

        result = ScanService._merge_chunk_analyses(chunk_results)
        result["provider_used"] = provider_used_list[0] if provider_used_list else "local_fallback"
        result["provider_used_list"] = provider_used_list

        if redis_client:
            redis_client.setex(f"scan:analysis:{cache_key}", 3600, json.dumps(result))

        return result

    @staticmethod
    def _chunk_source(source_text: str) -> List[str]:
        text = source_text or ""
        if len(text) <= ANALYSIS_CHUNK_CHAR_SIZE:
            return [text]

        lines = text.splitlines()
        chunks = []
        current_lines = []
        current_size = 0
        for line in lines:
            line_size = len(line) + 1
            if current_lines and current_size + line_size > ANALYSIS_CHUNK_CHAR_SIZE:
                chunks.append("\n".join(current_lines))
                current_lines = []
                current_size = 0
            current_lines.append(line)
            current_size += line_size
            if len(chunks) >= ANALYSIS_MAX_CHUNKS:
                break

        if current_lines and len(chunks) < ANALYSIS_MAX_CHUNKS:
            chunks.append("\n".join(current_lines))
        return chunks[:ANALYSIS_MAX_CHUNKS] or [text[:ANALYSIS_CHUNK_CHAR_SIZE]]

    @staticmethod
    def _merge_chunk_analyses(chunk_results: List[Dict[str, object]]) -> Dict[str, object]:
        merged_issues = []
        pros = []
        cons = []
        refactors = []
        scores = []
        seen = set()

        for result in chunk_results:
            scores.append(int(result.get("health_score") or 0))
            pros.extend(ScanService._coerce_string_list(result.get("pros")))
            cons.extend(ScanService._coerce_string_list(result.get("cons")))
            refactors.extend(ScanService._coerce_string_list(result.get("refactor_suggestions")))
            for issue in result.get("issues", []):
                issue_key = (
                    issue.get("title"),
                    issue.get("file_path"),
                    issue.get("line_number"),
                    issue.get("severity"),
                )
                if issue_key in seen:
                    continue
                seen.add(issue_key)
                merged_issues.append(issue)

        return {
            "issues": merged_issues,
            "health_score": int(mean(scores)) if scores else 100,
            "pros": list(dict.fromkeys(pros))[:6],
            "cons": list(dict.fromkeys(cons))[:6],
            "refactor_suggestions": list(dict.fromkeys(refactors))[:6],
        }

    @staticmethod
    def _build_local_fallback_analysis(source_text, failure_reason, language="text"):
        issues = []
        lower_text = (source_text or "").lower()

        if "eval(" in lower_text or "exec(" in lower_text:
            issues.append(
                {
                    "title": "Dynamic code execution detected",
                    "description": "The code appears to use eval/exec, which can execute attacker-controlled input.",
                    "plain_english": "Your code runs text as code. If user input reaches this path, attackers can run harmful commands.",
                    "severity": "high",
                    "category": "security",
                    "file_path": "snippet",
                    "line_number": None,
                    "fix_suggestion": "Avoid eval/exec on untrusted input. Use strict parsing or whitelisted operations.",
                    "exploit_risk": 85,
                    "cwe_id": "CWE-95",
                    "code_snippet": ScanService._snippet_for_pattern(source_text, "eval("),
                }
            )

        if re.search(r"select\s+\*\s+from", lower_text) and ("+" in source_text or "f\"" in source_text or "format(" in lower_text):
            issues.append(
                {
                    "title": "Potential SQL injection pattern",
                    "description": "The query text appears to be built through string concatenation/interpolation.",
                    "plain_english": "A database query seems to be built using raw text pieces. That can let malicious input change the query.",
                    "severity": "critical",
                    "category": "security",
                    "file_path": "snippet",
                    "line_number": None,
                    "fix_suggestion": "Use parameterized queries/placeholders instead of string building.",
                    "exploit_risk": 92,
                    "cwe_id": "CWE-89",
                    "code_snippet": ScanService._snippet_for_pattern(source_text, "select"),
                }
            )

        if "password" in lower_text and ("=" in source_text) and ("'" in source_text or '"' in source_text):
            issues.append(
                {
                    "title": "Possible hardcoded credential",
                    "description": "A password-like identifier appears assigned to a literal value.",
                    "plain_english": "A password looks hardcoded in the code. Secrets in source can leak and be abused.",
                    "severity": "medium",
                    "category": "security",
                    "file_path": "snippet",
                    "line_number": None,
                    "fix_suggestion": "Move secrets to environment variables or a secrets manager.",
                    "exploit_risk": 60,
                    "cwe_id": "CWE-798",
                    "code_snippet": ScanService._snippet_for_pattern(source_text, "password"),
                }
            )

        if language == "python" and re.search(r"\bexcept\s*:\s*$", source_text, flags=re.MULTILINE):
            issues.append(
                {
                    "title": "Broad exception handler hides failures",
                    "description": "A bare except block can swallow runtime errors and make debugging harder.",
                    "plain_english": "The code catches every possible error without being specific, so important failures may stay hidden.",
                    "severity": "medium",
                    "category": "bug",
                    "file_path": "snippet",
                    "line_number": None,
                    "fix_suggestion": "Catch specific exception types and log or re-raise unexpected failures.",
                    "exploit_risk": 28,
                    "cwe_id": "CWE-391",
                    "code_snippet": ScanService._snippet_for_pattern(source_text, "except"),
                }
            )

        health_score = max(10, 100 - (len(issues) * 20))
        return {
            "issues": issues,
            "health_score": health_score,
            "pros": ["Scan completed using local resilience fallback."],
            "cons": [f"Primary AI providers unavailable: {failure_reason}"],
            "refactor_suggestions": ["Configure at least one healthy AI provider key for richer analysis."],
        }

    @staticmethod
    def _snippet_for_pattern(source_text: str, pattern: str, window: int = 220) -> str:
        lower_text = (source_text or "").lower()
        start = lower_text.find(pattern.lower())
        if start == -1:
            return (source_text or "")[:window]
        end = min(len(source_text or ""), start + window)
        return (source_text or "")[max(0, start - 40) : end].strip()

    @staticmethod
    def build_fix_preview(scan, finding, override_suggestion=None):
        suggestion = (override_suggestion or finding.fix_suggestion or "").strip()
        before = (finding.code_snippet or "").strip("\n")
        if not before:
            source_text = ScanService._resolve_scan_input(scan)
            before = ScanService._derive_finding_snippet(source_text, finding)
        language = ScanService.normalize_language(scan.input_language)
        preview_language = language if language != "text" else ScanService._guess_snippet_language(before)
        change_summary, rationale, edit_hints = ScanService._build_fix_guidance(
            {
                "title": finding.title,
                "description": finding.description,
                "plain_english": finding.plain_english,
                "severity": finding.severity,
                "category": finding.category,
                "fix_suggestion": finding.fix_suggestion,
            },
            preview_language,
            suggestion,
        )
        after = ScanService._build_fixed_code(
            before,
            {
                "title": finding.title,
                "description": finding.description,
                "plain_english": finding.plain_english,
                "severity": finding.severity,
                "category": finding.category,
                "fix_suggestion": finding.fix_suggestion,
            },
            preview_language,
            suggestion,
            rationale,
        )
        diff_stats = ScanService._compute_diff_stats(before, after)

        return {
            "scan_id": scan.api_scan_id,
            "finding_id": finding.id,
            "before": before,
            "after": after,
            "language": preview_language,
            "message": "Detailed fix preview generated from the finding details and captured snippet.",
            "source": "generated_fix_preview",
            "change_summary": change_summary,
            "rationale": rationale,
            "edit_hints": edit_hints,
            "diff_stats": diff_stats,
        }

    @staticmethod
    def _derive_finding_snippet(source_text: str, finding) -> str:
        text = source_text or ""
        title = str(getattr(finding, "title", "") or "").lower()
        description = str(getattr(finding, "description", "") or "").lower()
        combined = f"{title} {description}"

        pattern_sets = [
            (["sql", "injection", "query", "select"], ["select", "execute(", "cursor.execute", "where", "query"]),
            (["xss", "cross-site", "script"], ["<script", "innerhtml", "dangerouslysetinnerhtml", "request.args", "return f\"<"]),
            (["pickle", "deserialize", "deserialization"], ["pickle.loads", "pickle.load", "yaml.load", "deserialize"]),
            (["secret", "password", "token", "credential", "hardcoded"], ["secret", "password", "token", "api_key", "app.secret_key"]),
            (["command", "subprocess", "shell"], ["subprocess", "shell=true", "os.system", "exec(", "eval("])
        ]

        for keywords, patterns in pattern_sets:
            if not any(keyword in combined for keyword in keywords):
                continue
            for pattern in patterns:
                snippet = ScanService._snippet_for_pattern(text, pattern, window=320)
                if snippet and snippet.strip():
                    return snippet

        file_path = str(getattr(finding, "file_path", "") or "")
        if file_path and file_path.lower() != "unknown":
            snippet = ScanService._snippet_for_pattern(text, file_path, window=320)
            if snippet and snippet.strip():
                return snippet

        fallback = (text or "").strip()
        return fallback[:320] if fallback else ""

    @staticmethod
    def build_results_payload(scan):
        source_text = ScanService._resolve_scan_input(scan)
        input_language = ScanService.detect_language_for_scan(scan, source_text)
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
                "owasp_category": finding.owasp_category,
                "code_snippet": finding.code_snippet,
            }
            for finding in scan.findings.order_by(Finding.id.asc()).all()
        ]
        enriched = ScanService._enrich_findings(findings, source_text, input_language)
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for finding in enriched:
            severity_counts[finding["severity"]] += 1

        overview = ScanService._build_overview_tab(enriched)
        security_tab = ScanService._build_security_tab(enriched, source_text)
        map_tab = ScanService._build_map_tab(enriched, source_text)
        dependencies_tab = ScanService._build_dependencies_tab(source_text, enriched)
        learn_tab = ScanService._ensure_learn_content(scan, enriched, input_language)
        source_overview = ScanService._build_source_overview(scan, source_text)

        return {
            "scan_id": scan.api_scan_id,
            "health_score": scan.health_score,
            "input_language": input_language,
            "input_type": scan.input_type,
            "analysis_time_seconds": scan.analysis_time_seconds,
            "file_count": scan.file_count,
            "code_size_bytes": scan.code_size_bytes,
            "queue_mode": scan.queue_mode,
            "provider_used": scan.ai_provider_used,
            "created_at": ScanService.serialize_datetime(scan.created_at),
            "started_at": ScanService.serialize_datetime(scan.started_at),
            "completed_at": ScanService.serialize_datetime(scan.completed_at),
            "findings": enriched,
            "summary": {
                "total_findings": len(enriched),
                "critical_count": severity_counts["critical"],
                "high_count": severity_counts["high"],
                "medium_count": severity_counts["medium"],
                "low_count": severity_counts["low"],
                "security_count": len([item for item in enriched if item["category"] == "security"]),
                "complexity_score": overview["complexity_score"],
                "fix_time_total_minutes": overview["fix_time_total_minutes"],
            },
            "pros": ScanService._json_list_field(scan.pros_json),
            "cons": ScanService._json_list_field(scan.cons_json),
            "refactor_suggestions": ScanService._json_list_field(scan.refactor_suggestions_json),
            "source_overview": source_overview,
            "tabs": {
                "overview": overview,
                "security": security_tab,
                "map": map_tab,
                "dependencies": dependencies_tab,
                "learn": learn_tab,
            },
            "chat_starters": ScanService._build_chat_starters(enriched),
            "executive_summary": ScanService._build_executive_summary(scan, enriched, overview),
        }

    @staticmethod
    def regenerate_learn_content(scan):
        source_text = ScanService._resolve_scan_input(scan)
        input_language = ScanService.detect_language_for_scan(scan, source_text)
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
                "owasp_category": finding.owasp_category,
            }
            for finding in scan.findings.order_by(Finding.id.asc()).all()
        ]
        enriched = ScanService._enrich_findings(findings, source_text, input_language)
        learn_tab = ScanService._generate_learn_content(scan, enriched, input_language, force_ai=True)
        scan.learn_content_json = json.dumps(learn_tab)
        db.session.commit()
        return learn_tab

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
                owasp_category=issue.get("owasp_category"),
            )
            db.session.add(finding)

        scan.health_score = analysis.get("health_score")
        scan.total_findings = len(issues)
        scan.pros_json = json.dumps(ScanService._coerce_string_list(analysis.get("pros")))
        scan.cons_json = json.dumps(ScanService._coerce_string_list(analysis.get("cons")))
        scan.refactor_suggestions_json = json.dumps(ScanService._coerce_string_list(analysis.get("refactor_suggestions")))

    @staticmethod
    def _severity_weight(severity: str) -> int:
        return {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(severity, 1)

    @staticmethod
    def _owasp_for_issue(issue: Dict[str, object]) -> str:
        text = " ".join(
            [
                str(issue.get("title") or ""),
                str(issue.get("description") or ""),
                str(issue.get("plain_english") or ""),
                str(issue.get("cwe_id") or ""),
            ]
        ).lower()
        mappings = [
            ("A03: Injection", ["sql", "injection", "cwe-89", "command"]),
            ("A02: Cryptographic Failures", ["credential", "secret", "password", "token"]),
            ("A01: Broken Access Control", ["auth", "authorization", "cors", "access"]),
            ("A05: Security Misconfiguration", ["misconfiguration", "cors", "headers", "https"]),
            ("A06: Vulnerable Components", ["dependency", "package", "cve"]),
        ]
        for label, keywords in mappings:
            if any(keyword in text for keyword in keywords):
                return label
        return "A04: Insecure Design"

    @staticmethod
    def _infer_fix_effort(issue: Dict[str, object]) -> str:
        title = str(issue.get("title") or "").lower()
        if any(keyword in title for keyword in ("credential", "cors", "auth", "null")):
            return "quick win"
        if issue.get("severity") == "critical":
            return "deep fix"
        if issue.get("category") == "performance":
            return "medium lift"
        return "steady fix"

    @staticmethod
    def _estimate_fix_minutes(issue: Dict[str, object]) -> int:
        base = {"critical": 90, "high": 60, "medium": 30, "low": 15}.get(issue.get("severity"), 20)
        if issue.get("category") == "security":
            base += 15
        return base

    @staticmethod
    def _calculate_complexity_score(source_text: str) -> int:
        text = source_text or ""
        branch_tokens = re.findall(r"\b(if|elif|else|for|while|case|catch|except|switch|try)\b", text)
        nesting_tokens = text.count("{") + len(re.findall(r"^\s+", text, flags=re.MULTILINE))
        return max(12, min(100, len(branch_tokens) * 6 + min(nesting_tokens // 4, 28)))

    @staticmethod
    def _lesson_focus(issue: Dict[str, object]) -> str:
        category = issue.get("category")
        if category == "security":
            return "Threat model and safe input handling"
        if category == "performance":
            return "Complexity, hotspots, and faster alternatives"
        if category == "logic":
            return "Edge cases and control flow"
        return "Maintainability and code health"

    @staticmethod
    def _enrich_findings(findings: List[Dict[str, object]], source_text: str, input_language: str) -> List[Dict[str, object]]:
        enriched = []
        complexity_score = ScanService._calculate_complexity_score(source_text)
        for finding in findings:
            item = dict(finding)
            item["owasp_category"] = item.get("owasp_category") or ScanService._owasp_for_issue(item)
            item["fix_effort"] = ScanService._infer_fix_effort(item)
            item["fix_time_minutes"] = ScanService._estimate_fix_minutes(item)
            item["complexity_score"] = complexity_score
            item["finding_group"] = item["category"] if item["category"] != "bug" else "quality"
            item["is_secret_leak"] = "secret" in item["title"].lower() or "credential" in item["title"].lower()
            item["teaching_focus"] = ScanService._lesson_focus(item)
            item["attack_prompt"] = f"Simulate how an attacker would exploit {item['title']}."
            item["input_language"] = input_language
            item["explanation_card"] = ScanService._build_explanation_card(item)
            item["attack_simulation"] = ScanService._build_attack_simulation(item)
            item["code_roast"] = ScanService._build_code_roast(item)
            item["hacker_challenge"] = ScanService._build_hacker_challenge(item)
            item["live_simulator"] = ScanService._build_live_simulator(item)
            enriched.append(item)

        return sorted(
            enriched,
            key=lambda issue: (-ScanService._severity_weight(issue["severity"]), -(issue.get("exploit_risk") or 0), issue["title"]),
        )

    @staticmethod
    def _build_overview_tab(findings: List[Dict[str, object]]) -> Dict[str, object]:
        total_fix_time = sum(int(item.get("fix_time_minutes") or 0) for item in findings)
        risk_average = int(mean([int(item.get("exploit_risk") or 0) for item in findings])) if findings else 0
        complexity_score = max([int(item.get("complexity_score") or 0) for item in findings], default=22)
        return {
            "complexity_score": complexity_score,
            "risk_average": risk_average,
            "fix_time_total_minutes": total_fix_time,
            "matrix": [
                {
                    "id": item["id"],
                    "title": item["title"],
                    "risk": int(item.get("exploit_risk") or 0),
                    "effort": {"quick win": 24, "steady fix": 48, "medium lift": 68, "deep fix": 82}.get(item["fix_effort"], 50),
                    "severity": item["severity"],
                }
                for item in findings
            ],
            "priority_queue": [
                {
                    "id": item["id"],
                    "title": item["title"],
                    "priority_label": "Fix now" if item["severity"] in {"critical", "high"} else "Plan next",
                    "fix_time_minutes": item["fix_time_minutes"],
                    "owasp_category": item["owasp_category"],
                }
                for item in findings[:8]
            ],
            "secret_banner": next((item for item in findings if item.get("is_secret_leak")), None),
            "depth_levels": ["ELI5", "Beginner", "Developer", "Expert"],
            "personas": ["student", "startup founder", "security engineer", "staff developer"],
        }

    @staticmethod
    def _build_security_tab(findings: List[Dict[str, object]], source_text: str) -> Dict[str, object]:
        security_findings = []
        for item in findings:
            if item["category"] != "security":
                continue
            enriched = dict(item)
            enriched["attack_example"] = f"An attacker abuses {item['title'].lower()} in {item['file_path']} to reach sensitive behavior."
            enriched["challenge_prompt"] = f"What is the first payload you would try against {item['title']}?"
            enriched["exploit_difficulty"] = max(5, 100 - int(item.get("exploit_risk") or 0))
            security_findings.append(enriched)

        return {
            "threat_warnings": [item["title"] for item in security_findings[:5]],
            "findings": security_findings,
            "source_digest": (source_text or "")[:280],
        }

    @staticmethod
    def _build_map_tab(findings: List[Dict[str, object]], source_text: str) -> Dict[str, object]:
        file_groups = defaultdict(list)
        for item in findings:
            file_groups[item.get("file_path") or "snippet"].append(item)

        heat_map = []
        for file_path, file_findings in file_groups.items():
            severity_score = sum(ScanService._severity_weight(item["severity"]) for item in file_findings)
            heat_map.append(
                {
                    "file_path": file_path,
                    "health_score": max(5, 100 - severity_score * 10),
                    "issue_count": len(file_findings),
                    "dead_code_hint": "unused" in (source_text or "").lower(),
                }
            )

        duplicates = []
        lines = [line.strip() for line in (source_text or "").splitlines() if line.strip()]
        for index, (line, count) in enumerate(Counter(lines).items(), start=1):
            if count > 1 and len(line) > 18:
                duplicates.append({"id": index, "summary": line[:110], "count": count})
            if len(duplicates) >= 6:
                break

        return {
            "heat_map": heat_map,
            "dead_code_detected": "return" in (source_text or "").lower() and "print(" in (source_text or "").lower(),
            "duplicates": duplicates,
        }

    @staticmethod
    def _build_dependencies_tab(source_text: str, findings: List[Dict[str, object]]) -> Dict[str, object]:
        dependency_rows = ScanService._extract_dependency_rows(source_text)[:18]
        findings_by_file = defaultdict(list)
        for item in findings:
            findings_by_file[item.get("file_path") or "snippet"].append(item)

        file_findings = []
        for file_path, file_items in list(findings_by_file.items())[:10]:
            file_findings.append(
                {
                    "file_path": file_path,
                    "issue_count": len(file_items),
                    "top_issue": file_items[0]["title"],
                    "fix_summary": file_items[0].get("fix_suggestion") or "Review the finding details and patch the unsafe path.",
                    "severities": sorted({entry["severity"] for entry in file_items}),
                }
            )

        api_contract_gaps = [
            {
                "endpoint": item.get("file_path") or "snippet",
                "issue": item.get("fix_suggestion") or "Response validation is not clearly enforced before the payload is used.",
            }
            for item in findings
            if "validation" in item["description"].lower() or "api" in item["title"].lower()
        ][:5]

        return {
            "dependency_audit": dependency_rows,
            "dependency_count": len(dependency_rows),
            "manifest_count": len({row["manifest_path"] for row in dependency_rows if row.get("manifest_path")}),
            "insecure_chain": [
                {
                    "package": row["name"],
                    "attack_surface": f"{row['name']} should be reviewed because the current version can widen operational risk and drift.",
                }
                for row in dependency_rows[:5]
            ],
            "api_contract_gaps": api_contract_gaps,
            "outdated_packages": dependency_rows[:5],
            "file_findings": file_findings,
            "scanned_targets": [item["path"] for item in ScanService._split_source_files(source_text)[:12]],
        }

    @staticmethod
    def _build_learn_tab(findings: List[Dict[str, object]], input_language: str) -> Dict[str, object]:
        top_items = findings[:5]
        return {
            "micro_lessons": [
                {
                    "title": item["title"],
                    "lesson": item["teaching_focus"],
                    "story": f"This is a common issue in {input_language} projects when teams move quickly.",
                }
                for item in top_items
            ],
            "quiz": [
                {
                    "question": f"What makes '{item['title']}' risky?",
                    "answer": item["plain_english"] or item["description"],
                }
                for item in top_items
            ],
            "fix_it_yourself": [
                {
                    "finding_id": item["id"],
                    "prompt": f"Rewrite the {input_language} code so it avoids {item['title'].lower()}.",
                    "hint": item["fix_suggestion"],
                }
                for item in top_items
            ],
            "debate_starters": [
                {
                    "finding_id": item["id"],
                    "starter": f"I think '{item['title']}' might be a false positive because...",
                }
                for item in top_items
            ],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "scan_generated",
        }

    @staticmethod
    def _ensure_learn_content(scan: Scan, findings: List[Dict[str, object]], input_language: str) -> Dict[str, object]:
        fallback = ScanService._build_seeded_learn_tab(findings, input_language)
        if scan.learn_content_json:
            try:
                parsed = json.loads(scan.learn_content_json)
                if isinstance(parsed, dict):
                    return ScanService._normalize_learn_tab(parsed, fallback)
            except (TypeError, ValueError):
                pass

        learn_tab = ScanService._generate_learn_content(scan, findings, input_language, force_ai=False)
        scan.learn_content_json = json.dumps(learn_tab)
        db.session.commit()
        return learn_tab

    @staticmethod
    def _generate_learn_content(scan: Scan, findings: List[Dict[str, object]], input_language: str, force_ai: bool) -> Dict[str, object]:
        fallback = ScanService._build_seeded_learn_tab(findings, input_language)
        if not findings:
            return fallback

        if not force_ai:
            return fallback

        prompt = (
            "You are generating a learn tab for a secure code scanning product.\n"
            "Return ONLY JSON with keys micro_lessons, quiz, fix_it_yourself, debate_starters, hacker_challenges, code_roasts, live_attack_labs, generated_at, source.\n"
            "Each value except generated_at/source must be a list. Keep answers concise, beginner-safe, and grounded in the findings.\n"
            f"Language: {input_language}\n"
            f"Scan ID: {scan.api_scan_id}\n"
            f"Findings: {json.dumps(findings[:5])}"
        )
        try:
            from app.services.ai_provider import get_ai_provider_service

            service = get_ai_provider_service()
            raw_text, provider_used = asyncio.run(
                service.generate_text(
                    user_prompt="Generate learn content for this scan.",
                    system_prompt=prompt,
                    preferred_order=["gemini", "groq", "cerebras"],
                )
            )
            candidate = AIProviderService._extract_json_payload(raw_text)
            parsed = json.loads(candidate)
            if not isinstance(parsed, dict):
                raise ValueError("Learn content payload must be an object")
            parsed["generated_at"] = datetime.now(timezone.utc).isoformat()
            parsed["source"] = f"ai_generated:{provider_used}"
            learn_tab = ScanService._normalize_learn_tab(parsed, fallback)
            return learn_tab
        except Exception:
            return {
                **fallback,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source": "seeded",
            }

    @staticmethod
    def _safe_object_list(raw_value: object) -> List[Dict[str, object]]:
        if not isinstance(raw_value, list):
            return []
        return [item for item in raw_value if isinstance(item, dict)]

    @staticmethod
    def _normalize_learn_tab(candidate: Dict[str, object], fallback: Dict[str, object]) -> Dict[str, object]:
        micro_lessons = ScanService._safe_object_list(candidate.get("micro_lessons")) or fallback["micro_lessons"]
        quiz = ScanService._safe_object_list(candidate.get("quiz")) or fallback["quiz"]
        fix_it_yourself = ScanService._safe_object_list(candidate.get("fix_it_yourself")) or fallback["fix_it_yourself"]
        debate_starters = ScanService._safe_object_list(candidate.get("debate_starters")) or fallback["debate_starters"]

        hacker_challenges = ScanService._safe_object_list(candidate.get("hacker_challenges")) or fallback["hacker_challenges"]
        code_roasts = ScanService._safe_object_list(candidate.get("code_roasts")) or fallback["code_roasts"]
        live_attack_labs = ScanService._safe_object_list(candidate.get("live_attack_labs")) or fallback["live_attack_labs"]

        return {
            "micro_lessons": micro_lessons,
            "quiz": quiz,
            "fix_it_yourself": fix_it_yourself,
            "debate_starters": debate_starters,
            "hacker_challenges": hacker_challenges,
            "code_roasts": code_roasts,
            "live_attack_labs": live_attack_labs,
            "generated_at": candidate.get("generated_at") or fallback.get("generated_at") or datetime.now(timezone.utc).isoformat(),
            "source": candidate.get("source") or "seeded",
        }

    @staticmethod
    def _build_seeded_learn_tab(findings: List[Dict[str, object]], input_language: str) -> Dict[str, object]:
        top_items = findings[:5]
        return {
            "micro_lessons": [
                {
                    "finding_id": item["id"],
                    "title": item["title"],
                    "lesson": item["teaching_focus"],
                    "story": f"In {input_language}, this pattern often slips in when teams optimize for speed over validation.",
                    "fact": f"{item['owasp_category']} is a useful reference point for this issue.",
                }
                for item in top_items
            ],
            "quiz": [
                {
                    "question": f"Why is '{item['title']}' risky in this scan?",
                    "answer": item["plain_english"] or item["description"],
                    "difficulty": "beginner" if item["severity"] in {"low", "medium"} else "developer",
                }
                for item in top_items
            ],
            "fix_it_yourself": [
                {
                    "finding_id": item["id"],
                    "prompt": f"Rewrite the {input_language} code path so it avoids {item['title'].lower()}.",
                    "hint": item["fix_suggestion"],
                    "success_criteria": "The risky pattern is removed without changing intended behavior.",
                }
                for item in top_items
            ],
            "debate_starters": [
                {
                    "finding_id": item["id"],
                    "starter": f"I think '{item['title']}' may be a false positive because...",
                    "coach_reply": "Explain which validation, escaping, or guardrail makes you believe the issue is already mitigated.",
                }
                for item in top_items
            ],
            "hacker_challenges": [
                {
                    "finding_id": item["id"],
                    "title": item["title"],
                    "prompt": item["hacker_challenge"]["prompt"],
                    "hint": item["hacker_challenge"]["hint"],
                    "expected_keywords": item["hacker_challenge"]["expected_keywords"],
                    "solution": item["hacker_challenge"]["solution"],
                }
                for item in top_items
            ],
            "code_roasts": [
                {
                    "finding_id": item["id"],
                    "title": item["title"],
                    "gentle": item["code_roast"]["gentle"],
                    "brutal": item["code_roast"]["brutal"],
                    "teaching_point": item["code_roast"]["teaching_point"],
                }
                for item in top_items
            ],
            "live_attack_labs": [
                {
                    "finding_id": item["id"],
                    "title": item["title"],
                    "label": item["live_simulator"]["label"],
                    "placeholder": item["live_simulator"]["placeholder"],
                    "safe_default_payload": item["live_simulator"]["safe_default_payload"],
                    "expected_result": item["live_simulator"]["expected_result"],
                    "impact": item["live_simulator"]["impact"],
                }
                for item in top_items
            ],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "seeded",
        }

    @staticmethod
    def _build_source_overview(scan: Scan, source_text: str) -> Dict[str, object]:
        files = ScanService._split_source_files(source_text)
        payload = ScanService._parse_url_scan_input(scan.input_value) if scan.input_type == "url" else None
        dominant_languages = Counter(
            ScanService.detect_language(item["content"], item["path"]) for item in files
        )
        if "text" in dominant_languages and len(dominant_languages) > 1:
            del dominant_languages["text"]
        return {
            "input_type": scan.input_type,
            "selected_paths": payload["selected_paths"] if payload else [],
            "scan_mode": (
                "entire_repo"
                if payload and payload["scan_entire"]
                else "selected_paths"
                if payload
                else "direct_input"
            ),
            "target_count": len(files),
            "targets": [item["path"] for item in files[:20]],
            "language_breakdown": [
                {"language": language, "count": count}
                for language, count in dominant_languages.most_common(6)
            ],
        }

    @staticmethod
    def _dependency_severity(version: str) -> str:
        cleaned = str(version or "").strip().lstrip("^~>=<")
        if cleaned.startswith("0."):
            return "high"
        if cleaned.startswith("1."):
            return "medium"
        return "low"

    @staticmethod
    def _dependency_fix_hint(name: str, version: str, ecosystem: str) -> str:
        severity = ScanService._dependency_severity(version)
        if severity == "high":
            return f"Prioritize a review of {name} in {ecosystem}; early major versions often need closer upgrade scrutiny."
        if severity == "medium":
            return f"Check whether {name} has a newer maintained release and rerun the scan after upgrading."
        return f"Keep {name} under normal dependency review and pin updates through your {ecosystem} workflow."

    @staticmethod
    def _extract_dependency_rows(source_text: str) -> List[Dict[str, object]]:
        rows = []
        seen = set()
        for file_info in ScanService._split_source_files(source_text):
            path = file_info["path"]
            content = file_info["content"]
            lowered_name = os.path.basename(path).lower()

            if lowered_name == "package.json":
                try:
                    payload = json.loads(content)
                except (TypeError, ValueError):
                    payload = {}
                for section_name in ("dependencies", "devDependencies"):
                    section = payload.get(section_name) or {}
                    if not isinstance(section, dict):
                        continue
                    for name, version in section.items():
                        key = (path, name, str(version))
                        if key in seen:
                            continue
                        seen.add(key)
                        rows.append(
                            {
                                "name": name,
                                "version": str(version),
                                "severity": ScanService._dependency_severity(str(version)),
                                "fix_available": ScanService._dependency_fix_hint(name, str(version), "npm"),
                                "ecosystem": "npm",
                                "manifest_path": path,
                                "section": section_name,
                            }
                        )
                continue

            if lowered_name in {"requirements.txt", "pipfile", "poetry.lock"}:
                for raw_line in content.splitlines():
                    match = re.match(r"^\s*([A-Za-z0-9_.-]+)\s*(?:==|>=|~=|<=)?\s*([0-9][^\s;#]*)", raw_line)
                    if not match:
                        continue
                    name, version = match.groups()
                    key = (path, name, version)
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append(
                        {
                            "name": name,
                            "version": version,
                            "severity": ScanService._dependency_severity(version),
                            "fix_available": ScanService._dependency_fix_hint(name, version, "pip"),
                            "ecosystem": "pip",
                            "manifest_path": path,
                            "section": "dependencies",
                        }
                    )
                continue

            if lowered_name == "pyproject.toml":
                try:
                    payload = tomllib.loads(content)
                except (TypeError, ValueError, tomllib.TOMLDecodeError):
                    payload = {}
                candidates = []
                project = payload.get("project") or {}
                candidates.extend(project.get("dependencies") or [])
                poetry = (((payload.get("tool") or {}).get("poetry") or {}).get("dependencies") or {})
                if isinstance(poetry, dict):
                    for dep_name, dep_value in poetry.items():
                        if dep_name.lower() == "python":
                            continue
                        version = dep_value if isinstance(dep_value, str) else dep_value.get("version", "*")
                        candidates.append(f"{dep_name} {version}")
                for raw_line in candidates:
                    match = re.match(r"^\s*([A-Za-z0-9_.-]+).{0,6}?([0-9][A-Za-z0-9+_.-]*)", str(raw_line))
                    if not match:
                        continue
                    name, version = match.groups()
                    key = (path, name, version)
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append(
                        {
                            "name": name,
                            "version": version,
                            "severity": ScanService._dependency_severity(version),
                            "fix_available": ScanService._dependency_fix_hint(name, version, "python"),
                            "ecosystem": "python",
                            "manifest_path": path,
                            "section": "dependencies",
                        }
                    )
                continue

            if lowered_name == "go.mod":
                for match in re.finditer(r"^\s*([A-Za-z0-9./_-]+)\s+v([0-9][^\s]*)", content, flags=re.MULTILINE):
                    name, version = match.groups()
                    key = (path, name, version)
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append(
                        {
                            "name": name,
                            "version": version,
                            "severity": ScanService._dependency_severity(version),
                            "fix_available": ScanService._dependency_fix_hint(name, version, "go"),
                            "ecosystem": "go",
                            "manifest_path": path,
                            "section": "require",
                        }
                    )
                continue

            if lowered_name == "cargo.toml":
                for match in re.finditer(r"^\s*([A-Za-z0-9_.-]+)\s*=\s*\"([^\"]+)\"", content, flags=re.MULTILINE):
                    name, version = match.groups()
                    if name.lower() in {"package", "version", "edition"}:
                        continue
                    key = (path, name, version)
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append(
                        {
                            "name": name,
                            "version": version,
                            "severity": ScanService._dependency_severity(version),
                            "fix_available": ScanService._dependency_fix_hint(name, version, "cargo"),
                            "ecosystem": "cargo",
                            "manifest_path": path,
                            "section": "dependencies",
                        }
                    )
                continue

            for pattern in (
                r"^([A-Za-z0-9_.-]+)==([0-9][^\s]*)$",
                r"\"([A-Za-z0-9_.-]+)\"\s*:\s*\"([~^]?[0-9][^\"]*)\"",
            ):
                for match in re.finditer(pattern, content or "", flags=re.MULTILINE):
                    name, version = match.groups()
                    key = (path, name, version)
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append(
                        {
                            "name": name,
                            "version": version,
                            "severity": ScanService._dependency_severity(version),
                            "fix_available": ScanService._dependency_fix_hint(name, version, "manifest"),
                            "ecosystem": "manifest",
                            "manifest_path": path,
                            "section": "dependencies",
                        }
                    )
        return rows

    @staticmethod
    def _comment_prefix(language: str) -> str:
        return "#" if language in {"python", "yaml"} else "//"

    @staticmethod
    def _build_explanation_card(issue: Dict[str, object]) -> Dict[str, object]:
        return {
            "plain_english": issue.get("plain_english") or issue.get("description") or "This pattern makes the code easier to misuse.",
            "why_it_matters": (
                f"This issue is marked {issue.get('severity', 'medium')} because it can affect "
                f"{'security boundaries' if issue.get('category') == 'security' else 'runtime correctness'}."
            ),
            "next_step": issue.get("fix_suggestion") or "Apply validation, safer APIs, and targeted tests.",
        }

    @staticmethod
    def _build_attack_simulation(issue: Dict[str, object]) -> Dict[str, object]:
        title = str(issue.get("title") or "").lower()
        is_xss = "xss" in title or "script" in title
        payload = "<script>alert(1)</script>" if is_xss else "' OR '1'='1"
        return {
            "payload": payload,
            "entry_point": issue.get("file_path") or "snippet",
            "steps": [
                "Find the input that reaches the vulnerable code path.",
                f"Send a crafted payload like {payload}.",
                "Observe how the application changes behavior when that input is trusted.",
            ],
            "result": (
                "The browser would execute attacker-controlled script."
                if is_xss
                else "The query logic can be altered so authorization or filtering is bypassed."
            ),
            "impact": issue.get("plain_english") or issue.get("description") or "Unsafe input handling can change program behavior.",
        }

    @staticmethod
    def _build_code_roast(issue: Dict[str, object]) -> Dict[str, object]:
        title = issue.get("title") or "This finding"
        plain = issue.get("plain_english") or issue.get("description") or "The code trusts input too early."
        return {
            "gentle": f"{title} is a good reminder that convenience code still needs a safety rail.",
            "brutal": f"{title} is basically the codebase hanging out a 'free bugs here' sign. {plain}",
            "teaching_point": issue.get("fix_suggestion") or "Replace the unsafe pattern with a constrained API.",
        }

    @staticmethod
    def _build_hacker_challenge(issue: Dict[str, object]) -> Dict[str, object]:
        title = str(issue.get("title") or "").lower()
        if any(keyword in title for keyword in ("sql", "injection", "parameterized", "select ", "query")):
            return {
                "prompt": "What short payload could bend the SQL query logic without crashing the app?",
                "hint": "Think about quotes, boolean logic, and how string-built queries behave.",
                "expected_keywords": ["'", "or", "1=1"],
                "solution": "A classic example is `' OR '1'='1`, which can turn a restrictive WHERE clause into a permissive one.",
            }
        if "xss" in title:
            return {
                "prompt": "What payload would prove the page is rendering unsafe HTML or script?",
                "hint": "Use a tiny harmless browser-visible script marker.",
                "expected_keywords": ["<script", "alert"],
                "solution": "A demo payload like `<script>alert(1)</script>` is enough to prove the browser would execute attacker input.",
            }
        return {
            "prompt": f"What unsafe input would you try first against {issue.get('title', 'this code path')}?",
            "hint": "Start with the smallest payload that changes control flow or output.",
            "expected_keywords": ["input", "payload"],
            "solution": issue.get("fix_suggestion") or "Look for an input that reaches a privileged operation without validation.",
        }

    @staticmethod
    def _build_live_simulator(issue: Dict[str, object]) -> Dict[str, object]:
        title = str(issue.get("title") or "").lower()
        if "xss" in title:
            return {
                "label": "Browser payload sandbox",
                "placeholder": "<script>alert(1)</script>",
                "safe_default_payload": "<img src=x onerror=alert(1) />",
                "expected_result": "Unsafe rendering would execute the payload in the browser context.",
                "impact": "An attacker could steal sessions, deface content, or act as the user.",
            }
        if "pickle" in title or "deserialize" in title:
            return {
                "label": "Deserializer payload sandbox",
                "placeholder": "gASV...crafted_pickle_payload...",
                "safe_default_payload": "pickle.loads(attacker_controlled_bytes)",
                "expected_result": "Unsafe deserialization can execute attacker-controlled behavior during object loading.",
                "impact": "An attacker could trigger unexpected code paths and potentially execute arbitrary actions.",
            }
        if any(keyword in title for keyword in ("secret", "password", "token", "credential")):
            return {
                "label": "Secret exposure sandbox",
                "placeholder": "grep -R \"secret\" .",
                "safe_default_payload": "SECRET_KEY=dev-secret-123",
                "expected_result": "Hardcoded secrets are easy to leak through logs, repos, and screenshots.",
                "impact": "An attacker who obtains the secret can impersonate users or decrypt protected data.",
            }
        if any(keyword in title for keyword in ("command", "shell", "subprocess")):
            return {
                "label": "Command payload sandbox",
                "placeholder": "; cat /etc/passwd",
                "safe_default_payload": "&& whoami",
                "expected_result": "Unsafe command execution would treat payload text as shell instructions.",
                "impact": "An attacker could run commands on the host and pivot deeper into the environment.",
            }
        return {
            "label": "Query payload sandbox",
            "placeholder": "' OR '1'='1",
            "safe_default_payload": "' UNION SELECT 'admin','token' --",
            "expected_result": "Unsafe query construction would treat attacker input as executable query logic.",
            "impact": "An attacker could bypass filters, read data, or alter rows they should not control.",
        }

    @staticmethod
    def _build_fix_guidance(issue: Dict[str, object], language: str, suggestion: str) -> Tuple[List[str], List[str], List[str]]:
        del language
        title = " ".join(
            [
                str(issue.get("title") or ""),
                str(issue.get("description") or ""),
                str(issue.get("plain_english") or ""),
                str(issue.get("fix_suggestion") or ""),
                suggestion or "",
            ]
        ).lower()
        summary: List[str] = []
        rationale: List[str] = []
        edit_hints: List[str] = []

        if "sql" in title or "injection" in title:
            summary = [
                "Stop building the query with string interpolation.",
                "Move user-controlled data into query parameters.",
                "Keep the SQL text static so the database treats the input as data, not syntax.",
            ]
            rationale = [
                "Parameterized queries neutralize quote-breaking and boolean-bypass payloads.",
                "Static query strings are easier to test and audit.",
            ]
            edit_hints = [
                "Find the variable inserted into the query string and pass it separately to execute/query.",
                "If multiple parameters exist, preserve their order in the placeholder tuple or array.",
            ]
        elif "credential" in title or "password" in title or "secret" in title:
            summary = [
                "Remove the secret from source control.",
                "Load it from an environment variable or secret manager at runtime.",
                "Fail fast with a clear error if the secret is missing.",
            ]
            rationale = [
                "Secrets in source leak through git history, logs, and screenshots.",
                "Runtime injection keeps rotation and environment separation practical.",
            ]
            edit_hints = [
                "Choose an env var name that matches the purpose, such as APP_PASSWORD or API_TOKEN.",
                "Add a short error message telling teammates where the secret should come from.",
            ]
        elif "dynamic code execution" in title or "eval" in title:
            summary = [
                "Replace dynamic code execution with parsing or a strict allowlist.",
                "Treat incoming text as data, not executable instructions.",
            ]
            rationale = [
                "eval/exec turns input handling into remote code execution risk.",
            ]
            edit_hints = [
                "For Python literals, prefer ast.literal_eval over eval when the input format is limited.",
                "For command-like features, map allowed tokens to explicit functions.",
            ]
        else:
            summary = [
                suggestion or "Apply the secure coding guidance for this finding.",
                "Add a targeted regression test around the unsafe path.",
            ]
            rationale = [
                "The fix should remove the risky behavior and lock it down with a test.",
            ]
            edit_hints = [
                "Preserve surrounding behavior and change only the risky path first.",
            ]

        return summary, rationale, edit_hints

    @staticmethod
    def _build_fixed_code(before: str, issue: Dict[str, object], language: str, suggestion: str, rationale: List[str]) -> str:
        if not before:
            prefix = ScanService._comment_prefix(language)
            lines = [f"{prefix} No original snippet was captured for this finding."]
            lines.extend(f"{prefix} {item}" for item in rationale)
            return "\n".join(lines)

        title = " ".join(
            [
                str(issue.get("title") or ""),
                str(issue.get("description") or ""),
                str(issue.get("plain_english") or ""),
                str(issue.get("fix_suggestion") or ""),
                suggestion or "",
                before,
            ]
        ).lower()
        fixed = before

        if any(keyword in title for keyword in ("sql", "injection", "parameterized", "select ", "query")) and language == "python":
            fixed = ScanService._rewrite_python_sql_injection(before)
        elif any(keyword in title for keyword in ("sql", "injection", "parameterized", "select ", "query")) and language in {"javascript", "typescript"}:
            fixed = ScanService._rewrite_js_sql_injection(before)
        elif any(keyword in title for keyword in ("credential", "password", "secret")):
            fixed = ScanService._rewrite_hardcoded_secret(before, language)
        elif "dynamic code execution" in title or "eval" in title:
            fixed = ScanService._rewrite_dynamic_execution(before, language)
        elif "exception" in title or "except" in before.lower():
            fixed = ScanService._rewrite_broad_exception(before, language)

        if fixed.strip() == before.strip():
            prefix = ScanService._comment_prefix(language)
            guidance = [f"{prefix} Fix intent: {suggestion or issue.get('fix_suggestion') or 'Apply safer validation and constrained APIs.'}"]
            guidance.extend(f"{prefix} {item}" for item in rationale)
            guidance.append(before)
            fixed = "\n".join(guidance)

        return fixed

    @staticmethod
    def _rewrite_python_sql_injection(before: str) -> str:
        variable = ScanService._infer_interpolated_variable(before) or "user_input"
        query_match = re.search(r"SELECT .*", before, flags=re.IGNORECASE)
        query_text = query_match.group(0).strip() if query_match else "SELECT * FROM users WHERE id = %s"
        query_text = re.sub(r"\{[^}]+\}", "%s", query_text)
        query_text = query_text.replace("%s%s", "%s")
        lines = []
        for line in before.splitlines():
            stripped = line.strip()
            if stripped.startswith("query ="):
                indent = line[: len(line) - len(line.lstrip())]
                lines.append(f'{indent}query = "{query_text}"')
                continue
            if ".execute(" in stripped:
                indent = line[: len(line) - len(line.lstrip())]
                target = stripped.split(".execute(", 1)[0] or "cursor"
                lines.append(f"{indent}{target}.execute(query, ({variable},))")
                continue
            lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def _rewrite_js_sql_injection(before: str) -> str:
        variable = ScanService._infer_interpolated_variable(before) or "userInput"
        query_match = re.search(r"SELECT .*", before, flags=re.IGNORECASE)
        query_text = query_match.group(0).strip() if query_match else "SELECT * FROM users WHERE id = ?"
        query_text = re.sub(r"\$\{[^}]+\}", "?", query_text)
        lines = []
        for line in before.splitlines():
            stripped = line.strip()
            if "const query" in stripped or "let query" in stripped or stripped.startswith("query ="):
                indent = line[: len(line) - len(line.lstrip())]
                keyword = "const" if "const " in stripped else "let" if "let " in stripped else "const"
                lines.append(f'{indent}{keyword} query = "{query_text}";')
                continue
            if ".query(" in stripped or ".execute(" in stripped:
                indent = line[: len(line) - len(line.lstrip())]
                if ".query(" in stripped:
                    target = stripped.split(".query(", 1)[0] or "db"
                    lines.append(f"{indent}{target}.query(query, [{variable}]);")
                else:
                    target = stripped.split(".execute(", 1)[0] or "db"
                    lines.append(f"{indent}{target}.execute(query, [{variable}]);")
                continue
            lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def _rewrite_hardcoded_secret(before: str, language: str) -> str:
        env_name = "APP_SECRET"
        if "password" in before.lower():
            env_name = "APP_PASSWORD"
        replacement = f'os.getenv("{env_name}")' if language == "python" else f"process.env.{env_name}"
        updated = re.sub(r"=\s*([\"']).+?\1", f" = {replacement}", before, count=1)
        if language == "python" and "os.getenv" in updated and "import os" not in updated:
            updated = f"import os\n{updated}"
        return updated

    @staticmethod
    def _rewrite_dynamic_execution(before: str, language: str) -> str:
        if language == "python":
            updated = before.replace("eval(", "ast.literal_eval(")
            if updated != before and "import ast" not in updated:
                updated = f"import ast\n{updated}"
            return updated
        return before.replace("eval(", "safeEvaluate(")

    @staticmethod
    def _rewrite_broad_exception(before: str, language: str) -> str:
        if language != "python":
            return before
        updated = re.sub(r"except\s*:\s*$", "except Exception as exc:", before, flags=re.MULTILINE)
        if updated != before and "logger." not in updated:
            updated = updated.replace(
                "except Exception as exc:",
                'except Exception as exc:\n    logger.exception("Unexpected failure during secure operation")\n    raise',
                1,
            )
        return updated

    @staticmethod
    def _infer_interpolated_variable(before: str) -> Optional[str]:
        match = re.search(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", before)
        if match:
            return match.group(1)
        concat_match = re.search(r"\+\s*([A-Za-z_][A-Za-z0-9_]*)", before)
        if concat_match:
            return concat_match.group(1)
        return None

    @staticmethod
    def _guess_snippet_language(before: str) -> str:
        snippet = before or ""
        if "cursor.execute" in snippet or "conn.cursor" in snippet or 'f"' in snippet:
            return "python"
        if "const " in snippet or "let " in snippet or "=>" in snippet:
            return "javascript"
        return "text"

    @staticmethod
    def _compute_diff_stats(before: str, after: str) -> Dict[str, int]:
        before_lines = before.splitlines()
        after_lines = after.splitlines()
        matcher = SequenceMatcher(a=before_lines, b=after_lines)
        added = 0
        removed = 0
        changed = 0
        for opcode, a0, a1, b0, b1 in matcher.get_opcodes():
            if opcode == "insert":
                added += b1 - b0
            elif opcode == "delete":
                removed += a1 - a0
            elif opcode == "replace":
                changed += max(a1 - a0, b1 - b0)
        return {
            "before_lines": len(before_lines),
            "after_lines": len(after_lines),
            "added_lines": added,
            "removed_lines": removed,
            "changed_lines": changed,
        }

    @staticmethod
    def _build_chat_starters(findings: List[Dict[str, object]]) -> List[Dict[str, str]]:
        starters = [
            {"label": "What should I fix first?", "message": "What should I fix first and why?"},
            {"label": "Explain simply", "message": "Explain the highest-risk issue like I'm a student."},
        ]
        if findings:
            top = findings[0]
            starters.extend(
                [
                    {"label": "Show safest fix", "message": f"Show me the safest fix for {top['title']} step by step."},
                    {"label": "Simulate attack", "message": f"Simulate how an attacker would exploit {top['title']}."},
                ]
            )
        return starters

    @staticmethod
    def _build_executive_summary(scan: Scan, findings: List[Dict[str, object]], overview: Dict[str, object]) -> Dict[str, object]:
        return {
            "headline": f"Code health score is {scan.health_score or 0}/100",
            "verdict": "Needs attention" if (scan.health_score or 0) < 80 else "Generally healthy",
            "top_risks": [
                {
                    "title": item["title"],
                    "severity": item["severity"],
                    "impact": item["plain_english"] or item["description"],
                }
                for item in findings[:3]
            ],
            "plain_english": f"This scan found {len(findings)} issue(s). Estimated fix time is about {overview['fix_time_total_minutes']} minutes.",
        }

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
