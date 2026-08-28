from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, Literal


# ── Upload ────────────────────────────────────────────────────────────────────
class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    chunks: int
    # Extended ingestion stats returned by /api/upload
    pages: int = 0
    total_chars: int = 0
    total_tokens: int = 0
    parser_used: str = ""


# ── /api/ask ──────────────────────────────────────────────────────────────────
class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, description="The student's question")
    doc_id: Optional[str] = Field(
        default=None,
        description="Restrict context retrieval to this specific document. "
                    "Omit to search across all indexed documents.",
    )
    mode: Literal["standard", "eli5"] = Field(
        default="standard",
        description=(
            "'standard' → accurate, detailed answer pitched at a knowledgeable student. "
            "'eli5' → Explain Like I'm 10: simple words, vivid analogies, short sentences."
        ),
    )
    conversation_history: Optional[list["ChatTurn"]] = Field(
        default=None,
        description="Previous turns for multi-turn conversations (last 6 used).",
    )
    k: int = Field(default=5, ge=1, le=20, description="Number of context chunks to retrieve.")


class SourceChunk(BaseModel):
    filename: str
    page: int
    chunk_index: int
    snippet: str  # first 200 chars of the chunk


class AskResponse(BaseModel):
    answer: str
    mode_used: Literal["standard", "eli5"]
    sources: list[SourceChunk]
    follow_up_questions: list[str]
    context_chunks_used: int


# ── Explain ──────────────────────────────────────────────────────────────────
class ExplainRequest(BaseModel):
    topic: str
    doc_id: Optional[str] = None
    level: Literal["eli5", "beginner", "intermediate"] = "eli5"


class ExplainResponse(BaseModel):
    explanation: str
    analogy: str
    key_points: list[str]


# ── Quiz ─────────────────────────────────────────────────────────────────────
class QuizGenerateRequest(BaseModel):
    doc_id: Optional[str] = None
    topic: Optional[str] = Field(
        default=None,
        description="Free-text topic or syllabus heading. If omitted and doc_id is given, "
                    "questions are generated from the indexed document context.",
    )
    num_questions: int = Field(default=5, ge=3, le=10)
    difficulty: Literal["easy", "medium", "hard", "mixed"] = "mixed"
    timer_seconds: int = Field(
        default=30,
        description="Hint stored in the response so the frontend knows the configured timer.",
    )


class QuizQuestion(BaseModel):
    id: str
    question: str
    options: list[str]          # exactly 4 options
    correct_index: int          # 0-based index into options
    explanation: str            # concise 1-2 sentence rationale
    difficulty: Literal["easy", "medium", "hard"]
    topic_tag: str = ""         # e.g. "Photosynthesis", "Newton's Laws"
    hint: str = ""              # optional nudge shown after timeout


class QuizGenerateResponse(BaseModel):
    quiz_id: str
    questions: list[QuizQuestion]
    topic: str                  # resolved topic label shown in the UI
    timer_seconds: int          # per-question timer (15 or 30)
    difficulty: str


class QuizAnswerDetail(BaseModel):
    """Per-question breakdown returned in submit response."""
    question_id: str
    question: str
    user_index: int             # -1 if timed-out / not answered
    correct_index: int
    is_correct: bool
    topic_tag: str
    difficulty: Literal["easy", "medium", "hard"]
    explanation: str


class QuizSubmitRequest(BaseModel):
    quiz_id: str
    answers: dict[str, int]     # question_id → chosen_index (-1 = no answer)
    time_taken: int             # total seconds spent


class QuizSubmitResponse(BaseModel):
    score: int
    total: int
    percentage: float
    time_taken: int
    details: list[QuizAnswerDetail]
    weak_topics: list[str]
    strong_topics: list[str]
    recommendations: list[str]
    grade: str                  # "S", "A", "B", "C", "D"


# ── Revision Planner ─────────────────────────────────────────────────────────
class RevisionPlanRequest(BaseModel):
    # Core inputs
    exam_date: str = Field(..., description="Target exam date (YYYY-MM-DD).")
    daily_hours: float = Field(default=2.0, ge=0.5, le=8.0, description="Available study hours per day.")

    # Content sources — at least one must be provided
    syllabus_text: Optional[str] = Field(
        default=None,
        description="Raw syllabus / notes pasted directly into the form. "
                    "Parsed to extract topics automatically when topics list is empty.",
    )
    topics: list[str] = Field(
        default_factory=list,
        description="Explicit topic list. Auto-extracted from syllabus_text when empty.",
    )
    weak_topics: Optional[list[str]] = Field(
        default=None,
        description="Topics the student struggles with — given higher weighting and earlier scheduling.",
    )
    doc_id: Optional[str] = Field(
        default=None,
        description="doc_id of an already-indexed document to pull extra context from.",
    )


class RevisionTask(BaseModel):
    """One study session within the revision plan."""
    date: str                                              # YYYY-MM-DD
    day_label: str = ""                                    # e.g. "Day 1 · Mon 14 Jul"
    session_type: Literal["concept", "quiz", "buffer", "rest"] = "concept"
    topic: str                                             # main topic / activity label
    subtopics: list[str] = Field(default_factory=list)    # bullet-point breakdown
    duration_mins: int
    priority: Literal["high", "medium", "low"]
    technique: str
    resources: list[str] = Field(default_factory=list)
    notes: str = ""                                        # short coaching note for the session


class PlanStats(BaseModel):
    total_days: int
    study_days: int
    quiz_days: int
    buffer_days: int
    rest_days: int
    total_study_mins: int
    topics_covered: int
    days_to_exam: int


class RevisionPlanResponse(BaseModel):
    plan: list[RevisionTask]
    summary: str
    tips: list[str]
    stats: PlanStats
    topic_list: list[str]          # resolved final topic list shown in the UI


# ── Doubt Solver ─────────────────────────────────────────────────────────────
class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class DoubtRequest(BaseModel):
    question: str
    doc_id: Optional[str] = None
    conversation_history: Optional[list[ChatTurn]] = None


class DoubtResponse(BaseModel):
    answer: str
    sources: list[str]
    follow_up_questions: list[str]
