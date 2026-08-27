"""
LLM service — async wrapper around the OpenAI chat completions API.
"""
from openai import AsyncOpenAI
from config import get_settings

settings = get_settings()
_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        if not settings.openai_api_key or settings.openai_api_key.strip() == "":
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it in the Render dashboard → Environment."
            )
        _client = AsyncOpenAI(api_key=settings.openai_api_key.strip())
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
        model=model or settings.openai_model,
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
        model=settings.openai_model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=messages,
    )
    return response.choices[0].message.content or ""
