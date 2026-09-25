"""
LLM service — Groq (primary) with Gemini 2.5 Flash (fallback).

Provider selection:
  1. Groq  — if GROQ_API_KEY is set (tried with model rotation on rate-limit)
  2. Gemini — if GEMINI_API_KEY is set and Groq is absent or exhausted
  Neither set → raises RuntimeError with a helpful message.
"""
from __future__ import annotations

import logging
import re
import time
from collections.abc import AsyncIterator

import google.genai as genai
from openai import AsyncOpenAI, NotFoundError, RateLimitError
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_groq_client: AsyncOpenAI | None = None


# ── Groq client (OpenAI-compatible shim) ─────────────────────────────────────

def _get_groq() -> AsyncOpenAI:
    global _groq_client
    if _groq_client is None:
        _groq_client = AsyncOpenAI(
            api_key=settings.groq_api_key.strip(),
            base_url="https://api.groq.com/openai/v1",
        )
    return _groq_client


# ── Gemini client ─────────────────────────────────────────────────────────────

def _get_gemini() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key.strip())


# ── Provider guard ────────────────────────────────────────────────────────────

def _require_configured() -> None:
    if not settings.llm_configured:
        raise RuntimeError(
            "No LLM API key configured. Set GROQ_API_KEY (primary) or "
            "GEMINI_API_KEY (fallback) in your .env or deployment environment."
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _groq_model_rotation() -> list[str]:
    """Return [primary] + fallbacks — all Groq models to try in order."""
    primary = settings.groq_model
    fallbacks = [m for m in settings.groq_fallback_models_list if m != primary]
    return [primary] + fallbacks


def _clean_response(raw: str) -> str:
    """
    Clean model output before JSON parsing.
    - Strips <think>…</think> blocks (Qwen3 reasoning models)
    - Strips unclosed <think>… blocks (token-cutoff edge case)
    - Strips markdown code fences  ```json … ```
    """
    text = raw.strip()

    # Remove closed think blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # Remove unclosed think blocks (token limit hit mid-think)
    text = re.sub(r"<think>.*", "", text, flags=re.DOTALL)
    text = text.strip()

    # If nothing left, try splitting on </think> and taking what follows
    if not text and "</think>" in raw:
        text = raw.split("</think>")[-1].strip()

    # Strip markdown code fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    # Last resort: find first JSON object or array in the raw output
    if not text:
        m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", raw)
        if m:
            logger.warning("_clean_response: used JSON scan fallback")
            text = m.group(1).strip()

    return text


# ── Gemini helpers ────────────────────────────────────────────────────────────

def _build_gemini_prompt(system: str, user: str) -> str:
    return f"{system}\n\n{user}"


def _build_gemini_prompt_from_history(system: str, history: list[dict]) -> str:
    parts = [system]
    for msg in history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        parts.append(f"[{role}]: {content}")
    return "\n\n".join(parts)


async def _gemini_chat(prompt: str) -> str:
    client = _get_gemini()
    t0 = time.monotonic()
    response = await client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
    )
    latency_ms = int((time.monotonic() - t0) * 1000)
    raw = response.text or ""
    result = _clean_response(raw)
    logger.info(
        "llm_call",
        extra={
            "fn": "gemini_chat",
            "model": settings.gemini_model,
            "latency_ms": latency_ms,
        },
    )
    if latency_ms > 10_000:
        logger.warning("llm_slow_call latency_ms=%d model=%s", latency_ms, settings.gemini_model)
    return result


async def _gemini_stream(prompt: str) -> AsyncIterator[str]:
    client = _get_gemini()
    async for chunk in await client.aio.models.generate_content_stream(
        model=settings.gemini_model,
        contents=prompt,
    ):
        if chunk.text:
            yield chunk.text


# ── Public API ────────────────────────────────────────────────────────────────

async def chat(
    system: str,
    user: str,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    _require_configured()

    # ── Try Groq first ────────────────────────────────────────────────────────
    if settings.groq_api_key.strip():
        client = _get_groq()
        models_to_try = [model] if model else _groq_model_rotation()
        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ]
        last_exc: Exception | None = None
        for used_model in models_to_try:
            t0 = time.monotonic()
            try:
                response = await client.chat.completions.create(
                    model=used_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    messages=messages,
                )
            except (RateLimitError, NotFoundError) as exc:
                logger.warning("groq_model_unavailable model=%s: %s", used_model, exc)
                last_exc = exc
                continue
            latency_ms = int((time.monotonic() - t0) * 1000)
            raw = response.choices[0].message.content or ""
            result = _clean_response(raw)
            usage = response.usage
            logger.info(
                "llm_call",
                extra={
                    "fn": "chat",
                    "model": used_model,
                    "finish": response.choices[0].finish_reason,
                    "prompt_tokens": usage.prompt_tokens if usage else 0,
                    "completion_tokens": usage.completion_tokens if usage else 0,
                    "latency_ms": latency_ms,
                },
            )
            if latency_ms > 10_000:
                logger.warning("llm_slow_call latency_ms=%d model=%s", latency_ms, used_model)
            return result

        logger.warning("groq_all_models_exhausted, falling back to Gemini: %s", last_exc)

    # ── Gemini fallback ───────────────────────────────────────────────────────
    if settings.gemini_api_key.strip():
        logger.info("llm_fallback provider=gemini model=%s", settings.gemini_model)
        return await _gemini_chat(_build_gemini_prompt(system, user))

    raise RuntimeError(
        "All Groq models rate-limited and no Gemini fallback key is configured. "
        "Set GEMINI_API_KEY in your .env or deployment environment."
    )


