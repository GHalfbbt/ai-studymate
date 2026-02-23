/**
 * Analytics API service.
 *
 * Two endpoints:
 * - GET /analytics/overview → KPI cards + recommendations
 * - GET /analytics/details  → Chart data (mastery, score trend, weak topics, activity)
 */

import apiClient from './client';

// ── Types ───────────────────────────────────────────────

export interface AnalyticsOverview {
    total_flashcards: number;
    new_count: number;
    learning_count: number;
    mastered_count: number;
    due_today: number;
    avg_exam_score: number | null;
    exam_attempts_count: number;
    study_streak: number;
    recommendations: string[];
}

export interface MasteryDistribution {
    new: number;
    learning: number;
    mastered: number;
}

export interface ScoreTrendPoint {
    date: string;
    avg_score: number;
}

export interface WeakTopic {
    topic: string;
    incorrect_count: number;
}

export interface StudyActivityPoint {
    date: string;
    actions: number;
}

export interface AnalyticsDetails {
    mastery_distribution: MasteryDistribution;
    score_trend: ScoreTrendPoint[];
    weak_topics: WeakTopic[];
    study_activity: StudyActivityPoint[];
}

export interface AnalyticsParams {
    workspace_id?: string;
    course_id?: string;
    subject_id?: string;
}

// ── API Functions ───────────────────────────────────────

export async function getAnalyticsOverview(params: AnalyticsParams = {}): Promise<AnalyticsOverview> {
    const res = await apiClient.get<AnalyticsOverview>('/analytics/overview', { params });
    return res.data;
}

export async function getAnalyticsDetails(params: AnalyticsParams = {}): Promise<AnalyticsDetails> {
    const res = await apiClient.get<AnalyticsDetails>('/analytics/details', { params });
    return res.data;
}
