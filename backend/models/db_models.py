"""
models/db_models.py — SQLAlchemy ORM table definitions.

Tables:
  - documents    : uploaded file metadata per user (keyed by doc_id from vector stores)
  - quiz_sessions: quiz questions stored so submit works after server restart
  - quiz_results : completed quiz scores for history / progress tracking
  - saved_answers: bookmarked Q&A pairs from the Doubt Solver
  - chat_sessions: named conversation sessions for the Doubt Solver
  - chat_messages: individual messages inside a chat session
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
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


# ── Chat sessions (Doubt Solver conversations) ────────────────────────────────

class ChatSession(Base):
    """A named conversation session in the Doubt Solver."""
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(255), default="New Chat")
    doc_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )


class ChatMessage(Base):
    """A single user or assistant message inside a ChatSession."""
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))          # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    sources_json: Mapped[str] = mapped_column(Text, default="[]")   # JSON list[SourceChunk]
    mode: Mapped[str] = mapped_column(String(16), default="standard")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    session: Mapped["ChatSession"] = relationship(back_populates="messages")


# ── Flashcard sessions + cards ───────────────────────────────────────────────

class FlashcardSession(Base):
    """A generated flashcard deck for a document."""
    __tablename__ = "flashcard_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    doc_id: Mapped[str] = mapped_column(String(36), index=True)
    topic: Mapped[str] = mapped_column(String(255), default="General")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    cards: Mapped[list["Flashcard"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Flashcard.id",
    )


class Flashcard(Base):
    """A single flip-card in a FlashcardSession."""
    __tablename__ = "flashcards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("flashcard_sessions.id", ondelete="CASCADE"), index=True
    )
    front: Mapped[str] = mapped_column(Text)
    back: Mapped[str] = mapped_column(Text)
    topic_tag: Mapped[str] = mapped_column(String(100), default="")

    session: Mapped["FlashcardSession"] = relationship(back_populates="cards")


# ── Feynman evaluation results ───────────────────────────────────────────────

class FeynmanResult(Base):
    """Stores each Feynman Mode evaluation so progress can be tracked over time."""
    __tablename__ = "feynman_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    concept: Mapped[str] = mapped_column(String(255), default="")
    explanation_length: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[int] = mapped_column(Integer)          # 0–100
    grade: Mapped[str] = mapped_column(String(2))        # S/A/B/C/D
    gap_count: Mapped[int] = mapped_column(Integer, default=0)
    doc_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# ── Shared resources (quiz share links) ──────────────────────────────────────

class SharedResource(Base):
    """A short-lived share link containing quiz questions or document metadata."""
    __tablename__ = "shared_resources"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)   # short nanoid-like key
    resource_type: Mapped[str] = mapped_column(String(20))          # "quiz" | "document"
    payload_json: Mapped[str] = mapped_column(Text)                 # full JSON payload
    title: Mapped[str] = mapped_column(String(255), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
