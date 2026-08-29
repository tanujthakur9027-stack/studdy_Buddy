"""
models/db_models.py — SQLAlchemy ORM table definitions.

Tables:
  - documents    : uploaded file metadata per user (keyed by doc_id from vector stores)
  - quiz_sessions: quiz questions stored so submit works after server restart
  - quiz_results : completed quiz scores for history / progress tracking
  - saved_answers: bookmarked Q&A pairs from the Doubt Solver
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


# ── Documents ─────────────────────────────────────────────────────────────────

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    doc_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    filename: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    pages: Mapped[int] = mapped_column(Integer, default=0)
    chunks: Mapped[int] = mapped_column(Integer, default=0)
    total_chars: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    parser_used: Mapped[str] = mapped_column(String(50), default="")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    quiz_results: Mapped[list["QuizResult"]] = relationship(back_populates="document", cascade="all, delete-orphan")


# ── Quiz sessions (replaces in-process _quiz_store dict) ─────────────────────

class QuizSession(Base):
    """Stores the questions for a quiz so /quiz/submit works after restart."""
    __tablename__ = "quiz_sessions"

    quiz_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    questions_json: Mapped[str] = mapped_column(Text)   # JSON-serialised list[QuizQuestion]
    topic: Mapped[str] = mapped_column(String(255), default="")
    difficulty: Mapped[str] = mapped_column(String(20), default="mixed")
    timer_seconds: Mapped[int] = mapped_column(Integer, default=30)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# ── Quiz results (score history) ──────────────────────────────────────────────

class QuizResult(Base):
    __tablename__ = "quiz_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    quiz_id: Mapped[str] = mapped_column(String(36), index=True)
    doc_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.doc_id", ondelete="SET NULL"), nullable=True)
    topic: Mapped[str] = mapped_column(String(255), default="")
    difficulty: Mapped[str] = mapped_column(String(20), default="mixed")
    score: Mapped[int] = mapped_column(Integer)
    total: Mapped[int] = mapped_column(Integer)
    percentage: Mapped[float] = mapped_column(Float)
    grade: Mapped[str] = mapped_column(String(2))
    time_taken: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    document: Mapped["Document | None"] = relationship(back_populates="quiz_results")


# ── Saved answers (bookmarks) ─────────────────────────────────────────────────

class SavedAnswer(Base):
    __tablename__ = "saved_answers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
