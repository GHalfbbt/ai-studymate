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
from app.models.topic import Topic
from app.models.document import Document
from app.schemas.workspace import (
    WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse,
    CourseCreate, CourseUpdate, CourseResponse,
    SubjectCreate, SubjectUpdate, SubjectResponse,
    TopicCreate, TopicUpdate, TopicResponse,
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
        .order_by(Course.position, Course.created_at)
        .all()
    )
    # Calculate subject counts
    results = []
    for c in courses:
        subject_count = db.query(Subject).filter(Subject.course_id == c.id).count()
        results.append(CourseResponse(
            id=c.id, workspace_id=c.workspace_id, name=c.name,
            position=c.position, created_at=c.created_at, subject_count=subject_count,
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
    
    # Auto-assign position if not provided
    if data.position is None:
        max_pos = db.query(Course).filter(Course.workspace_id == workspace.id).count()
        position = max_pos
    else:
        position = data.position
    
    course = Course(
        name=data.name,
        workspace_id=workspace.id,
        position=position,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return CourseResponse(
        id=course.id, workspace_id=course.workspace_id, name=course.name,
        position=course.position, created_at=course.created_at, subject_count=0,
    )


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
        .order_by(Subject.position, Subject.created_at)
        .all()
    )
    results = []
    for s in subjects:
        doc_count = db.query(Document).filter(Document.subject_id == s.id).count()
        topic_count = db.query(Topic).filter(Topic.subject_id == s.id).count()
        results.append(SubjectResponse(
            id=s.id, course_id=s.course_id, name=s.name, color=s.color,
            position=s.position, created_at=s.created_at,
            document_count=doc_count, topic_count=topic_count,
        ))
    return results


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

    # Auto-assign position if not provided
    if data.position is None:
        max_pos = db.query(Subject).filter(Subject.course_id == course.id).count()
        position = max_pos
    else:
        position = data.position

    subject = Subject(
        name=data.name,
        color=data.color,
        course_id=course.id,
        position=position,
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return SubjectResponse(
        id=subject.id, course_id=subject.course_id, name=subject.name,
        color=subject.color, position=subject.position, created_at=subject.created_at,
        document_count=0, topic_count=0,
    )


# ─── Helpers ─────────────────────────────────────────────

def _get_user_workspace(workspace_id: UUID, user: User, db: Session) -> Workspace:
    """Get workspace ensuring it belongs to the user."""
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id, Workspace.user_id == user.id
    ).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@router.patch("/{workspace_id}", response_model=WorkspaceResponse, summary="Update workspace")
async def update_workspace(
    workspace_id: UUID,
    data: WorkspaceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update workspace name or description."""
    workspace = _get_user_workspace(workspace_id, current_user, db)
    if data.name is not None:
        workspace.name = data.name
    if data.description is not None:
        workspace.description = data.description
    db.commit()
    db.refresh(workspace)
    course_count = db.query(Course).filter(Course.workspace_id == workspace.id).count()
    return WorkspaceResponse(
        id=workspace.id, name=workspace.name, description=workspace.description,
        created_at=workspace.created_at, course_count=course_count,
    )


@router.delete("/{workspace_id}", status_code=204, summary="Delete workspace")
async def delete_workspace(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete workspace and all its contents (cascade)."""
    workspace = _get_user_workspace(workspace_id, current_user, db)
    db.delete(workspace)
    db.commit()
    return None


@router.patch("/{workspace_id}/courses/{course_id}", response_model=CourseResponse, summary="Update course")
async def update_course(
    workspace_id: UUID,
    course_id: UUID,
    data: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update course name or position."""
    _get_user_workspace(workspace_id, current_user, db)
    course = db.query(Course).filter(
        Course.id == course_id, Course.workspace_id == workspace_id
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if data.name is not None:
        course.name = data.name
    if data.position is not None:
        course.position = data.position
    db.commit()
    db.refresh(course)
    subject_count = db.query(Subject).filter(Subject.course_id == course.id).count()
    return CourseResponse(
        id=course.id, workspace_id=course.workspace_id, name=course.name,
        position=course.position, created_at=course.created_at, subject_count=subject_count,
    )


@router.delete("/{workspace_id}/courses/{course_id}", status_code=204, summary="Delete course")
async def delete_course(
    workspace_id: UUID,
    course_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete course and all its contents (cascade)."""
    _get_user_workspace(workspace_id, current_user, db)
    course = db.query(Course).filter(
        Course.id == course_id, Course.workspace_id == workspace_id
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    db.delete(course)
    db.commit()
    return None


@router.patch(
    "/{workspace_id}/courses/{course_id}/subjects/{subject_id}",
    response_model=SubjectResponse,
    summary="Update subject",
)
async def update_subject(
    workspace_id: UUID,
    course_id: UUID,
    subject_id: UUID,
    data: SubjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update subject name, color, or position."""
    _get_user_workspace(workspace_id, current_user, db)
    subject = db.query(Subject).filter(
        Subject.id == subject_id, Subject.course_id == course_id
    ).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    if data.name is not None:
        subject.name = data.name
    if data.color is not None:
        subject.color = data.color
    if data.position is not None:
        subject.position = data.position
    db.commit()
    db.refresh(subject)
    document_count = db.query(Document).filter(Document.subject_id == subject.id).count()
    topic_count = db.query(Topic).filter(Topic.subject_id == subject.id).count()
    return SubjectResponse(
        id=subject.id, course_id=subject.course_id, name=subject.name,
        color=subject.color, position=subject.position, created_at=subject.created_at,
        document_count=document_count, topic_count=topic_count,
    )


@router.delete(
    "/{workspace_id}/courses/{course_id}/subjects/{subject_id}",
    status_code=204,
    summary="Delete subject",
)
async def delete_subject(
    workspace_id: UUID,
    course_id: UUID,
    subject_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete subject and all its contents (cascade)."""
    _get_user_workspace(workspace_id, current_user, db)
    subject = db.query(Subject).filter(
        Subject.id == subject_id, Subject.course_id == course_id
    ).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    db.delete(subject)
    db.commit()
    return None


# ─── Topics ──────────────────────────────────────────────

@router.get(
    "/{workspace_id}/courses/{course_id}/subjects/{subject_id}/topics",
    response_model=List[TopicResponse],
    summary="List topics",
)
async def list_topics(
    workspace_id: UUID,
    course_id: UUID,
    subject_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all topics in a subject."""
    _get_user_workspace(workspace_id, current_user, db)
    subject = db.query(Subject).filter(
        Subject.id == subject_id, Subject.course_id == course_id
    ).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    topics = (
        db.query(Topic)
        .filter(Topic.subject_id == subject.id)
        .order_by(Topic.position, Topic.created_at)
        .all()
    )
    results = []
    for t in topics:
        doc_count = db.query(Document).filter(Document.topic_id == t.id).count()
        results.append(TopicResponse(
            id=t.id, subject_id=t.subject_id, name=t.name,
            position=t.position, created_at=t.created_at, document_count=doc_count,
        ))
    return results


@router.post(
    "/{workspace_id}/courses/{course_id}/subjects/{subject_id}/topics",
    response_model=TopicResponse,
    status_code=201,
    summary="Create topic",
)
async def create_topic(
    workspace_id: UUID,
    course_id: UUID,
    subject_id: UUID,
    data: TopicCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new topic inside a subject."""
    _get_user_workspace(workspace_id, current_user, db)
    subject = db.query(Subject).filter(
        Subject.id == subject_id, Subject.course_id == course_id
    ).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    # Auto-assign position if not provided
    if data.position is None:
        max_pos = db.query(Topic).filter(Topic.subject_id == subject.id).count()
        position = max_pos
    else:
        position = data.position

    topic = Topic(
        name=data.name,
        subject_id=subject.id,
        position=position,
    )
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return TopicResponse(
        id=topic.id, subject_id=topic.subject_id, name=topic.name,
        position=topic.position, created_at=topic.created_at, document_count=0,
    )


@router.patch(
    "/{workspace_id}/courses/{course_id}/subjects/{subject_id}/topics/{topic_id}",
    response_model=TopicResponse,
    summary="Update topic",
)
async def update_topic(
    workspace_id: UUID,
    course_id: UUID,
    subject_id: UUID,
    topic_id: UUID,
    data: TopicUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update topic name or position."""
    _get_user_workspace(workspace_id, current_user, db)
    topic = db.query(Topic).filter(
        Topic.id == topic_id, Topic.subject_id == subject_id
    ).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    if data.name is not None:
        topic.name = data.name
    if data.position is not None:
        topic.position = data.position
    db.commit()
    db.refresh(topic)
    doc_count = db.query(Document).filter(Document.topic_id == topic.id).count()
    return TopicResponse(
        id=topic.id, subject_id=topic.subject_id, name=topic.name,
        position=topic.position, created_at=topic.created_at, document_count=doc_count,
    )


@router.delete(
    "/{workspace_id}/courses/{course_id}/subjects/{subject_id}/topics/{topic_id}",
    status_code=204,
    summary="Delete topic",
)
async def delete_topic(
    workspace_id: UUID,
    course_id: UUID,
    subject_id: UUID,
    topic_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete topic and all its contents (cascade)."""
    _get_user_workspace(workspace_id, current_user, db)
    topic = db.query(Topic).filter(
        Topic.id == topic_id, Topic.subject_id == subject_id
    ).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    db.delete(topic)
    db.commit()
    return None
