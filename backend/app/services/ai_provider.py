
import asyncio
import importlib
import json
import logging
import os
from time import perf_counter
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


class AIProviderConfig:
    """Configuration for each AI provider."""

    PROVIDERS = {
        "groq": {
            "name": "Groq",
            "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            "max_tokens": 8192,
            "timeout": 30,
            "retry_count": 3,
            "api_key_env": "GROQ_API_KEY",
        },
        "cerebras": {
            "name": "Cerebras",
            "model": os.getenv("CEREBRAS_MODEL", "llama3.1-8b"),
            "max_tokens": 8192,
            "timeout": 30,
            "retry_count": 3,
            "api_key_env": "CEREBRAS_API_KEY",
            "available_models": [
                {
                    "id": "llama3.1-8b",
                    "best_for": "Fast responses, chat, simple tasks",
                },
                {
                    "id": "qwen-3-235b-a22b-instruct-2507",
                    "best_for": "Complex reasoning, long context (65k tokens), slower",
                },
            ],
        },
        "gemini": {
            "name": "Google Gemini",
            "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            "max_tokens": 8192,
            "timeout": 35,
            "retry_count": 2,
            "api_key_env": "GEMINI_API_KEY",
        },
        "llama": {
            "name": "Meta Llama 2",
            "model": "meta-llama/llama-2-70b-chat-hf",
            "max_tokens": 4096,
            "timeout": 60,
            "retry_count": 1,
            "api_key_env": "HUGGING_FACE_API_KEY",
        },
    }

    TEMPERATURE = 0.2  # Low creativity for deterministic responses
    DEFAULT_PROVIDER_ORDER = ["gemini", "groq", "cerebras", "llama"]
    RETRY_BACKOFF_BASE = {
        "groq": 1,
        "cerebras": 1,
        "gemini": 2,
        "llama": 2,
    }
    REQUIRED_RESPONSE_FIELDS = ("issues", "health_score", "pros", "cons")
    VALID_SEVERITIES = {"critical", "high", "medium", "low"}
    VALID_CATEGORIES = {"security", "bug", "performance", "logic"}


