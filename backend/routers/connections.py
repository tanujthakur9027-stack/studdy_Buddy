"""
routers/connections.py — Student: search students, connect, manage connections.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database import get_db
from dependencies.auth import get_current_user
from models.db_models import User, StudentProfile, ConnectionRequest, StudentConnection
from services.notification_service import create_notification

router = APIRouter(tags=["Connections"])


class StudentSearchOut(BaseModel):
    user_id: str
    full_name: str
    student_id: str
    course: str
    branch: str
    semester: str
    section: str
    profile_photo_url: Optional[str]


class ConnectionRequestOut(BaseModel):
    id: str
    from_user_id: str
    from_user_name: str
    to_user_id: str
    status: str
    created_at: str


class ConnectionOut(BaseModel):
    connection_id: str
    user_id: str
    full_name: str
    student_id: str
    course: str
    profile_photo_url: Optional[str]
    connected_at: str


@router.get("/students/search", response_model=list[StudentSearchOut])
async def search_students(
    q: str = "",
    course: Optional[str] = None,
    semester: Optional[str] = None,
    section: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(User, StudentProfile)
        .join(StudentProfile, StudentProfile.user_id == User.id)
        .where(User.role == "student", User.id != current_user.id, User.is_active == True)  # noqa: E712
    )
    if q:
        query = query.where(
            or_(
                User.full_name.ilike(f"%{q}%"),
                StudentProfile.student_id.ilike(f"%{q}%"),
            )
        )
    if course:
        query = query.where(StudentProfile.course.ilike(f"%{course}%"))
    if semester:
        query = query.where(StudentProfile.semester == semester)
    if section:
        query = query.where(StudentProfile.section == section)

    result = await db.execute(query.limit(50))
    return [
        StudentSearchOut(
            user_id=u.id, full_name=u.full_name,
            student_id=p.student_id, course=p.course,
            branch=p.branch, semester=p.semester, section=p.section,
            profile_photo_url=p.profile_photo_url,
        )
        for u, p in result.all()
    ]


@router.post("/connections/request")
async def send_request(
    to_user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if to_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot connect with yourself")

    # Check already requested
    existing = await db.execute(
        select(ConnectionRequest).where(
            or_(
                and_(ConnectionRequest.from_user_id == current_user.id, ConnectionRequest.to_user_id == to_user_id),
                and_(ConnectionRequest.from_user_id == to_user_id, ConnectionRequest.to_user_id == current_user.id),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Request already exists")

    req = ConnectionRequest(from_user_id=current_user.id, to_user_id=to_user_id)
    db.add(req)
    await db.flush()

    await create_notification(
        db, to_user_id,
        title="Connection Request",
        message=f"{current_user.full_name} sent you a connection request.",
        notif_type="connection",
        reference_id=req.id,
    )

    await db.commit()
    return {"message": "Connection request sent", "request_id": req.id}


@router.patch("/connections/{request_id}/respond")
async def respond_request(
    request_id: str,
    accept: bool,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ConnectionRequest).where(
            ConnectionRequest.id == request_id,
            ConnectionRequest.to_user_id == current_user.id,
            ConnectionRequest.status == "pending",
        )
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    if accept:
        req.status = "accepted"
        conn = StudentConnection(user_a_id=req.from_user_id, user_b_id=req.to_user_id)
        db.add(conn)
        await create_notification(
            db, req.from_user_id,
            title="Connection Accepted",
            message=f"{current_user.full_name} accepted your connection request.",
            notif_type="connection",
        )
    else:
        req.status = "rejected"

    await db.commit()
    return {"message": "accepted" if accept else "rejected"}


@router.get("/connections", response_model=list[ConnectionOut])
async def list_connections(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(StudentConnection).where(
            or_(
                StudentConnection.user_a_id == current_user.id,
                StudentConnection.user_b_id == current_user.id,
            )
        ).order_by(StudentConnection.connected_at.desc())
    )
    connections = result.scalars().all()

    out = []
    for c in connections:
        other_id = c.user_b_id if c.user_a_id == current_user.id else c.user_a_id
        u_result = await db.execute(select(User).where(User.id == other_id))
        other = u_result.scalar_one_or_none()
        p_result = await db.execute(select(StudentProfile).where(StudentProfile.user_id == other_id))
        profile = p_result.scalar_one_or_none()
        if other:
            out.append(ConnectionOut(
                connection_id=c.id,
                user_id=other.id,
                full_name=other.full_name,
                student_id=profile.student_id if profile else "",
                course=profile.course if profile else "",
                profile_photo_url=profile.profile_photo_url if profile else None,
                connected_at=str(c.connected_at),
            ))
    return out


@router.get("/connections/requests/incoming", response_model=list[ConnectionRequestOut])
async def incoming_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ConnectionRequest, User)
        .join(User, ConnectionRequest.from_user_id == User.id)
        .where(
            ConnectionRequest.to_user_id == current_user.id,
            ConnectionRequest.status == "pending",
        )
    )
    return [
        ConnectionRequestOut(
            id=req.id, from_user_id=req.from_user_id,
            from_user_name=u.full_name, to_user_id=req.to_user_id,
            status=req.status, created_at=str(req.created_at),
        )
        for req, u in result.all()
    ]


@router.delete("/connections/{connection_id}")
async def remove_connection(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(StudentConnection).where(
            StudentConnection.id == connection_id,
            or_(
                StudentConnection.user_a_id == current_user.id,
                StudentConnection.user_b_id == current_user.id,
            ),
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    await db.delete(conn)
    await db.commit()
    return {"message": "Connection removed"}
