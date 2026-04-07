import asyncio
import sys
import types

import pytest


if "google.generativeai" not in sys.modules:
    google_module = types.ModuleType("google")
    generativeai_module = types.ModuleType("google.generativeai")

    class _DummyGenerativeModel:
        def __init__(self, *_args, **_kwargs):
            pass

        def generate_content(self, *_args, **_kwargs):
            class _Resp:
                text = '{"issues": [], "health_score": 80, "pros": [], "cons": []}'

            return _Resp()

    def _dummy_configure(**_kwargs):
        return None

    generativeai_module.GenerativeModel = _DummyGenerativeModel
    generativeai_module.configure = _dummy_configure
    google_module.generativeai = generativeai_module
    sys.modules["google"] = google_module
    sys.modules["google.generativeai"] = generativeai_module

if "groq" not in sys.modules:
    groq_module = types.ModuleType("groq")

    class _DummyGroq:
        def __init__(self, *_args, **_kwargs):
            pass

    groq_module.Groq = _DummyGroq
    sys.modules["groq"] = groq_module

if "huggingface_hub" not in sys.modules:
    hf_module = types.ModuleType("huggingface_hub")

    class _DummyInferenceClient:
        def __init__(self, *_args, **_kwargs):
            pass

    hf_module.InferenceClient = _DummyInferenceClient
    sys.modules["huggingface_hub"] = hf_module

from app.services.ai_provider import (
    AIAnalysisError,
    AIProviderResponseError,
    AIProviderService,
)


def test_parse_response_handles_json_fence_and_normalizes_fields():
    response = """
```json
{
  "issues": [
    {
      "title": "SQL Injection",
      "description": "raw",
      "plain_english": "plain",
      "severity": "INVALID",
      "category": "oops",
      "file_path": "app.py",
      "line_number": "12",
      "fix_suggestion": "Use parameters",
      "exploit_risk": "120",
      "cwe_id": "CWE-89"
    }
  ],
  "health_score": 101,
  "pros": ["A", "  ", null],
  "cons": ["B"],
  "refactor_suggestions": ["C"]
}
```
"""

    parsed = AIProviderService._parse_response(response)

    assert parsed["health_score"] == 100
    assert parsed["pros"] == ["A"]
    assert parsed["cons"] == ["B"]
    assert parsed["refactor_suggestions"] == ["C"]
    assert parsed["issues"][0]["severity"] == "medium"
    assert parsed["issues"][0]["category"] == "security"
    assert parsed["issues"][0]["exploit_risk"] == 100


def test_parse_response_rejects_missing_required_fields():
    with pytest.raises(AIProviderResponseError):
        AIProviderService._parse_response('{"issues": [], "health_score": 80}')


def test_retryable_error_detection_and_backoff():
    service = AIProviderService()

    assert service._is_retryable_error(asyncio.TimeoutError()) is True
    assert service._is_retryable_error(RuntimeError("rate limit exceeded")) is True
    assert service._is_retryable_error(RuntimeError("missing required fields")) is False
    assert service._get_backoff_delay("groq", 1) == 1
    assert service._get_backoff_delay("groq", 2) == 2


def test_analyze_code_falls_back_to_next_provider(monkeypatch):
    service = AIProviderService()
    service.provider_order = ["groq", "gemini"]

    def _available(_provider_name):
        return True

    attempts = {"count": 0}

    async def _fake_call(provider_name, _code_chunk, _system_prompt, _scan_id):
        attempts["count"] += 1
        if provider_name == "groq":
            raise RuntimeError("rate limit")
        return {
            "issues": [],
            "health_score": 90,
            "pros": [],
            "cons": [],
            "refactor_suggestions": [],
        }

    monkeypatch.setattr(service, "_is_provider_available", _available)
    monkeypatch.setattr(service, "_call_provider_with_retry", _fake_call)

    result, provider = asyncio.run(service.analyze_code("print(1)", "prompt", 1))

    assert provider == "gemini"
    assert result["health_score"] == 90
    assert attempts["count"] == 2


def test_analyze_code_raises_when_all_providers_fail(monkeypatch):
    service = AIProviderService()
    service.provider_order = ["groq"]

    monkeypatch.setattr(service, "_is_provider_available", lambda _name: True)

    async def _always_fail(*_args, **_kwargs):
        raise RuntimeError("provider down")

    monkeypatch.setattr(service, "_call_provider_with_retry", _always_fail)

    with pytest.raises(AIAnalysisError):
        asyncio.run(service.analyze_code("print(1)", "prompt", 2))
