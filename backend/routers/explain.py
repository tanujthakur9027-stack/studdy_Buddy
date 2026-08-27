"""
Explain router — ELI5 / simplified explanation endpoint.
"""
import json
from fastapi import APIRouter, HTTPException
from models.schemas import ExplainRequest, ExplainResponse
from services.llm_service import chat
from services.document_service import retrieve_context

router = APIRouter()

LEVEL_PROMPTS = {
    "eli5": (
        "You are a brilliant teacher explaining to a curious 6-year-old child. "
        "Use very simple words, short sentences, and vivid everyday analogies. "
        "Avoid jargon entirely."
    ),
    "beginner": (
        "You are a patient tutor explaining to a high-school student with no prior knowledge. "
        "Use clear language, relatable examples, and avoid heavy technical terms."
    ),
    "intermediate": (
        "You are a university professor explaining to an undergraduate student. "
        "Use precise terminology, but still provide clear examples and comparisons."
    ),
}


@router.post("/explain", response_model=ExplainResponse, tags=["Learning"])
async def explain_topic(req: ExplainRequest):
    """Return a simplified explanation, analogy, and key points for a topic."""
    system = LEVEL_PROMPTS[req.level]

    # Optionally augment with RAG context
    context_block = ""
    if req.doc_id:
        docs = retrieve_context(req.topic, doc_id=req.doc_id, k=4)
        if docs:
            context_block = "\n\nRelevant context from the student's notes:\n" + "\n---\n".join(
                d.page_content for d in docs
            )

    user_prompt = f"""Explain the following topic: "{req.topic}"{context_block}

Respond ONLY with valid JSON matching this schema (no markdown fences):
{{
  "explanation": "<clear explanation in 150-250 words>",
  "analogy": "<one vivid everyday analogy>",
  "key_points": ["<point 1>", "<point 2>", "<point 3>", "<point 4>", "<point 5>"]
}}"""

    try:
        raw = await chat(system=system, user=user_prompt, temperature=0.65, max_tokens=1024)
        # Strip markdown fences if model wraps response anyway
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        data = json.loads(raw)
        return ExplainResponse(
            explanation=data.get("explanation", ""),
            analogy=data.get("analogy", ""),
            key_points=data.get("key_points", []),
        )
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"LLM returned invalid JSON: {e}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
