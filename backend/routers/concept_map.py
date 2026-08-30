"""
/api/concept-map — Generate a concept map from an indexed document.

Returns a JSON graph (nodes + edges) that the frontend renders as SVG.

Endpoint:
  POST /api/concept-map
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from services.document_service import retrieve_context
from services.llm_service import chat
from utils.text_utils import truncate_to_tokens, strip_json_fences

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
log = logging.getLogger(__name__)

_SYSTEM = """\
You are an expert knowledge organiser. Your task is to extract a concept map from study material.

Return ONLY valid JSON (no markdown fences) matching this exact schema:
{
  "nodes": [
    {"id": "<short_snake_case>", "label": "<display name>", "type": "main|sub|detail"}
  ],
  "edges": [
    {"from": "<node_id>", "to": "<node_id>", "label": "<relationship verb>"}
  ]
}

Rules:
- 6–14 nodes total. 1–2 "main" nodes, 3–6 "sub" nodes, rest "detail".
- Each edge label must be a short verb phrase (e.g. "requires", "produces", "is part of", "leads to").
- Every node must appear in at least one edge.
- No duplicate node ids.
- Keep labels short (2–5 words max)."""


class ConceptMapRequest(BaseModel):
    doc_id: str
    topic: str = ""


class ConceptNode(BaseModel):
    id: str
    label: str
    type: str   # "main" | "sub" | "detail"


class ConceptEdge(BaseModel):
    from_node: str
    to_node: str
    label: str


class ConceptMapResponse(BaseModel):
    nodes: list[ConceptNode]
    edges: list[ConceptEdge]


@router.post("/concept-map", response_model=ConceptMapResponse, tags=["Learning"])
@limiter.limit("10/minute")
async def generate_concept_map(request: Request, req: ConceptMapRequest) -> ConceptMapResponse:
    """Generate a concept map graph from the indexed document."""
    query = req.topic.strip() if req.topic.strip() else "key concepts definitions relationships overview"
    docs = retrieve_context(query, doc_id=req.doc_id, k=10)

    if not docs:
        raise HTTPException(status_code=404, detail="No content found for this document. Please re-upload it.")

    raw_context = "\n\n---\n\n".join(d.page_content for d in docs)
    context = truncate_to_tokens(raw_context, max_tokens=3500)

    focus = f' Focus on the topic: "{req.topic}".' if req.topic.strip() else ""
    user_prompt = (
        f"Create a concept map from the following study material.{focus}\n\n"
        f"=== MATERIAL ===\n{context}\n=== END ==="
    )

    try:
        raw = await chat(system=_SYSTEM, user=user_prompt, temperature=0.3, max_tokens=900)
        cleaned = strip_json_fences(raw)
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        log.error("concept-map JSON parse failed: %r", raw[:300] if "raw" in dir() else "")
        raise HTTPException(status_code=500, detail=f"LLM returned invalid JSON: {e}") from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    nodes = [
        ConceptNode(id=n["id"], label=n["label"], type=n.get("type", "sub"))
        for n in data.get("nodes", [])
    ]
    edges = [
        ConceptEdge(from_node=e["from"], to_node=e["to"], label=e.get("label", "→"))
        for e in data.get("edges", [])
    ]

    return ConceptMapResponse(nodes=nodes, edges=edges)
