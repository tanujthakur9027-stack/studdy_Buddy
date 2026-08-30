"""
Text utilities used across the backend.
"""
from __future__ import annotations

import re
import unicodedata


def strip_json_fences(raw: str) -> str:
    """
    Strip markdown code-fences from LLM output so json.loads() always gets
    clean JSON regardless of whether the model wrapped its response in:
      ```json ... ``` or ``` ... ```

    NOTE: Do NOT use str.lstrip("```json") — that strips individual *characters*
    from the set {`backtick`, j, s, o, n}, which corrupts valid JSON strings.
    """
    raw = raw.strip()
    # Remove opening fence:  ```json  or  ```
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    # Remove closing fence:  ```
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def clean_text(text: str) -> str:
    """
    Normalise extracted text:
    - NFKC unicode normalisation (ligatures, full-width chars, etc.)
    - Collapse runs of 3+ newlines → double newline.
    - Collapse runs of spaces/tabs → single space (within a line).
    - Strip leading/trailing whitespace per line.
    - Remove lines that are pure noise (just dots, dashes, underscores, digits).
    """
    if not text:
        return ""
    # Unicode normalisation
    text = unicodedata.normalize("NFKC", text)
    # Remove null bytes and control characters (except newline/tab)
    text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", text)
    # Normalise line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Strip each line of leading/trailing spaces; remove pure-noise lines
    cleaned_lines: list[str] = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()
        # Drop lines that are only punctuation/dashes/dots (common in PDFs)
        if re.fullmatch(r"[.\-_=*~\s]{3,}", line):
            continue
        cleaned_lines.append(line)
    # Collapse 3+ consecutive blank lines → 2
    result = "\n".join(cleaned_lines)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def count_tokens(text: str) -> int:
    """
    Approximate token count using tiktoken (cl100k_base, used by GPT-4 / gpt-4o-mini).
    Falls back to a word-based heuristic if tiktoken is unavailable.
    """
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        # Rough heuristic: ~0.75 tokens per word
        return max(1, int(len(text.split()) * 0.75))


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate *text* so it fits within *max_tokens*, preserving whole words."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        tokens = enc.encode(text)
        if len(tokens) <= max_tokens:
            return text
        return enc.decode(tokens[:max_tokens])
    except Exception:
        # Fallback: split by words
        words = text.split()
        limit = int(max_tokens / 0.75)
        return " ".join(words[:limit])
