"""
LLM service — async wrapper around OpenAI (primary) and Groq (fallback).

Provider selection:
  - If OPENAI_API_KEY is set → use OpenAI (gpt-4o-mini by default).
  - Else if GROQ_API_KEY is set → use Groq (qwen/qwen3.6-27b by default).
  - Neither set → raises RuntimeError with a helpful message.
"""
from __future__ import annotations

import logging
import re
from openai import AsyncOpenAI
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_openai_client: AsyncOpenAI | None = None
_groq_client:   AsyncOpenAI | None = None


def _get_openai() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key.strip())
    return _openai_client


def _get_groq() -> AsyncOpenAI:
    global _groq_client
    if _groq_client is None:
        _groq_client = AsyncOpenAI(
            api_key=settings.groq_api_key.strip(),
            base_url="https://api.groq.com/openai/v1",
        )
    return _groq_client


def get_client() -> tuple[AsyncOpenAI, str]:
    provider = settings.llm_provider
    if provider == "openai":
        logger.debug("LLM provider: OpenAI (%s)", settings.openai_model)
        return _get_openai(), settings.openai_model
    if provider == "groq":
        logger.debug("LLM provider: Groq (%s)", settings.groq_model)
        return _get_groq(), settings.groq_model
    raise RuntimeError(
        "No LLM API key configured. Set OPENAI_API_KEY (primary) or "
        "GROQ_API_KEY (free fallback) in your .env or deployment environment."
    )


def _extract_content(message) -> str:
    """
    Extract the usable text from a Groq/OpenAI chat message.

    Qwen3 on Groq always puts <think>…</think> INSIDE message.content.
    The actual answer (JSON) appears AFTER the closing </think> tag.

    Strategy — try each in order, return first non-empty result:
      1. Strip <think>…</think> block → take what's left
      2. Take everything after the last </think>
      3. Scan the raw text for the first JSON object / array
      4. Return raw as-is (let caller handle it)
    """
    raw = (message.content or "").strip()

    # Also grab reasoning_content if it exists (some API versions)
    try:
        reasoning = (message.reasoning_content or "").strip()
    except AttributeError:
        reasoning = ""

    full = raw  # primary source

    # ── Strategy 1: strip closed <think>…</think> blocks ─────────────────────
    s1 = re.sub(r"<think>.*?</think>", "", full, flags=re.DOTALL).strip()
    if s1:
        logger.debug("_extract_content: strategy 1 succeeded (%d chars)", len(s1))
        return s1

    # ── Strategy 2: take everything after the LAST </think> ──────────────────
    parts = re.split(r"</think>", full, flags=re.DOTALL)
    if len(parts) > 1:
        s2 = parts[-1].strip()
        if s2:
            logger.debug("_extract_content: strategy 2 succeeded (%d chars)", len(s2))
            return s2

    # ── Strategy 3: find first JSON object or array anywhere in full+reasoning ─
    combined = full + "\n" + reasoning
    m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", combined)
    if m:
        s3 = m.group(1).strip()
        logger.warning("_extract_content: strategy 3 (regex JSON scan) (%d chars)", len(s3))
        return s3

    # ── Strategy 4: fallback — return raw and let caller deal with it ─────────
    logger.error("_extract_content: all strategies failed. raw=%r", full[:200])
    return full


async def chat(
    system: str,
    user: str,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    client, default_model = get_client()
    response = await client.chat.completions.create(
        model=model or default_model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    )
    result = _extract_content(response.choices[0].message)
    logger.debug("chat() -> %d chars, finish=%s", len(result), response.choices[0].finish_reason)
    return result


async def chat_with_history(
    system: str,
    history: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    client, default_model = get_client()
    messages = [{"role": "system", "content": system}] + history
    response = await client.chat.completions.create(
        model=default_model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=messages,
    )
    result = _extract_content(response.choices[0].message)
    logger.debug("chat_with_history() -> %d chars, finish=%s", len(result), response.choices[0].finish_reason)
    return result
