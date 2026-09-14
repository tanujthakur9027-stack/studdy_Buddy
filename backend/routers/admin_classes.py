"""
routers/admin_classes.py — Admin: CRUD for classes, sections, subjects.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database import get_db
from dependencies.auth import require_admin
from models.db_models import Class, Section, Subject, User

router = APIRouter(prefix="/admin", tags=["Admin - Classes"])


# ── Classes ────────────────────────────────────────────────────────────────────

class ClassCreate(BaseModel):
    name: str
    course: str = ""


class ClassOut(BaseModel):
    id: str
    name: str
    course: str
    created_at: str


@router.get("/classes", response_model=list[ClassOut])
async def list_classes(admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Class).order_by(Class.name))
    return [ClassOut(id=c.id, name=c.name, course=c.course, created_at=str(c.created_at)) for c in result.scalars()]


@router.post("/classes", response_model=ClassOut, status_code=201)
async def create_class(body: ClassCreate, admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    klass = Class(name=body.name, course=body.course, created_by=admin.id)
    db.add(klass)
    await db.commit()
    await db.refresh(klass)
    return ClassOut(id=klass.id, name=klass.name, course=klass.course, created_at=str(klass.created_at))


@router.patch("/classes/{class_id}", response_model=ClassOut)
async def update_class(class_id: str, body: ClassCreate, admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Class).where(Class.id == class_id))
    klass = result.scalar_one_or_none()
    if not klass:
        raise HTTPException(status_code=404, detail="Class not found")
    klass.name = body.name
    klass.course = body.course
    await db.commit()
    return ClassOut(id=klass.id, name=klass.name, course=klass.course, created_at=str(klass.created_at))


@router.delete("/classes/{class_id}")
async def delete_class(class_id: str, admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Class).where(Class.id == class_id))
    klass = result.scalar_one_or_none()
    if not klass:
        raise HTTPException(status_code=404, detail="Class not found")
    await db.delete(klass)
    await db.commit()
    return {"message": "Class deleted"}


# ── Sections ───────────────────────────────────────────────────────────────────

class SectionCreate(BaseModel):
    name: str
    class_id: str


class SectionOut(BaseModel):
    id: str
    name: str
    class_id: str
    created_at: str


@router.get("/sections", response_model=list[SectionOut])
async def list_sections(class_id: Optional[str] = None, admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    q = select(Section)
    if class_id:
        q = q.where(Section.class_id == class_id)
    result = await db.execute(q.order_by(Section.name))
    return [SectionOut(id=s.id, name=s.name, class_id=s.class_id, created_at=str(s.created_at)) for s in result.scalars()]


@router.post("/sections", response_model=SectionOut, status_code=201)
async def create_section(body: SectionCreate, admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    section = Section(name=body.name, class_id=body.class_id)
    db.add(section)
    await db.commit()
    await db.refresh(section)
    return SectionOut(id=section.id, name=section.name, class_id=section.class_id, created_at=str(section.created_at))


@router.delete("/sections/{section_id}")
async def delete_section(section_id: str, admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Section).where(Section.id == section_id))
    section = result.scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    await db.delete(section)
    await db.commit()
    return {"message": "Section deleted"}


# ── Subjects ───────────────────────────────────────────────────────────────────

class SubjectCreate(BaseModel):
    name: str
    code: str = ""
    class_id: str


class SubjectOut(BaseModel):
    id: str
    name: str
    code: str
    class_id: str
    created_at: str


@router.get("/subjects", response_model=list[SubjectOut])
async def list_subjects(class_id: Optional[str] = None, admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    q = select(Subject)
    if class_id:
        q = q.where(Subject.class_id == class_id)
    result = await db.execute(q.order_by(Subject.name))
    return [SubjectOut(id=s.id, name=s.name, code=s.code, class_id=s.class_id, created_at=str(s.created_at)) for s in result.scalars()]


@router.post("/subjects", response_model=SubjectOut, status_code=201)
async def create_subject(body: SubjectCreate, admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    subject = Subject(name=body.name, code=body.code, class_id=body.class_id, created_by=admin.id)
    db.add(subject)
    await db.commit()
    await db.refresh(subject)
    return SubjectOut(id=subject.id, name=subject.name, code=subject.code, class_id=subject.class_id, created_at=str(subject.created_at))


@router.patch("/subjects/{subject_id}", response_model=SubjectOut)
async def update_subject(subject_id: str, body: SubjectCreate, admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Subject).where(Subject.id == subject_id))
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    subject.name = body.name
    subject.code = body.code
    subject.class_id = body.class_id
    await db.commit()
    return SubjectOut(id=subject.id, name=subject.name, code=subject.code, class_id=subject.class_id, created_at=str(subject.created_at))


@router.delete("/subjects/{subject_id}")
async def delete_subject(subject_id: str, admin=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Subject).where(Subject.id == subject_id))
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    await db.delete(subject)
    await db.commit()
    return {"message": "Subject deleted"}


# ── Student-facing class/subject reads ────────────────────────────────────────

from dependencies.auth import get_current_user  # noqa: E402

student_router = APIRouter(prefix="/students", tags=["Student - Classes"])


@student_router.get("/classes", response_model=list[ClassOut])
async def student_list_classes(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Class).order_by(Class.name))
    return [ClassOut(id=c.id, name=c.name, course=c.course, created_at=str(c.created_at)) for c in result.scalars()]


@student_router.get("/subjects", response_model=list[SubjectOut])
async def student_list_subjects(class_id: Optional[str] = None, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    q = select(Subject)
    if class_id:
        q = q.where(Subject.class_id == class_id)
    result = await db.execute(q.order_by(Subject.name))
    return [SubjectOut(id=s.id, name=s.name, code=s.code, class_id=s.class_id, created_at=str(s.created_at)) for s in result.scalars()]
