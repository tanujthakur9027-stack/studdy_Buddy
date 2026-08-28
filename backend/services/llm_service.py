"""
LLM service — async wrapper around OpenAI (primary) and Groq (fallback).

Provider selection:
  - If OPENAI_API_KEY is set → use OpenAI (gpt-4o-mini by default).
  - Else if GROQ_API_KEY is set → use Groq (llama-3.3-70b-versatile by default).
  - Neither set → raises RuntimeError with a helpful message.
"""
from __future__ import annotations

import logging
from openai import AsyncOpenAI
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Lazily-initialised client singletons
_openai_client: AsyncOpenAI | None = None
_groq_client: AsyncOpenAI | None = None  # Groq's SDK is OpenAI-compatible


def _get_openai() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key.strip())
    return _openai_client


def _get_groq() -> AsyncOpenAI:
    """Groq exposes an OpenAI-compatible API, so we reuse AsyncOpenAI with a custom base_url."""
    global _groq_client
    if _groq_client is None:
        try:
            from groq import AsyncGroq  # type: ignore[import]
            # Store as an attribute-compatible object; wrap in a shim below
        except ImportError:
            pass
        # Use OpenAI SDK pointing at Groq's base URL (fully compatible)
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


def _extra_body() -> dict:
    """
    Qwen3 models on Groq default to 'thinking' mode which wraps output in
    <think>...</think> tags — this breaks JSON parsing.
    Passing thinking={"type": "disabled"} suppresses it.
    Only sent when provider is Groq; ignored silently by OpenAI.
    """
    if settings.llm_provider == "groq" and "qwen" in settings.groq_model.lower():
        return {"thinking": {"type": "disabled"}}
    return {}


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
        extra_body=_extra_body(),
    )
    return response.choices[0].message.content or ""


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
        extra_body=_extra_body(),
    )
    return response.choices[0].message.content or ""
