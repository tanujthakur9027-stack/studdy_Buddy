"""
LLM service — async wrapper around OpenAI (primary) and Groq (fallback).

Provider selection:
  - If OPENAI_API_KEY is set → use OpenAI (gpt-4o-mini by default).
  - Else if GROQ_API_KEY is set → use Groq (qwen/qwen3.6-27b by default).
  - Neither set → raises RuntimeError with a helpful message.

Qwen3 note:
  Qwen3 models on Groq return a separate `reasoning_content` field for the
  <think>…</think> block. The actual answer is always in `message.content`.
  However, if max_tokens is hit mid-think, content may be empty.
  We handle all cases:
    1. content has JSON → use it directly (after stripping any stray tags)
    2. content is empty but reasoning_content has JSON → extract from there
    3. Both empty → raise so the caller can retry
"""
from __future__ import annotations

import logging
import re
from openai import AsyncOpenAI
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Lazily-initialised client singletons
_openai_client: AsyncOpenAI | None = None
_groq_client:   AsyncOpenAI | None = None  # Groq's SDK is OpenAI-compatible


def _get_openai() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key.strip())
    return _openai_client


def _get_groq() -> AsyncOpenAI:
    """Groq exposes an OpenAI-compatible API — reuse AsyncOpenAI with custom base_url."""
    global _groq_client
    if _groq_client is None:
        _groq_client = AsyncOpenAI(
            api_key=settings.groq_api_key.strip(),
            base_url="https://api.groq.com/openai/v1",
        )
    return _groq_client


def get_client() -> tuple[AsyncOpenAI, str]:
    """
    Returns (client, model_name) for the configured provider.
    Raises RuntimeError if neither OPENAI_API_KEY nor GROQ_API_KEY is set.
    """
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
    Robustly extract the text answer from a chat completion message.

    Qwen3 on Groq can return the answer in three ways:
      A) message.content = "<think>…</think>\\n{…json…}"  — old behaviour
      B) message.content = "{…json…}"  and reasoning in reasoning_content — new behaviour
      C) message.content = None / ""   — hit max_tokens inside the think block

    Strategy:
      1. Try message.content after stripping <think>…</think> blocks.
      2. If empty, look for a JSON object/array anywhere in the full raw text
         (content + reasoning_content concatenated).
      3. Return whatever we found; callers still validate via json.loads.
    """
    content = (message.content or "").strip()

    # Strip any <think>…</think> or unclosed <think>… blocks
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
    content = re.sub(r"<think>.*",          "", content, flags=re.DOTALL)
    content = content.strip()

    if content:
        return content

    # Fallback: scan reasoning_content for a JSON blob
    reasoning = ""
    try:
        reasoning = (message.reasoning_content or "").strip()
    except AttributeError:
        pass

    combined = (message.content or "") + reasoning
    # Find the first complete JSON object or array
    match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", combined)
    if match:
        logger.warning("LLM: content was empty — extracted JSON from reasoning_content")
        return match.group(1)

    logger.error("LLM: both content and reasoning_content are empty. Raw: %r", combined[:300])
    return ""


async def chat(
    system: str,
    user: str,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
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
    return _extract_content(response.choices[0].message)


async def chat_with_history(
    system: str,
    history: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> str:
    client, default_model = get_client()
    messages = [{"role": "system", "content": system}] + history
    response = await client.chat.completions.create(
        model=default_model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=messages,
    )
    return _extract_content(response.choices[0].message)
