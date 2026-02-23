"""
Analytics endpoints — read-only aggregated data for the Analytics dashboard.

Two endpoints:
- GET /analytics/overview  → KPI cards + recommendations
- GET /analytics/details   → Chart data (mastery donut, score trend, weak topics, study activity)

All queries are aggregated SQL with JOINs (no N+1).
No schema or model changes required.
"""

from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, cast, Date, func, and_, text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.course import Course
from app.models.exam import Exam, ExamAttempt, ExamAnswer, ExamQuestion
from app.models.flashcard import Flashcard
from app.models.subject import Subject
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsDetailsResponse,
    AnalyticsOverviewResponse,
    MasteryDistribution,
    ScoreTrendPoint,
    StudyActivityPoint,
    WeakTopic,
)

router = APIRouter()


# ── Helpers ──────────────────────────────────────────────

def _resolve_subject_ids(
    db: Session,
    user: User,
    workspace_id: Optional[UUID] = None,
    course_id: Optional[UUID] = None,
    subject_id: Optional[UUID] = None,
) -> List[UUID]:
    """
    Resolve scope parameters to a flat list of subject IDs.

    Priority: subject_id > course_id > workspace_id.
    Single query per scope level, no N+1.
    """
    if subject_id:
        return [subject_id]

    if course_id:
        rows = (
            db.query(Subject.id)
            .filter(Subject.course_id == course_id)
            .all()
        )
        return [r[0] for r in rows]

    if workspace_id:
        rows = (
            db.query(Subject.id)
            .join(Course, Subject.course_id == Course.id)
            .filter(Course.workspace_id == workspace_id)
            .all()
        )
        return [r[0] for r in rows]

    # Fallback: all subjects for the user (across all workspaces)
    from app.models.workspace import Workspace
    rows = (
        db.query(Subject.id)
        .join(Course, Subject.course_id == Course.id)
        .join(Workspace, Course.workspace_id == Workspace.id)
        .filter(Workspace.user_id == user.id)
        .all()
    )
    return [r[0] for r in rows]


def _compute_study_streak(activity_dates: set[date]) -> int:
    """
    Compute consecutive study streak from today backwards.

    Rules:
    - If today has no activity → streak = 0
    - Start at 1 if today has activity
    - Continue while previous day exists in set
    - Stop at first gap
    """
    today = date.today()
    if today not in activity_dates:
        return 0

    streak = 1
    while (today - timedelta(days=streak)) in activity_dates:
        streak += 1
    return streak


def _get_activity_dates(
    db: Session,
    subject_ids: List[UUID],
) -> set[date]:
    """
    Get distinct dates with any study activity (reviews or exam attempts).
    Used for streak calculation.
    """
    if not subject_ids:
        return set()

    # Flashcard review dates
    fc_dates = (
        db.query(cast(Flashcard.last_reviewed, Date))
        .filter(
            Flashcard.subject_id.in_(subject_ids),
            Flashcard.last_reviewed.isnot(None),
        )
        .distinct()
        .all()
    )

    # Exam attempt completion dates
    ea_dates = (
        db.query(cast(ExamAttempt.completed_at, Date))
        .join(Exam, ExamAttempt.exam_id == Exam.id)
        .filter(
            Exam.subject_id.in_(subject_ids),
            ExamAttempt.completed_at.isnot(None),
        )
        .distinct()
        .all()
    )

    dates = set()
    for (d,) in fc_dates:
        if d is not None:
            dates.add(d)
    for (d,) in ea_dates:
        if d is not None:
            dates.add(d)
    return dates


def _build_recommendations(
    total_flashcards: int,
    new_count: int,
    mastered_count: int,
    avg_score: Optional[float],
    streak: int,
    weak_topics: List[WeakTopic],
) -> List[str]:
    """
    Generate rule-based plain text recommendations.
    No ML — simple threshold rules.
    """
    recs: List[str] = []

    # Exam score recommendation
    if avg_score is not None and avg_score < 60:
        recs.append(
            "📉 Your average exam score is below 60%. "
            "Consider reviewing weak topics before taking more exams."
        )

    # Many new flashcards
    if total_flashcards > 0 and new_count > total_flashcards * 0.5:
        recs.append(
            "🆕 You have many unreviewed flashcards. "
            "Start a review session to move them into the learning pool!"
        )

    # Weak topics
    if weak_topics:
        top_topics = ", ".join(wt.topic for wt in weak_topics[:3])
        recs.append(
            f"🎯 Focus on these weak topics: {top_topics}."
        )

    # Mastery encouragement
    if total_flashcards > 0:
        mastered_pct = (mastered_count / total_flashcards) * 100
        if mastered_pct > 60:
            recs.append(
                f"🏆 Great progress! {mastered_pct:.0f}% of your flashcards are mastered."
            )

    # Streak
    if streak > 0:
        recs.append(
            f"🔥 You're on a {streak}-day study streak! Keep it up!"
        )
    else:
        recs.append(
            "💪 Start studying today to build your streak!"
        )

    # Default if no specific recommendations
    if len(recs) <= 1:  # Only streak message
        recs.insert(0, "📚 Keep studying consistently for the best results.")

    return recs


