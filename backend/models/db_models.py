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
from typing import Optional

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


# ── Users (authentication) ────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255), default="")
    role: Mapped[str] = mapped_column(String(20), default="student")  # "admin" | "student"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    # Relationships
    student_profile: Mapped[Optional["StudentProfile"]] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user", cascade="all, delete-orphan")


# ── Student profile ───────────────────────────────────────────────────────────

class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    student_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), default="")
    course: Mapped[str] = mapped_column(String(100), default="")
    branch: Mapped[str] = mapped_column(String(100), default="")
    semester: Mapped[str] = mapped_column(String(20), default="")
    section: Mapped[str] = mapped_column(String(20), default="")
    academic_year: Mapped[str] = mapped_column(String(20), default="")
    dob: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    profile_photo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    class_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("classes.id", ondelete="SET NULL"), nullable=True)

    user: Mapped["User"] = relationship(back_populates="student_profile")
    klass: Mapped[Optional["Class"]] = relationship(foreign_keys=[class_id])


# ── Academic structure ────────────────────────────────────────────────────────

class Class(Base):
    __tablename__ = "classes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(100))
    course: Mapped[str] = mapped_column(String(100), default="")
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    sections: Mapped[list["Section"]] = relationship(back_populates="klass", cascade="all, delete-orphan")
    subjects: Mapped[list["Subject"]] = relationship(back_populates="klass", cascade="all, delete-orphan")


class Section(Base):
    __tablename__ = "sections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(50))
    class_id: Mapped[str] = mapped_column(String(36), ForeignKey("classes.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    klass: Mapped["Class"] = relationship(back_populates="sections")


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(100))
    code: Mapped[str] = mapped_column(String(50), default="")
    class_id: Mapped[str] = mapped_column(String(36), ForeignKey("classes.id", ondelete="CASCADE"))
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    klass: Mapped["Class"] = relationship(back_populates="subjects")


# ── Assignments ───────────────────────────────────────────────────────────────

class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(255))
    subject_id: Mapped[str] = mapped_column(String(36), ForeignKey("subjects.id", ondelete="CASCADE"))
    class_id: Mapped[str] = mapped_column(String(36), ForeignKey("classes.id", ondelete="CASCADE"))
    section_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("sections.id", ondelete="SET NULL"), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    instructions: Mapped[str] = mapped_column(Text, default="")
    file_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    due_date: Mapped[str] = mapped_column(String(20))
    due_time: Mapped[str] = mapped_column(String(10), default="23:59")
    max_marks: Mapped[int] = mapped_column(Integer, default=100)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    subject: Mapped["Subject"] = relationship()
    klass: Mapped["Class"] = relationship()
    submissions: Mapped[list["AssignmentSubmission"]] = relationship(back_populates="assignment", cascade="all, delete-orphan")


class AssignmentSubmission(Base):
    __tablename__ = "assignment_submissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    assignment_id: Mapped[str] = mapped_column(String(36), ForeignKey("assignments.id", ondelete="CASCADE"))
    student_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    file_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    marks_obtained: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    feedback: Mapped[str] = mapped_column(Text, default="")
    is_evaluated: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="submitted")  # submitted | late | evaluated

    assignment: Mapped["Assignment"] = relationship(back_populates="submissions")
    student: Mapped["User"] = relationship()


# ── Marks system ──────────────────────────────────────────────────────────────

class AssessmentCategory(Base):
    __tablename__ = "assessment_categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(100))
    subject_id: Mapped[str] = mapped_column(String(36), ForeignKey("subjects.id", ondelete="CASCADE"))
    max_marks: Mapped[float] = mapped_column(Float, default=100.0)
    weightage: Mapped[float] = mapped_column(Float, default=100.0)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    marks: Mapped[list["Mark"]] = relationship(back_populates="category", cascade="all, delete-orphan")


class Mark(Base):
    __tablename__ = "marks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    student_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    category_id: Mapped[str] = mapped_column(String(36), ForeignKey("assessment_categories.id", ondelete="CASCADE"))
    obtained_marks: Mapped[float] = mapped_column(Float, default=0.0)
    remarks: Mapped[str] = mapped_column(Text, default="")
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    category: Mapped["AssessmentCategory"] = relationship(back_populates="marks")
    student: Mapped["User"] = relationship()


# ── Timetable ─────────────────────────────────────────────────────────────────

class Timetable(Base):
    __tablename__ = "timetables"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    class_id: Mapped[str] = mapped_column(String(36), ForeignKey("classes.id", ondelete="CASCADE"))
    section_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("sections.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(100), default="Timetable")
    start_time: Mapped[str] = mapped_column(String(10), default="09:00")  # HH:MM
    periods_per_day: Mapped[int] = mapped_column(Integer, default=8)
    lunch_after_period: Mapped[int] = mapped_column(Integer, default=4)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    klass: Mapped["Class"] = relationship()
    slots: Mapped[list["TimetableSlot"]] = relationship(back_populates="timetable", cascade="all, delete-orphan")


class TimetableSlot(Base):
    __tablename__ = "timetable_slots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    timetable_id: Mapped[str] = mapped_column(String(36), ForeignKey("timetables.id", ondelete="CASCADE"))
    day_of_week: Mapped[int] = mapped_column(Integer)  # 0=Mon, 5=Sat
    period_number: Mapped[int] = mapped_column(Integer)  # 1-based
    subject_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    teacher_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    room: Mapped[str] = mapped_column(String(50), default="")

    timetable: Mapped["Timetable"] = relationship(back_populates="slots")
    subject: Mapped[Optional["Subject"]] = relationship()
    teacher: Mapped[Optional["User"]] = relationship(foreign_keys=[teacher_id])


# ── Notifications ─────────────────────────────────────────────────────────────

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    notif_type: Mapped[str] = mapped_column(String(50), default="general")  # assignment|submission|marks|timetable|announcement|note|registration
    reference_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="notifications")


# ── Announcements ─────────────────────────────────────────────────────────────

class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    class_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("classes.id", ondelete="SET NULL"), nullable=True)
    section_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("sections.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    author: Mapped["User"] = relationship(foreign_keys=[created_by])


# ── Student connections ───────────────────────────────────────────────────────

class ConnectionRequest(Base):
    __tablename__ = "connection_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    from_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    to_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|accepted|rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    from_user: Mapped["User"] = relationship(foreign_keys=[from_user_id])
    to_user: Mapped["User"] = relationship(foreign_keys=[to_user_id])


class StudentConnection(Base):
    __tablename__ = "student_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_a_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    user_b_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user_a: Mapped["User"] = relationship(foreign_keys=[user_a_id])
    user_b: Mapped["User"] = relationship(foreign_keys=[user_b_id])


# ── Notes / Resources ─────────────────────────────────────────────────────────

class Note(Base):
    __tablename__ = "notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    subject: Mapped[str] = mapped_column(String(100), default="")
    course: Mapped[str] = mapped_column(String(100), default="")
    semester: Mapped[str] = mapped_column(String(20), default="")
    tags: Mapped[str] = mapped_column(String(500), default="")
    file_url: Mapped[str] = mapped_column(String(500))
    original_filename: Mapped[str] = mapped_column(String(255), default="")
    uploaded_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    visibility: Mapped[str] = mapped_column(String(20), default="connections")  # connections|class|public
    class_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("classes.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    uploader: Mapped["User"] = relationship(foreign_keys=[uploaded_by])
