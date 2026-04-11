import asyncio
import hashlib
import json
import logging
import os
import re
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from statistics import mean
from typing import Dict, List, Optional

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
            github_service = GitHubService(token=os.getenv("GITHUB_TOKEN"))
            snapshot = github_service.fetch_repository_snapshot(scan.input_value)
            return snapshot["content"]

        return scan.input_value or ""

    @staticmethod
    def normalize_language(raw_language: Optional[str]) -> str:
        normalized = str(raw_language or "").strip().lower()
        aliases = {"py": "python", "js": "javascript", "ts": "typescript", "tsx": "typescript", "golang": "go"}
        return aliases.get(normalized, normalized or "text")

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
        before = finding.code_snippet or ""
        language = ScanService.normalize_language(scan.input_language)
        comment_prefix = "#" if language in {"python", "yaml"} else "//"

        intro = f"{comment_prefix} Suggested fix for: {finding.title}"
        guidance = suggestion or "Apply the secure coding guidance for this finding."

        if before:
            after = (
                f"{intro}\n"
                f"{comment_prefix} {guidance}\n"
                f"{comment_prefix} Review and adapt to your full file context before applying.\n"
                f"{before}"
            )
        else:
            after = (
                f"{intro}\n"
                f"{comment_prefix} {guidance}\n"
                f"{comment_prefix} Original code snippet was not available in scan results."
            )

        return {
            "scan_id": scan.api_scan_id,
            "finding_id": finding.id,
            "before": before,
            "after": after,
            "language": language,
            "message": "Fix preview generated from scan finding metadata.",
            "source": "scan_finding",
        }

    @staticmethod
    def build_results_payload(scan):
        source_text = ScanService._resolve_scan_input(scan)
        input_language = ScanService.normalize_language(scan.input_language)
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
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for finding in enriched:
            severity_counts[finding["severity"]] += 1

        overview = ScanService._build_overview_tab(enriched)
        security_tab = ScanService._build_security_tab(enriched, source_text)
        map_tab = ScanService._build_map_tab(enriched, source_text)
        dependencies_tab = ScanService._build_dependencies_tab(source_text, enriched)
        learn_tab = ScanService._ensure_learn_content(scan, enriched, input_language)

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
        input_language = ScanService.normalize_language(scan.input_language)
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
            enriched["live_simulator"] = {
                "label": "Payload sandbox",
                "placeholder": "<script>alert(1)</script>" if "xss" in item["title"].lower() else "' OR '1'='1",
                "expected_result": "This demo shows how untrusted input can change runtime behavior.",
            }
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
        dependency_rows = []
        patterns = [
            r"^([A-Za-z0-9_.-]+)==([0-9][^\s]*)$",
            r"\"([A-Za-z0-9_.-]+)\"\s*:\s*\"([~^]?[0-9][^\"]*)\"",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, source_text or "", flags=re.MULTILINE):
                name, version = match.groups()
                dependency_rows.append(
                    {
                        "name": name,
                        "version": version,
                        "severity": "high" if version.startswith(("0.", "1.")) else "medium",
                        "fix_available": "Review the latest stable release",
                    }
                )
        dependency_rows = dependency_rows[:10]

        api_contract_gaps = [
            {
                "endpoint": item.get("file_path") or "snippet",
                "issue": "Response validation is not clearly enforced before the payload is used.",
            }
            for item in findings
            if "validation" in item["description"].lower() or "api" in item["title"].lower()
        ][:5]

        return {
            "dependency_audit": dependency_rows,
            "insecure_chain": [
                {
                    "package": row["name"],
                    "attack_surface": f"{row['name']} expands the attack surface until it is reviewed and upgraded.",
                }
                for row in dependency_rows[:5]
            ],
            "api_contract_gaps": api_contract_gaps,
            "outdated_packages": dependency_rows[:5],
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
        if scan.learn_content_json:
            try:
                parsed = json.loads(scan.learn_content_json)
                if isinstance(parsed, dict):
                    return parsed
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
            "Return ONLY JSON with keys micro_lessons, quiz, fix_it_yourself, debate_starters, generated_at, source.\n"
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
                    preferred_order=["groq", "gemini"],
                )
            )
            candidate = AIProviderService._extract_json_payload(raw_text)
            parsed = json.loads(candidate)
            if not isinstance(parsed, dict):
                raise ValueError("Learn content payload must be an object")
            learn_tab = {
                "micro_lessons": parsed.get("micro_lessons") or fallback["micro_lessons"],
                "quiz": parsed.get("quiz") or fallback["quiz"],
                "fix_it_yourself": parsed.get("fix_it_yourself") or fallback["fix_it_yourself"],
                "debate_starters": parsed.get("debate_starters") or fallback["debate_starters"],
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source": f"ai_generated:{provider_used}",
            }
            return learn_tab
        except Exception:
            return {
                **fallback,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source": "seeded",
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
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "seeded",
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