# ── Endpoints ────────────────────────────────────────────

@router.get(
    "/overview",
    response_model=AnalyticsOverviewResponse,
    summary="Analytics overview (KPIs + recommendations)",
)
async def analytics_overview(
    workspace_id: Optional[UUID] = Query(None),
    course_id: Optional[UUID] = Query(None),
    subject_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalyticsOverviewResponse:
    """
    Return KPI data for the analytics dashboard header cards
    and rule-based study recommendations.
    """
    subject_ids = _resolve_subject_ids(
        db, current_user, workspace_id, course_id, subject_id
    )

    if not subject_ids:
        return AnalyticsOverviewResponse(
            recommendations=["📚 Create a workspace and add some study materials to get started!"]
        )

    # Q1: Flashcard pool counts (mutually exclusive, exhaustive)
    fc_stats = db.query(
        func.count().label("total"),
        func.count().filter(
            Flashcard.times_reviewed == 0
        ).label("new_count"),
        func.count().filter(and_(
            Flashcard.times_reviewed >= 3,
            Flashcard.ease_factor >= 2.5,
        )).label("mastered_count"),
        func.count().filter(and_(
            Flashcard.times_reviewed >= 1,
            ~and_(Flashcard.times_reviewed >= 3, Flashcard.ease_factor >= 2.5),
        )).label("learning_count"),
        func.count().filter(and_(
            Flashcard.next_review.isnot(None),
            Flashcard.next_review <= func.now(),
        )).label("due_today"),
    ).filter(
        Flashcard.subject_id.in_(subject_ids)
    ).first()

    total = fc_stats.total or 0
    new_count = fc_stats.new_count or 0
    mastered_count = fc_stats.mastered_count or 0
    learning_count = fc_stats.learning_count or 0
    due_today = fc_stats.due_today or 0

    # Q2: Exam stats (last 30 days, JOIN)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    exam_stats = db.query(
        func.coalesce(func.avg(ExamAttempt.score), 0).label("avg_score"),
        func.count().label("attempts_count"),
    ).join(
        Exam, ExamAttempt.exam_id == Exam.id
    ).filter(
        Exam.subject_id.in_(subject_ids),
        ExamAttempt.status == "completed",
        ExamAttempt.completed_at >= thirty_days_ago,
    ).first()

    avg_score_val = float(exam_stats.avg_score) if exam_stats.avg_score else None
    attempts_count = exam_stats.attempts_count or 0

    # If no completed attempts, set avg to None
    if attempts_count == 0:
        avg_score_val = None

    # Q3: Study streak
    activity_dates = _get_activity_dates(db, subject_ids)
    streak = _compute_study_streak(activity_dates)

    # Q4: Recommendations (needs weak topics — quick fetch top 3)
    weak_topics_rows = (
        db.query(
            ExamQuestion.topic,
            func.count().label("incorrect_count"),
        )
        .join(ExamAnswer, ExamAnswer.question_id == ExamQuestion.id)
        .join(ExamAttempt, ExamAnswer.attempt_id == ExamAttempt.id)
        .join(Exam, ExamAttempt.exam_id == Exam.id)
        .filter(
            ExamAnswer.is_correct == False,  # noqa: E712
            ExamQuestion.topic.isnot(None),
            Exam.subject_id.in_(subject_ids),
        )
        .group_by(ExamQuestion.topic)
        .order_by(func.count().desc())
        .limit(3)
        .all()
    )
    weak_topics_for_recs = [
        WeakTopic(topic=row.topic, incorrect_count=row.incorrect_count)
        for row in weak_topics_rows
    ]

    recommendations = _build_recommendations(
        total_flashcards=total,
        new_count=new_count,
        mastered_count=mastered_count,
        avg_score=avg_score_val,
        streak=streak,
        weak_topics=weak_topics_for_recs,
    )

    return AnalyticsOverviewResponse(
        total_flashcards=total,
        new_count=new_count,
        learning_count=learning_count,
        mastered_count=mastered_count,
        due_today=due_today,
        avg_exam_score=round(avg_score_val, 1) if avg_score_val is not None else None,
        exam_attempts_count=attempts_count,
        study_streak=streak,
        recommendations=recommendations,
    )


