"""
Workspace, Course, and Subject management endpoints.

Provides CRUD operations for the organizational hierarchy:
Workspace → Course → Subject → Documents
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.workspace import Workspace
from app.models.course import Course
from app.models.subject import Subject
from app.schemas.workspace import (
    WorkspaceCreate, WorkspaceResponse,
    CourseCreate, CourseResponse,
    SubjectCreate, SubjectResponse,
)

router = APIRouter()


# ─── Workspaces ──────────────────────────────────────────

@router.get("/", response_model=List[WorkspaceResponse], summary="List workspaces")
async def list_workspaces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all workspaces belonging to the current user."""
    workspaces = (
        db.query(Workspace)
        .filter(Workspace.user_id == current_user.id)
        .order_by(Workspace.created_at.desc())
        .all()
    )
    # Calculate course counts
    results = []
    for ws in workspaces:
        course_count = db.query(Course).filter(Course.workspace_id == ws.id).count()
        results.append(WorkspaceResponse(
            id=ws.id, name=ws.name, description=ws.description,
            created_at=ws.created_at, course_count=course_count,
        ))
    return results


@router.post("/", response_model=WorkspaceResponse, status_code=201, summary="Create workspace")
async def create_workspace(
    data: WorkspaceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new workspace for the current user."""
    workspace = Workspace(
        name=data.name,
        description=data.description,
        user_id=current_user.id,
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


# ─── Courses ─────────────────────────────────────────────

@router.get("/{workspace_id}/courses", response_model=List[CourseResponse], summary="List courses")
async def list_courses(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all courses in a workspace."""
    workspace = _get_user_workspace(workspace_id, current_user, db)
    courses = (
        db.query(Course)
        .filter(Course.workspace_id == workspace.id)
        .order_by(Course.created_at.desc())
        .all()
    )
    # Calculate subject counts
    results = []
    for c in courses:
        subject_count = db.query(Subject).filter(Subject.course_id == c.id).count()
        results.append(CourseResponse(
            id=c.id, workspace_id=c.workspace_id, name=c.name,
            created_at=c.created_at, subject_count=subject_count,
        ))
    return results


@router.post("/{workspace_id}/courses", response_model=CourseResponse, status_code=201, summary="Create course")
async def create_course(
    workspace_id: UUID,
    data: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new course inside a workspace."""
    workspace = _get_user_workspace(workspace_id, current_user, db)
    course = Course(
        name=data.name,
        workspace_id=workspace.id,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


# ─── Subjects ────────────────────────────────────────────

@router.get(
    "/{workspace_id}/courses/{course_id}/subjects",
    response_model=List[SubjectResponse],
    summary="List subjects",
)
async def list_subjects(
    workspace_id: UUID,
    course_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all subjects in a course."""
    _get_user_workspace(workspace_id, current_user, db)
    course = db.query(Course).filter(
        Course.id == course_id, Course.workspace_id == workspace_id
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    subjects = (
        db.query(Subject)
        .filter(Subject.course_id == course.id)
        .order_by(Subject.created_at.desc())
        .all()
    )
    return subjects


@router.post(
    "/{workspace_id}/courses/{course_id}/subjects",
    response_model=SubjectResponse,
    status_code=201,
    summary="Create subject",
)
async def create_subject(
    workspace_id: UUID,
    course_id: UUID,
    data: SubjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new subject inside a course."""
    _get_user_workspace(workspace_id, current_user, db)
    course = db.query(Course).filter(
        Course.id == course_id, Course.workspace_id == workspace_id
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    subject = Subject(
        name=data.name,
        color=data.color,
        course_id=course.id,
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


# ─── Helpers ─────────────────────────────────────────────

def _get_user_workspace(workspace_id: UUID, user: User, db: Session) -> Workspace:
    """Get workspace ensuring it belongs to the user."""
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id, Workspace.user_id == user.id
    ).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace
