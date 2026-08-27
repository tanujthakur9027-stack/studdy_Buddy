"""
LLM service — thin async wrapper around the Groq chat completions API.
Groq is OpenAI-API-compatible so the call shape is identical to the old
AsyncOpenAI client; only the import and key field change.
"""
from groq import AsyncGroq
from config import get_settings

settings = get_settings()
_client: AsyncGroq | None = None


def get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=settings.groq_api_key)
    return _client


async def chat(
    system: str,
    user: str,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> str:
    client = get_client()
    response = await client.chat.completions.create(
        model=model or settings.groq_model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    )
    return response.choices[0].message.content or ""


async def chat_with_history(
    system: str,
    history: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> str:
    client = get_client()
    messages = [{"role": "system", "content": system}] + history
    response = await client.chat.completions.create(
        model=settings.groq_model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=messages,
    )
    return response.choices[0].message.content or ""
