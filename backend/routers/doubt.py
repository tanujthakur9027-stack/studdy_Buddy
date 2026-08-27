"""
Doubt solver router — RAG-powered conversational Q&A.
"""
import json
from fastapi import APIRouter, HTTPException
from models.schemas import DoubtRequest, DoubtResponse
from services.llm_service import chat_with_history
from services.document_service import retrieve_context

router = APIRouter()

SYSTEM_PROMPT = """You are StudyBuddy, a knowledgeable, patient, and encouraging AI tutor.
Your role is to help students understand concepts clearly using the provided context from their documents.

Guidelines:
- Answer clearly and accurately based on the provided context
- If the context doesn't cover the question, use your general knowledge but say so
- Use markdown formatting: **bold** for key terms, bullet points for lists, code blocks for code
- Keep answers focused and digestible (200-400 words unless more detail is needed)
- End with encouragement when appropriate"""


@router.post("/doubt/solve", response_model=DoubtResponse, tags=["Doubt Solver"])
async def solve_doubt(req: DoubtRequest):
    """Answer a student's question using RAG over their uploaded documents."""
    # Retrieve relevant context
    context_docs = retrieve_context(req.question, doc_id=req.doc_id, k=5)
    sources = list({
        doc.metadata.get("filename", "document")
        for doc in context_docs
        if doc.metadata.get("filename")
    })
    context_text = "\n\n---\n\n".join(doc.page_content for doc in context_docs)

    # Build conversation history
    history: list[dict] = []
    if req.conversation_history:
        for turn in req.conversation_history[-6:]:  # Keep last 6 turns for context window
            history.append({"role": turn.role, "content": turn.content})

    # Inject context into the user message
    context_block = f"\n\nRelevant context from the student's documents:\n{context_text}\n\n" if context_text else ""
    question_with_context = (
        f"{context_block}Student's question: {req.question}\n\n"
        "After answering, respond ONLY with valid JSON:\n"
        '{"answer": "<your markdown answer>", "follow_up_questions": ["<q1>", "<q2>", "<q3>"]}'
    )
    history.append({"role": "user", "content": question_with_context})

    try:
        raw = await chat_with_history(
            system=SYSTEM_PROMPT,
            history=history,
            temperature=0.65,
            max_tokens=1500,
        )
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        data = json.loads(raw)
        return DoubtResponse(
            answer=data.get("answer", raw),
            sources=sources,
            follow_up_questions=data.get("follow_up_questions", []),
        )
    except json.JSONDecodeError:
        # If model didn't return JSON, just return the raw text
        return DoubtResponse(answer=raw, sources=sources, follow_up_questions=[])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
