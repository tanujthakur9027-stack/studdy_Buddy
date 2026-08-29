"""
LLM service — async wrapper around OpenAI (primary) and Groq (fallback).

Provider selection:
  - If OPENAI_API_KEY is set → use OpenAI (gpt-4o-mini by default).
  - Else if GROQ_API_KEY is set → use Groq (openai/gpt-oss-20b by default).
  - Neither set → raises RuntimeError with a helpful message.
"""
from __future__ import annotations

import logging
import re
from collections.abc import AsyncIterator

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


def _clean_response(raw: str) -> str:
    """
    Clean model output before JSON parsing.
    - Strips <think>…</think> blocks (Qwen3 reasoning models)
    - Strips unclosed <think>… blocks (token-cutoff edge case)
    - Takes everything after the last </think> tag
    - Strips markdown code fences  ```json … ```
    """
    text = raw.strip()

    # Remove closed think blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # Remove unclosed think blocks (token limit hit mid-think)
    text = re.sub(r"<think>.*",          "", text, flags=re.DOTALL)
    text = text.strip()

    # If nothing left, try splitting on </think> and taking what follows
    if not text and "</think>" in raw:
        text = raw.split("</think>")[-1].strip()

    # Strip markdown code fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$",          "", text)
    text = text.strip()

    # Last resort: find first JSON object or array in the raw output
    if not text:
        m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", raw)
        if m:
            logger.warning("_clean_response: used JSON scan fallback")
            text = m.group(1).strip()

    return text


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
    raw = response.choices[0].message.content or ""
    result = _clean_response(raw)
    logger.info("chat() model=%s finish=%s raw=%d clean=%d",
                model or default_model, response.choices[0].finish_reason, len(raw), len(result))
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
    raw = response.choices[0].message.content or ""
    result = _clean_response(raw)
    logger.info("chat_with_history() model=%s finish=%s raw=%d clean=%d",
                default_model, response.choices[0].finish_reason, len(raw), len(result))
    return result


async def stream_chat_with_history(
    system: str,
    history: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> AsyncIterator[str]:
    """
    Streaming variant of chat_with_history.
    Yields raw text delta chunks as they arrive from the LLM.
    Caller is responsible for assembling the full response.
    """
    client, default_model = get_client()
    messages = [{"role": "system", "content": system}] + history
    stream = await client.chat.completions.create(
        model=default_model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=messages,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            yield delta


async def stream_chat(
    system: str,
    user: str,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> AsyncIterator[str]:
    """Streaming variant of chat() for single-turn requests."""
    client, default_model = get_client()
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": user},
    ]
    stream = await client.chat.completions.create(
        model=default_model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=messages,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            yield delta
