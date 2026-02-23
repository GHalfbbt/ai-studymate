"""
Analytics Pydantic schemas for request/response validation.

Two consolidated endpoints: overview (KPIs + recommendations)
and details (charts data).
"""

from typing import List, Optional
from pydantic import BaseModel


# ── Nested models ────────────────────────────────────────

class MasteryDistribution(BaseModel):
    """Flashcard pool distribution for donut chart."""
    new: int = 0
    learning: int = 0
    mastered: int = 0


class ScoreTrendPoint(BaseModel):
    """Single data point for exam score trend line chart."""
    date: str
    avg_score: float


class WeakTopic(BaseModel):
    """Topic with highest incorrect answer count."""
    topic: str
    incorrect_count: int


class StudyActivityPoint(BaseModel):
    """Single day of study activity for bar chart."""
    date: str
    actions: int


# ── Response schemas ─────────────────────────────────────

class AnalyticsOverviewResponse(BaseModel):
    """
    GET /analytics/overview response.

    Contains KPI card data and rule-based recommendations.
    """
    # Flashcard KPIs
    total_flashcards: int = 0
    new_count: int = 0
    learning_count: int = 0
    mastered_count: int = 0
    due_today: int = 0

    # Exam KPIs (last 30 days)
    avg_exam_score: Optional[float] = None
    exam_attempts_count: int = 0

    # Study streak (consecutive days with activity)
    study_streak: int = 0

    # Rule-based recommendations
    recommendations: List[str] = []


class AnalyticsDetailsResponse(BaseModel):
    """
    GET /analytics/details response.

    Contains chart data for mastery donut, score trend,
    weak topics, and study activity.
    """
    # Mastery donut chart
    mastery_distribution: MasteryDistribution = MasteryDistribution()

    # Score trend line chart (last 30 days, per day AVG)
    score_trend: List[ScoreTrendPoint] = []

    # Weak topics horizontal bar (top 5, incorrect only)
    weak_topics: List[WeakTopic] = []

    # Study activity bar chart (last 30 days)
    study_activity: List[StudyActivityPoint] = []