class AIProviderService:
    """Main service for multi-provider AI analysis with fallback strategy."""

    def __init__(self):
        """Initialize all provider clients."""
        self.groq_client = None
        self.genai_client = None
        self.hf_client = None
        self.groq_api_key = None
        self.cerebras_api_key = None
        self.gemini_api_key = None
        self.hf_api_key = None
        self.provider_order = self._get_provider_order()
        self._init_providers()
        logger.info(
            "AI provider service initialized. order=%s available=%s",
            self.provider_order,
            self._list_available_providers(),
        )

    def _init_providers(self):
        """Initialize all available provider clients."""
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        if self.groq_api_key:
            try:
                groq_module = importlib.import_module("groq")
                self.groq_client = groq_module.Groq(api_key=self.groq_api_key)
                logger.info("Groq client initialized")
            except Exception as exc:
                logger.warning(
                    "Groq SDK client unavailable, HTTP fallback will be used: %s",
                    exc,
                )

        self.cerebras_api_key = os.getenv("CEREBRAS_API_KEY")

        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if self.gemini_api_key:
            try:
                genai_module = importlib.import_module("google.generativeai")
                genai_module.configure(api_key=self.gemini_api_key)
                self.genai_client = genai_module
                logger.info("Google Gemini client initialized")
            except Exception as exc:
                logger.warning(
                    "Gemini SDK client unavailable, HTTP fallback will be used: %s",
                    exc,
                )

        self.hf_api_key = os.getenv("HUGGING_FACE_API_KEY")
        if self.hf_api_key:
            try:
                hf_module = importlib.import_module("huggingface_hub")
                # huggingface-hub versions differ across token/api_key kwargs
                try:
                    self.hf_client = hf_module.InferenceClient(token=self.hf_api_key)
                except TypeError:
                    self.hf_client = hf_module.InferenceClient(api_key=self.hf_api_key)
                logger.info("Hugging Face Llama client initialized")
            except Exception as exc:
                logger.warning(
                    "Hugging Face SDK client unavailable, HTTP fallback will be used: %s",
                    exc,
                )

    def _list_available_providers(self) -> List[str]:
        """Return a list of configured providers with initialized clients."""
        available = []
        for provider_name in AIProviderConfig.PROVIDERS:
            if self._is_provider_available(provider_name):
                available.append(provider_name)
        return available

    def provider_status(self) -> Dict[str, Dict[str, Any]]:
        return {
            provider_name: {
                "configured": self._is_provider_available(provider_name),
                "model": AIProviderConfig.PROVIDERS[provider_name]["model"],
                "name": AIProviderConfig.PROVIDERS[provider_name]["name"],
                "available_models": AIProviderConfig.PROVIDERS[provider_name].get(
                    "available_models", []
                ),
            }
            for provider_name in AIProviderConfig.PROVIDERS
        }

    def _is_provider_available(self, provider_name: str) -> bool:
        """Check if a provider client is initialized and available for use."""
        if provider_name == "groq":
            return bool(self.groq_api_key)
        if provider_name == "cerebras":
            return bool(self.cerebras_api_key)
        if provider_name == "gemini":
            return bool(self.gemini_api_key)
        if provider_name == "llama":
            return bool(self.hf_api_key)
        return False

    def _get_provider_order(self) -> List[str]:
        """Get provider order from config or use default."""
        order_str = os.getenv("AI_PROVIDER_ORDER")
        requested_order = (
            [p.strip().lower() for p in order_str.split(",") if p.strip()]
            if order_str
            else list(AIProviderConfig.DEFAULT_PROVIDER_ORDER)
        )

        normalized_order = []
        for provider_name in requested_order:
            if provider_name in normalized_order:
                continue
            if provider_name not in AIProviderConfig.PROVIDERS:
                logger.warning(
                    "Unknown provider '%s' in AI_PROVIDER_ORDER. Skipping.",
                    provider_name,
                )
                continue
            normalized_order.append(provider_name)

        if not normalized_order:
            logger.warning(
                "No valid providers found in AI_PROVIDER_ORDER. Using default order."
            )
            return list(AIProviderConfig.DEFAULT_PROVIDER_ORDER)

        return normalized_order

    async def analyze_code(
        self, code_chunk: str, system_prompt: str, scan_id: Optional[int] = None
    ) -> Tuple[Dict, str]:
        """
        Analyze code using multi-provider fallback system.

        Args:
            code_chunk: Code to analyze
            system_prompt: System prompt for AI
            scan_id: Optional scan ID for logging

        Returns:
            Tuple of (analysis_result_dict, provider_used_name)

        Raises:
            AIAnalysisError: If all providers fail
        """
        if not code_chunk or not code_chunk.strip():
            raise ValueError("code_chunk must be a non-empty string")
        if not system_prompt or not system_prompt.strip():
            raise ValueError("system_prompt must be a non-empty string")

        provider_errors = []

        for provider_name in self.provider_order:
            if not self._is_provider_available(provider_name):
                logger.warning(
                    "[Scan %s] Provider %s is not configured, skipping.",
                    scan_id,
                    provider_name,
                )
                continue

            started_at = perf_counter()
            try:
                logger.info(
                    "[Scan %s] Attempting analysis with %s...",
                    scan_id,
                    provider_name,
                )
                result = await self._call_provider_with_retry(
                    provider_name,
                    code_chunk,
                    system_prompt,
                    scan_id,
                )
                elapsed = perf_counter() - started_at
                logger.info(
                    "[Scan %s] Analysis successful with %s in %.2fs",
                    scan_id,
                    provider_name,
                    elapsed,
                )
                return result, provider_name

            except Exception as exc:  # Fallback to the next provider
                elapsed = perf_counter() - started_at
                error_msg = f"{provider_name} error: {str(exc)}"
                provider_errors.append(error_msg)
                logger.warning(
                    "[Scan %s] %s after %.2fs, trying fallback...",
                    scan_id,
                    error_msg,
                    elapsed,
                )
                continue

        if not provider_errors:
            provider_errors.append("No configured AI providers are available")

        error_msg = "All AI providers failed. " + " | ".join(provider_errors[-3:])
        logger.error("[Scan %s] %s", scan_id, error_msg)
        raise AIAnalysisError(error_msg)

    async def generate_text(
        self,
        user_prompt: str,
        system_prompt: str,
        preferred_order: Optional[List[str]] = None,
    ) -> Tuple[str, str]:
        if not user_prompt or not user_prompt.strip():
            raise ValueError("user_prompt must be a non-empty string")
        if not system_prompt or not system_prompt.strip():
            raise ValueError("system_prompt must be a non-empty string")

        order = preferred_order or self.provider_order
        provider_errors = []
        for provider_name in order:
            if provider_name not in AIProviderConfig.PROVIDERS:
                continue
            if not self._is_provider_available(provider_name):
                continue

            config = AIProviderConfig.PROVIDERS[provider_name]
            timeout = config["timeout"]
            try:
                if provider_name == "groq":
                    text = await self._call_groq_text(user_prompt, system_prompt, timeout)
                elif provider_name == "cerebras":
                    text = await self._call_cerebras_text(
                        user_prompt,
                        system_prompt,
                        timeout,
                    )
                elif provider_name == "gemini":
                    text = await self._call_gemini_text(user_prompt, system_prompt, timeout)
                elif provider_name == "llama":
                    text = await self._call_llama_text(user_prompt, system_prompt, timeout)
                else:
                    continue

                if text and text.strip():
                    return text.strip(), provider_name
            except Exception as exc:
                provider_errors.append(f"{provider_name}: {exc}")

        if not provider_errors:
            provider_errors.append("No configured text-capable providers are available")
        raise AIAnalysisError(" | ".join(provider_errors))

    async def _call_provider_with_retry(
        self,
        provider_name: str,
        code_chunk: str,
        system_prompt: str,
        scan_id: Optional[int],
    ) -> Dict:
        """
        Call a provider with provider-specific retry and backoff.

        Args:
            provider_name: Name of provider (groq, cerebras, gemini, llama)
            code_chunk: Code to analyze
            system_prompt: System prompt
            scan_id: Optional scan ID for logging

        Returns:
            Analysis result as dictionary
        """
        config = AIProviderConfig.PROVIDERS[provider_name]
        retry_count = max(0, int(config["retry_count"]))
        max_attempts = retry_count + 1

        for attempt in range(1, max_attempts + 1):
            try:
                return await self._call_provider_once(
                    provider_name, code_chunk, system_prompt
                )
            except Exception as exc:
                is_last_attempt = attempt == max_attempts
                if is_last_attempt or not self._is_retryable_error(exc):
                    raise

                delay_seconds = self._get_backoff_delay(provider_name, attempt)
                logger.warning(
                    "[Scan %s] %s attempt %s/%s failed (%s). Retrying in %ss",
                    scan_id,
                    provider_name,
                    attempt,
                    max_attempts,
                    exc,
                    delay_seconds,
                )
                await asyncio.sleep(delay_seconds)

        raise AIAnalysisError(
            f"Retries exhausted for provider {provider_name}"
        )

    def _get_backoff_delay(self, provider_name: str, attempt: int) -> int:
        """Get exponential backoff delay in seconds for retry attempt."""
        base_delay = AIProviderConfig.RETRY_BACKOFF_BASE.get(provider_name, 1)
        return base_delay * (2 ** (attempt - 1))

    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine whether an error should trigger retry on the same provider."""
        if isinstance(error, asyncio.TimeoutError):
            return True

        status_code = getattr(error, "status_code", None)
        if status_code in {408, 409, 425, 429, 500, 502, 503, 504}:
            return True

        message = str(error).lower()
        non_retryable_markers = (
            "empty response",
            "failed to parse",
            "missing required fields",
            "must be",
            "not configured",
            "unknown provider",
            "unsupported provider",
        )
        if any(marker in message for marker in non_retryable_markers):
            return False

        retryable_markers = (
            "timeout",
            "timed out",
            "rate limit",
            "quota",
            "temporarily unavailable",
            "service unavailable",
            "connection reset",
            "connection aborted",
            "too many requests",
            "retry",
        )
        return any(marker in message for marker in retryable_markers)

    async def _call_provider_once(
        self, provider_name: str, code_chunk: str, system_prompt: str
    ) -> Dict:
        """Call a specific provider exactly once with timeout handling."""
        config = AIProviderConfig.PROVIDERS[provider_name]
        timeout = config["timeout"]
        provider_callers = {
            "groq": self._call_groq,
            "cerebras": self._call_cerebras,
            "gemini": self._call_gemini,
            "llama": self._call_llama,
        }
        caller = provider_callers.get(provider_name)
        if caller is None:
            raise ValueError(f"Unknown provider: {provider_name}")

        try:
            return await caller(code_chunk, system_prompt, timeout)
        except asyncio.TimeoutError as exc:
            raise asyncio.TimeoutError(
                f"{provider_name} request exceeded {timeout}s timeout"
            ) from exc

    async def _call_groq(
        self, code_chunk: str, system_prompt: str, timeout: int
    ) -> Dict:
        """Call Groq API with timeout."""
        if not self.groq_api_key:
            raise ValueError("Groq API key not configured")

        if self.groq_client:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.groq_client.chat.completions.create,
                    model=AIProviderConfig.PROVIDERS["groq"]["model"],
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": code_chunk},
                    ],
                    temperature=AIProviderConfig.TEMPERATURE,
                    max_tokens=AIProviderConfig.PROVIDERS["groq"]["max_tokens"],
                ),
                timeout=timeout,
            )

            try:
                response_text = response.choices[0].message.content
            except (AttributeError, IndexError, TypeError) as exc:
                raise AIProviderResponseError(
                    f"Groq returned unexpected response format: {exc}"
                ) from exc
        else:
            response_text = await self._call_groq_http(
                code_chunk=code_chunk,
                system_prompt=system_prompt,
                timeout=timeout,
            )

        return self._parse_response(response_text)

    async def _call_cerebras(
        self, code_chunk: str, system_prompt: str, timeout: int
    ) -> Dict:
        """Call Cerebras API with timeout."""
        if not self.cerebras_api_key:
            raise ValueError("Cerebras API key not configured")

        response_text = await self._call_cerebras_http(
            user_input=code_chunk,
            system_prompt=system_prompt,
            timeout=timeout,
        )
        return self._parse_response(response_text)

    async def _call_gemini(
        self, code_chunk: str, system_prompt: str, timeout: int
    ) -> Dict:
        """Call Google Gemini API with timeout."""
        if not self.gemini_api_key:
            raise ValueError("Gemini API key not configured")

        if self.genai_client:
            model = self.genai_client.GenerativeModel(
                AIProviderConfig.PROVIDERS["gemini"]["model"]
            )
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    model.generate_content,
                    f"{system_prompt}\n\n{code_chunk}",
                    generation_config={
                        "temperature": AIProviderConfig.TEMPERATURE,
                        "max_output_tokens": AIProviderConfig.PROVIDERS["gemini"][
                            "max_tokens"
                        ],
                    },
                ),
                timeout=timeout,
            )

            response_text = getattr(response, "text", None)
            if not response_text:
                raise AIProviderResponseError("Gemini returned empty response text")
        else:
            response_text = await self._call_gemini_http(
                user_input=code_chunk,
                system_prompt=system_prompt,
                timeout=timeout,
            )

        return self._parse_response(response_text)

    async def _call_llama(
        self, code_chunk: str, system_prompt: str, timeout: int
    ) -> Dict:
        """Call Llama via Hugging Face API with timeout."""
        if not self.hf_api_key:
            raise ValueError("Hugging Face API key not configured")

        if self.hf_client:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.hf_client.text_generation,
                    f"{system_prompt}\n\n{code_chunk}",
                    model=AIProviderConfig.PROVIDERS["llama"]["model"],
                    max_new_tokens=AIProviderConfig.PROVIDERS["llama"]["max_tokens"],
                    temperature=AIProviderConfig.TEMPERATURE,
                ),
                timeout=timeout,
            )

            response_text = response if isinstance(response, str) else str(response)
            if not response_text.strip():
                raise AIProviderResponseError("Llama returned empty response text")
        else:
            response_text = await self._call_llama_http(
                prompt=f"{system_prompt}\n\n{code_chunk}",
                timeout=timeout,
            )

        return self._parse_response(response_text)

    async def _call_groq_text(self, user_prompt: str, system_prompt: str, timeout: int) -> str:
        if not self.groq_api_key:
            raise ValueError("Groq API key not configured")
        if self.groq_client:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.groq_client.chat.completions.create,
                    model=AIProviderConfig.PROVIDERS["groq"]["model"],
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.35,
                    max_tokens=AIProviderConfig.PROVIDERS["groq"]["max_tokens"],
                ),
                timeout=timeout,
            )
            try:
                return response.choices[0].message.content or ""
            except (AttributeError, IndexError, TypeError) as exc:
                raise AIProviderResponseError(f"Groq returned unexpected text format: {exc}") from exc
        return await self._call_groq_http(
            code_chunk=user_prompt,
            system_prompt=system_prompt,
            timeout=timeout,
        )

    async def _call_gemini_text(self, user_prompt: str, system_prompt: str, timeout: int) -> str:
        if not self.gemini_api_key:
            raise ValueError("Gemini API key not configured")
        if self.genai_client:
            model = self.genai_client.GenerativeModel(AIProviderConfig.PROVIDERS["gemini"]["model"])
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    model.generate_content,
                    f"{system_prompt}\n\n{user_prompt}",
                    generation_config={
                        "temperature": 0.35,
                        "max_output_tokens": AIProviderConfig.PROVIDERS["gemini"]["max_tokens"],
                    },
                ),
                timeout=timeout,
            )
            response_text = getattr(response, "text", None)
            if not response_text:
                raise AIProviderResponseError("Gemini returned empty response text")
            return response_text
        return await self._call_gemini_http(
            user_input=user_prompt,
            system_prompt=system_prompt,
            timeout=timeout,
        )

    async def _call_cerebras_text(self, user_prompt: str, system_prompt: str, timeout: int) -> str:
        if not self.cerebras_api_key:
            raise ValueError("Cerebras API key not configured")
        return await self._call_cerebras_http(
            user_input=user_prompt,
            system_prompt=system_prompt,
            timeout=timeout,
            temperature=0.35,
        )

    async def _call_llama_text(self, user_prompt: str, system_prompt: str, timeout: int) -> str:
        if not self.hf_api_key:
            raise ValueError("Hugging Face API key not configured")
        if self.hf_client:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.hf_client.text_generation,
                    f"{system_prompt}\n\n{user_prompt}",
                    model=AIProviderConfig.PROVIDERS["llama"]["model"],
                    max_new_tokens=AIProviderConfig.PROVIDERS["llama"]["max_tokens"],
                    temperature=0.35,
                ),
                timeout=timeout,
            )
            return response if isinstance(response, str) else str(response)
        return await self._call_llama_http(
            prompt=f"{system_prompt}\n\n{user_prompt}",
            timeout=timeout,
        )

    async def _call_groq_http(self, code_chunk: str, system_prompt: str, timeout: int) -> str:
        """Call Groq chat completions over raw HTTP as SDK fallback."""
        url = "https://api.groq.com/openai/v1/chat/completions"
        payload = {
            "model": AIProviderConfig.PROVIDERS["groq"]["model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": code_chunk},
            ],
            "temperature": AIProviderConfig.TEMPERATURE,
            "max_tokens": AIProviderConfig.PROVIDERS["groq"]["max_tokens"],
        }
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json",
        }

        def _request_once() -> str:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            if response.status_code >= 400:
                raise AIProviderError(
                    f"Groq HTTP {response.status_code}: {response.text[:300]}"
                )
            data = response.json()
            choices = data.get("choices") or []
            if not choices:
                raise AIProviderResponseError("Groq HTTP response missing choices")
            message = (choices[0] or {}).get("message") or {}
            content = message.get("content")
            if not content:
                raise AIProviderResponseError("Groq HTTP response missing content")
            return str(content)

        return await asyncio.wait_for(asyncio.to_thread(_request_once), timeout=timeout)

    async def _call_gemini_http(self, user_input: str, system_prompt: str, timeout: int) -> str:
        """Call Gemini over REST API as SDK fallback."""
        model = AIProviderConfig.PROVIDERS["gemini"]["model"]
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            f"?key={self.gemini_api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_input}"}]}],
            "generationConfig": {
                "temperature": AIProviderConfig.TEMPERATURE,
                "maxOutputTokens": AIProviderConfig.PROVIDERS["gemini"]["max_tokens"],
            },
        }

        def _request_once() -> str:
            response = requests.post(url, json=payload, timeout=timeout)
            if response.status_code >= 400:
                raise AIProviderError(
                    f"Gemini HTTP {response.status_code}: {response.text[:300]}"
                )
            data = response.json()
            candidates = data.get("candidates") or []
            if not candidates:
                raise AIProviderResponseError("Gemini HTTP response missing candidates")
            first_candidate = candidates[0] or {}
            content = first_candidate.get("content") or {}
            parts = content.get("parts") or []
            text = (parts[0] or {}).get("text") if parts else None
            if not text:
                raise AIProviderResponseError("Gemini HTTP response missing text")
            return str(text)

        return await asyncio.wait_for(asyncio.to_thread(_request_once), timeout=timeout)

    async def _call_cerebras_http(
        self,
        user_input: str,
        system_prompt: str,
        timeout: int,
        temperature: Optional[float] = None,
    ) -> str:
        """Call Cerebras chat completions over HTTP."""
        url = "https://api.cerebras.ai/v1/chat/completions"
        payload = {
            "model": AIProviderConfig.PROVIDERS["cerebras"]["model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            "temperature": (
                AIProviderConfig.TEMPERATURE if temperature is None else temperature
            ),
            "max_tokens": AIProviderConfig.PROVIDERS["cerebras"]["max_tokens"],
        }
        headers = {
            "Authorization": f"Bearer {self.cerebras_api_key}",
            "Content-Type": "application/json",
        }

        def _request_once() -> str:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            if response.status_code >= 400:
                raise AIProviderError(
                    f"Cerebras HTTP {response.status_code}: {response.text[:300]}"
                )
            data = response.json()
            choices = data.get("choices") or []
            if not choices:
                raise AIProviderResponseError("Cerebras HTTP response missing choices")
            message = (choices[0] or {}).get("message") or {}
            content = message.get("content")
            if not content:
                raise AIProviderResponseError("Cerebras HTTP response missing content")
            return str(content)

        return await asyncio.wait_for(asyncio.to_thread(_request_once), timeout=timeout)

    async def _call_llama_http(self, prompt: str, timeout: int) -> str:
        """Call Hugging Face Inference API over HTTP as SDK fallback."""
        model = AIProviderConfig.PROVIDERS["llama"]["model"]
        url = f"https://router.huggingface.co/hf-inference/models/{model}"
        headers = {
            "Authorization": f"Bearer {self.hf_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": AIProviderConfig.PROVIDERS["llama"]["max_tokens"],
                "temperature": AIProviderConfig.TEMPERATURE,
            },
        }

        def _request_once() -> str:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            if response.status_code >= 400:
                raise AIProviderError(
                    f"HuggingFace HTTP {response.status_code}: {response.text[:300]}"
                )
            data = response.json()
            if isinstance(data, dict) and isinstance(data.get("choices"), list) and data["choices"]:
                message = (data["choices"][0] or {}).get("message") or {}
                content = message.get("content")
                if content:
                    return str(content)
            if isinstance(data, list) and data:
                generated = data[0].get("generated_text")
                if generated:
                    return str(generated)
            if isinstance(data, dict):
                generated = data.get("generated_text")
                if generated:
                    return str(generated)
            raise AIProviderResponseError("HuggingFace HTTP response missing generated_text")

        return await asyncio.wait_for(asyncio.to_thread(_request_once), timeout=timeout)

    @staticmethod
    def _parse_response(response_text: str) -> Dict:
        """
        Parse and validate AI response as JSON.

        Args:
            response_text: Raw response text from AI

        Returns:
            Parsed JSON response

        Raises:
            ValueError: If response is invalid JSON
        """
        if not isinstance(response_text, str) or not response_text.strip():
            raise AIProviderResponseError("Empty response from AI provider")

        payload = AIProviderService._extract_json_payload(response_text)

        try:
            result = json.loads(payload)
        except json.JSONDecodeError as e:
            payload_preview = payload[:500].replace("\n", " ")
            raise AIProviderResponseError(
                f"Failed to parse AI response as JSON: {e}. Payload preview: {payload_preview}"
            ) from e

        if not isinstance(result, dict):
            raise AIProviderResponseError(
                "AI response JSON must be an object at the top level"
            )

        missing_fields = [
            field
            for field in AIProviderConfig.REQUIRED_RESPONSE_FIELDS
            if field not in result
        ]
        if missing_fields:
            raise AIProviderResponseError(
                f"Missing required fields: {missing_fields}"
            )

        result["issues"] = AIProviderService._normalize_issues(result["issues"])
        result["health_score"] = AIProviderService._normalize_health_score(
            result["health_score"]
        )
        result["pros"] = AIProviderService._normalize_string_list(result["pros"], "pros")
        result["cons"] = AIProviderService._normalize_string_list(result["cons"], "cons")
        result["refactor_suggestions"] = AIProviderService._normalize_string_list(
            result.get("refactor_suggestions", []),
            "refactor_suggestions",
        )

        return result

    @staticmethod
    def _extract_json_payload(response_text: str) -> str:
        """Extract a JSON object from markdown/code-fenced provider responses."""
        text = response_text.strip()

        if "```" in text:
            segments = text.split("```")
            for segment in segments:
                candidate = segment.strip()
                if not candidate:
                    continue
                if candidate.lower().startswith("json"):
                    candidate = candidate[4:].strip()
                if candidate.startswith("{") and candidate.endswith("}"):
                    return candidate

        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            return text[start_idx : end_idx + 1]

        return text

    @staticmethod
    def _normalize_health_score(raw_value: Any) -> int:
        """Normalize health score to an integer within 0-100."""
        try:
            score = int(float(raw_value))
        except (TypeError, ValueError) as exc:
            raise AIProviderResponseError(
                "Field 'health_score' must be numeric"
            ) from exc

        return max(0, min(100, score))

    @staticmethod
    def _normalize_string_list(raw_value: Any, field_name: str) -> List[str]:
        """Normalize arbitrary list values into a clean list of strings."""
        if not isinstance(raw_value, list):
            raise AIProviderResponseError(f"Field '{field_name}' must be a list")

        normalized = []
        for item in raw_value:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                normalized.append(text)

        return normalized

    @staticmethod
    def _normalize_issues(raw_issues: Any) -> List[Dict[str, Any]]:
        """Normalize issue objects and enforce expected data types."""
        if not isinstance(raw_issues, list):
            raise AIProviderResponseError("Field 'issues' must be a list")

        normalized_issues = []
        for issue in raw_issues:
            if not isinstance(issue, dict):
                continue

            severity = str(issue.get("severity", "medium")).strip().lower()
            if severity not in AIProviderConfig.VALID_SEVERITIES:
                severity = "medium"

            category = str(issue.get("category", "security")).strip().lower()
            if category not in AIProviderConfig.VALID_CATEGORIES:
                category = "security"

            line_number = issue.get("line_number")
            try:
                line_number = int(line_number) if line_number is not None else None
            except (TypeError, ValueError):
                line_number = None
            if line_number is not None and line_number < 1:
                line_number = None

            exploit_risk = issue.get("exploit_risk", 0)
            try:
                exploit_risk = int(float(exploit_risk))
            except (TypeError, ValueError):
                exploit_risk = 0
            exploit_risk = max(0, min(100, exploit_risk))

            normalized_issues.append(
                {
                    "title": str(issue.get("title", "")).strip() or "Untitled issue",
                    "description": str(issue.get("description", "")).strip(),
                    "plain_english": str(issue.get("plain_english", "")).strip(),
                    "severity": severity,
                    "category": category,
                    "file_path": str(issue.get("file_path", "")).strip(),
                    "line_number": line_number,
                    "fix_suggestion": str(issue.get("fix_suggestion", "")).strip(),
                    "exploit_risk": exploit_risk,
                    "cwe_id": str(issue.get("cwe_id", "")).strip(),
                }
            )

        return normalized_issues


class AIProviderError(Exception):
    """Base exception for provider-level failures."""


class AIProviderResponseError(AIProviderError):
    """Raised when a provider returns invalid or malformed response data."""


class AIAnalysisError(Exception):
    """Custom exception for AI analysis failures."""

    pass


# Singleton instance
_ai_provider_service = None


def get_ai_provider_service() -> AIProviderService:
    """Get or create singleton instance of AI provider service."""
    global _ai_provider_service
    if _ai_provider_service is None:
        _ai_provider_service = AIProviderService()
    return _ai_provider_service