async def chat_with_history(
    system: str,
    history: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    _require_configured()

    # ── Try Groq first ────────────────────────────────────────────────────────
    if settings.groq_api_key.strip():
        client = _get_groq()
        models_to_try = _groq_model_rotation()
        messages = [{"role": "system", "content": system}] + history
        last_exc: Exception | None = None
        for used_model in models_to_try:
            t0 = time.monotonic()
            try:
                response = await client.chat.completions.create(
                    model=used_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    messages=messages,
                )
            except (RateLimitError, NotFoundError) as exc:
                logger.warning("groq_model_unavailable model=%s: %s", used_model, exc)
                last_exc = exc
                continue
            latency_ms = int((time.monotonic() - t0) * 1000)
            raw = response.choices[0].message.content or ""
            result = _clean_response(raw)
            usage = response.usage
            logger.info(
                "llm_call",
                extra={
                    "fn": "chat_with_history",
                    "model": used_model,
                    "finish": response.choices[0].finish_reason,
                    "prompt_tokens": usage.prompt_tokens if usage else 0,
                    "completion_tokens": usage.completion_tokens if usage else 0,
                    "latency_ms": latency_ms,
                },
            )
            if latency_ms > 10_000:
                logger.warning("llm_slow_call latency_ms=%d model=%s", latency_ms, used_model)
            return result

        logger.warning("groq_all_models_exhausted, falling back to Gemini: %s", last_exc)

    # ── Gemini fallback ───────────────────────────────────────────────────────
    if settings.gemini_api_key.strip():
        logger.info("llm_fallback provider=gemini model=%s", settings.gemini_model)
        prompt = _build_gemini_prompt_from_history(system, history)
        return await _gemini_chat(prompt)

    raise RuntimeError(
        "All Groq models rate-limited and no Gemini fallback key is configured. "
        "Set GEMINI_API_KEY in your .env or deployment environment."
    )


async def stream_chat_with_history(
    system: str,
    history: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> AsyncIterator[str]:
    """Streaming variant of chat_with_history. Falls back to Gemini if Groq is exhausted."""
    _require_configured()

    # ── Try Groq first ────────────────────────────────────────────────────────
    if settings.groq_api_key.strip():
        client = _get_groq()
        models_to_try = _groq_model_rotation()
        messages = [{"role": "system", "content": system}] + history
        groq_exhausted = False

        for used_model in models_to_try:
            try:
                stream = await client.chat.completions.create(
                    model=used_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    messages=messages,
                    stream=True,
                )
                async for chunk in stream:
                    delta = chunk.choices[0].delta.content if chunk.choices else None
                    if delta:
                        yield delta
                return  # success
            except (RateLimitError, NotFoundError) as exc:
                logger.warning("groq_model_unavailable stream model=%s: %s", used_model, exc)
                continue

        groq_exhausted = True
        logger.warning("groq_all_models_exhausted in stream, falling back to Gemini")

    # ── Gemini fallback ───────────────────────────────────────────────────────
    if settings.gemini_api_key.strip():
        logger.info("llm_fallback stream provider=gemini model=%s", settings.gemini_model)
        prompt = _build_gemini_prompt_from_history(system, history)
        async for chunk in _gemini_stream(prompt):
            yield chunk
        return

    raise RuntimeError(
        "All Groq models rate-limited and no Gemini fallback key is configured. "
        "Set GEMINI_API_KEY in your .env or deployment environment."
    )


async def stream_chat(
    system: str,
    user: str,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> AsyncIterator[str]:
    """Streaming single-turn chat. Falls back to Gemini if Groq is exhausted."""
    _require_configured()

    # ── Try Groq first ────────────────────────────────────────────────────────
    if settings.groq_api_key.strip():
        client = _get_groq()
        models_to_try = _groq_model_rotation()
        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ]

        for used_model in models_to_try:
            try:
                stream = await client.chat.completions.create(
                    model=used_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    messages=messages,
                    stream=True,
                )
                async for chunk in stream:
                    delta = chunk.choices[0].delta.content if chunk.choices else None
                    if delta:
                        yield delta
                return  # success
            except (RateLimitError, NotFoundError) as exc:
                logger.warning("groq_model_unavailable stream model=%s: %s", used_model, exc)
                continue

        logger.warning("groq_all_models_exhausted in stream_chat, falling back to Gemini")

    # ── Gemini fallback ───────────────────────────────────────────────────────
    if settings.gemini_api_key.strip():
        logger.info("llm_fallback stream provider=gemini model=%s", settings.gemini_model)
        async for chunk in _gemini_stream(_build_gemini_prompt(system, user)):
            yield chunk
        return

    raise RuntimeError(
        "All Groq models rate-limited and no Gemini fallback key is configured. "
        "Set GEMINI_API_KEY in your .env or deployment environment."
    )