@router.get(
    "/details",
    response_model=AnalyticsDetailsResponse,
    summary="Analytics details (chart data)",
)
async def analytics_details(
    workspace_id: Optional[UUID] = Query(None),
    course_id: Optional[UUID] = Query(None),
    subject_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalyticsDetailsResponse:
    """
    Return chart data for the analytics dashboard:
    mastery donut, score trend, weak topics, study activity.
    """
    subject_ids = _resolve_subject_ids(
        db, current_user, workspace_id, course_id, subject_id
    )

    if not subject_ids:
        return AnalyticsDetailsResponse()

    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    # Q5: Mastery distribution (same logic as Q1)
    fc_stats = db.query(
        func.count().filter(
            Flashcard.times_reviewed == 0
        ).label("new_count"),
        func.count().filter(and_(
            Flashcard.times_reviewed >= 3,
            Flashcard.ease_factor >= 2.5,
        )).label("mastered_count"),
        func.count().filter(and_(
            Flashcard.times_reviewed >= 1,
            ~and_(Flashcard.times_reviewed >= 3, Flashcard.ease_factor >= 2.5),
        )).label("learning_count"),
    ).filter(
        Flashcard.subject_id.in_(subject_ids)
    ).first()

    mastery = MasteryDistribution(
        new=fc_stats.new_count or 0,
        learning=fc_stats.learning_count or 0,
        mastered=fc_stats.mastered_count or 0,
    )

    # Q6: Score trend (last 30 days, GROUP BY date, AVG, ASC)
    score_trend_rows = (
        db.query(
            cast(ExamAttempt.completed_at, Date).label("d"),
            func.avg(ExamAttempt.score).label("avg_score"),
        )
        .join(Exam, ExamAttempt.exam_id == Exam.id)
        .filter(
            Exam.subject_id.in_(subject_ids),
            ExamAttempt.status == "completed",
            ExamAttempt.completed_at >= thirty_days_ago,
        )
        .group_by(cast(ExamAttempt.completed_at, Date))
        .order_by(cast(ExamAttempt.completed_at, Date).asc())
        .all()
    )
    score_trend = [
        ScoreTrendPoint(
            date=row.d.isoformat() if row.d else "",
            avg_score=round(float(row.avg_score), 1),
        )
        for row in score_trend_rows
        if row.d is not None
    ]

    # Q7: Weak topics (top 5, JOIN chain, incorrect only)
    weak_topics_rows = (
        db.query(
            ExamQuestion.topic,
            func.count().label("incorrect_count"),
        )
        .join(ExamAnswer, ExamAnswer.question_id == ExamQuestion.id)
        .join(ExamAttempt, ExamAnswer.attempt_id == ExamAttempt.id)
        .join(Exam, ExamAttempt.exam_id == Exam.id)
        .filter(
            ExamAnswer.is_correct == False,  # noqa: E712
            ExamQuestion.topic.isnot(None),
            Exam.subject_id.in_(subject_ids),
        )
        .group_by(ExamQuestion.topic)
        .order_by(func.count().desc())
        .limit(5)
        .all()
    )
    weak_topics = [
        WeakTopic(topic=row.topic, incorrect_count=row.incorrect_count)
        for row in weak_topics_rows
    ]

    # Q8: Study activity (last 30 days, UNION ALL + GROUP BY)
    # Flashcard reviews per day
    fc_activity = (
        db.query(
            cast(Flashcard.last_reviewed, Date).label("d"),
            func.count().label("cnt"),
        )
        .filter(
            Flashcard.subject_id.in_(subject_ids),
            Flashcard.last_reviewed.isnot(None),
            Flashcard.last_reviewed >= thirty_days_ago,
        )
        .group_by(cast(Flashcard.last_reviewed, Date))
        .subquery()
    )

    # Exam attempts per day
    ea_activity = (
        db.query(
            cast(ExamAttempt.completed_at, Date).label("d"),
            func.count().label("cnt"),
        )
        .join(Exam, ExamAttempt.exam_id == Exam.id)
        .filter(
            Exam.subject_id.in_(subject_ids),
            ExamAttempt.completed_at.isnot(None),
            ExamAttempt.completed_at >= thirty_days_ago,
        )
        .group_by(cast(ExamAttempt.completed_at, Date))
        .subquery()
    )

    # Combine using UNION ALL via raw SQL for clean aggregation
    # We'll use a simpler approach: query both and merge in Python
    fc_rows = db.query(fc_activity.c.d, fc_activity.c.cnt).all()
    ea_rows = db.query(ea_activity.c.d, ea_activity.c.cnt).all()

    # Merge by date
    activity_map: dict[date, int] = {}
    for row in fc_rows:
        if row.d is not None:
            activity_map[row.d] = activity_map.get(row.d, 0) + row.cnt
    for row in ea_rows:
        if row.d is not None:
            activity_map[row.d] = activity_map.get(row.d, 0) + row.cnt

    study_activity = [
        StudyActivityPoint(date=d.isoformat(), actions=cnt)
        for d, cnt in sorted(activity_map.items())
    ]

    return AnalyticsDetailsResponse(
        mastery_distribution=mastery,
        score_trend=score_trend,
        weak_topics=weak_topics,
        study_activity=study_activity,
    )
