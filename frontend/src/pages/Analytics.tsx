/**
 * Analytics dashboard page — SaaS-style study performance tracking.
 *
 * Layout (mandatory):
 * 1) Header (Title + Scope selector)
 * 2) KPI Cards (5-card grid)
 * 3) Two-column: Left = Flashcards mastery donut, Right = Score trend + Weak topics
 * 4) Full-width Study Activity bar chart (last 30 days)
 * 5) Full-width Recommendations panel
 *
 * All data is read-only, fetched from 2 endpoints:
 * GET /analytics/overview and GET /analytics/details
 */

import { useState, useEffect, useCallback } from 'react';
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  BarChart, Bar,
} from 'recharts';
import { listWorkspaces, listCourses, listSubjects } from '../api/workspaces';
import {
  getAnalyticsOverview,
  getAnalyticsDetails,
  type AnalyticsOverview,
  type AnalyticsDetails,
  type AnalyticsParams,
} from '../api/analytics';

// ── Types ───────────────────────────────────────────────

interface ScopeOption {
  id: string;
  name: string;
  label: string;
  type: 'workspace' | 'course' | 'subject';
}

// ── Constants ───────────────────────────────────────────

const DONUT_COLORS = {
  new: '#ef4444',
  learning: '#eab308',
  mastered: '#22c55e',
};

const CARD_STYLE: React.CSSProperties = {
  background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.8), rgba(15, 23, 42, 0.9))',
  border: '1px solid rgba(99, 102, 241, 0.1)',
  borderRadius: 16,
  padding: '1.5rem',
};

const SECTION_GAP = '2rem';

// ── Helpers ─────────────────────────────────────────────

function scoreColor(score: number | null): string {
  if (score === null) return 'rgba(226,232,240,0.5)';
  if (score >= 75) return '#22c55e';
  if (score >= 50) return '#eab308';
  return '#ef4444';
}

function masteredColor(total: number, mastered: number): string {
  if (total === 0) return 'rgba(226,232,240,0.5)';
  const pct = (mastered / total) * 100;
  return pct > 60 ? '#22c55e' : 'rgba(226,232,240,0.7)';
}

function EmptyState({ message }: { message: string }) {
  return (
    <div style={{
      textAlign: 'center',
      padding: '2rem 1rem',
      color: 'rgba(226,232,240,0.4)',
      fontSize: '0.9rem',
    }}>
      {message}
    </div>
  );
}

// ── Component ───────────────────────────────────────────

export default function Analytics() {
  // Scope
  const [scopes, setScopes] = useState<ScopeOption[]>([]);
  const [selectedScope, setSelectedScope] = useState('');
  const [selectedType, setSelectedType] = useState<'workspace' | 'course' | 'subject'>('workspace');

  // Data
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [details, setDetails] = useState<AnalyticsDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // ── Load scopes ─────────────────────────────────────
  useEffect(() => {
    loadScopes();
  }, []);

  async function loadScopes() {
    try {
      const wsList = await listWorkspaces();
      const opts: ScopeOption[] = [];
      for (const ws of wsList) {
        opts.push({ id: ws.id, name: ws.name, label: `🗂️ ${ws.name}`, type: 'workspace' });
        const courses = await listCourses(ws.id);
        for (const course of courses) {
          opts.push({ id: course.id, name: course.name, label: `  📖 ${course.name}`, type: 'course' });
          const subjects = await listSubjects(ws.id, course.id);
          for (const subject of subjects) {
            opts.push({ id: subject.id, name: subject.name, label: `    📝 ${subject.name}`, type: 'subject' });
          }
        }
      }
      setScopes(opts);
      if (opts.length > 0) {
        setSelectedScope(opts[0].id);
        setSelectedType(opts[0].type);
      }
    } catch {
      console.error('Failed to load scopes');
    }
  }

  // ── Fetch analytics ─────────────────────────────────
  const fetchAnalytics = useCallback(async () => {
    if (!selectedScope) return;
    setLoading(true);
    setError('');
    try {
      const params: AnalyticsParams = {};
      if (selectedType === 'workspace') params.workspace_id = selectedScope;
      else if (selectedType === 'course') params.course_id = selectedScope;
      else params.subject_id = selectedScope;

      const [ov, dt] = await Promise.all([
        getAnalyticsOverview(params),
        getAnalyticsDetails(params),
      ]);
      setOverview(ov);
      setDetails(dt);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load analytics';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [selectedScope, selectedType]);

  useEffect(() => {
    if (selectedScope) fetchAnalytics();
  }, [selectedScope, fetchAnalytics]);

  function handleScopeChange(newId: string) {
    const scope = scopes.find(s => s.id === newId);
    if (scope) {
      setSelectedScope(scope.id);
      setSelectedType(scope.type);
    }
  }

  // ── Derived data ────────────────────────────────────
  const masteryData = details ? [
    { name: 'New', value: details.mastery_distribution.new, color: DONUT_COLORS.new },
    { name: 'Learning', value: details.mastery_distribution.learning, color: DONUT_COLORS.learning },
    { name: 'Mastered', value: details.mastery_distribution.mastered, color: DONUT_COLORS.mastered },
  ] : [];

  const hasMasteryData = masteryData.some(d => d.value > 0);

  const masteredPct = overview && overview.total_flashcards > 0
    ? Math.round((overview.mastered_count / overview.total_flashcards) * 100)
    : 0;

  // ── Render ──────────────────────────────────────────
  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: SECTION_GAP }}>

      {/* ═══════════════════════════════════════════════
          SECTION 0 — HEADER
          ═══════════════════════════════════════════════ */}
      <div style={{ marginBottom: SECTION_GAP }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: '0.25rem' }}>
          🧠 Analytics
        </h1>
        <p style={{ color: 'rgba(226,232,240,0.5)', fontSize: '0.95rem', marginBottom: '1rem' }}>
          Track your study performance and identify improvement areas.
        </p>

        {/* Scope selector */}
        <select
          className="input"
          value={selectedScope}
          onChange={(e) => handleScopeChange(e.target.value)}
          style={{ maxWidth: 400 }}
        >
          {scopes.length === 0 && <option value="">No workspaces yet</option>}
          {scopes.map((s) => (
            <option key={`${s.type}-${s.id}`} value={s.id}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      {/* Error */}
      {error && (
        <div style={{
          padding: '0.75rem 1rem',
          background: 'rgba(239,68,68,0.15)',
          borderRadius: 12,
          color: '#ef4444',
          marginBottom: SECTION_GAP,
          fontSize: '0.9rem',
        }}>
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'rgba(226,232,240,0.5)' }}>
          <span style={{ fontSize: '2rem', display: 'block', marginBottom: '0.5rem' }}>⏳</span>
          Loading analytics...
        </div>
      )}

      {!loading && overview && details && (
        <>
          {/* ═══════════════════════════════════════════════
              SECTION 1 — KPI CARDS (5-card grid)
              ═══════════════════════════════════════════════ */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: '1rem',
            marginBottom: SECTION_GAP,
          }}>
            {/* KPI 1: Total Flashcards */}
            <div style={CARD_STYLE}>
              <div style={{ fontSize: '0.8rem', color: 'rgba(226,232,240,0.5)', marginBottom: '0.5rem' }}>
                Total Flashcards
              </div>
              <div style={{
                fontSize: '1.75rem',
                fontWeight: 700,
                color: masteredColor(overview.total_flashcards, overview.mastered_count),
              }}>
                {overview.total_flashcards}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'rgba(226,232,240,0.4)', marginTop: '0.25rem' }}>
                {masteredPct}% mastered
              </div>
            </div>

            {/* KPI 2: Cards Due Today */}
            <div style={CARD_STYLE}>
              <div style={{ fontSize: '0.8rem', color: 'rgba(226,232,240,0.5)', marginBottom: '0.5rem' }}>
                Cards Due Today
              </div>
              <div style={{
                fontSize: '1.75rem',
                fontWeight: 700,
                color: overview.due_today > 0 ? '#eab308' : 'rgba(226,232,240,0.7)',
              }}>
                {overview.due_today}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'rgba(226,232,240,0.4)', marginTop: '0.25rem' }}>
                {overview.due_today === 0 ? 'All caught up!' : 'cards to review'}
              </div>
            </div>

            {/* KPI 3: Average Exam Score */}
            <div style={CARD_STYLE}>
              <div style={{ fontSize: '0.8rem', color: 'rgba(226,232,240,0.5)', marginBottom: '0.5rem' }}>
                Avg Exam Score
              </div>
              <div style={{
                fontSize: '1.75rem',
                fontWeight: 700,
                color: scoreColor(overview.avg_exam_score),
              }}>
                {overview.avg_exam_score !== null ? `${overview.avg_exam_score}%` : '—'}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'rgba(226,232,240,0.4)', marginTop: '0.25rem' }}>
                {overview.exam_attempts_count} attempt{overview.exam_attempts_count !== 1 ? 's' : ''} (30d)
              </div>
            </div>

            {/* KPI 4: Study Streak */}
            <div style={CARD_STYLE}>
              <div style={{ fontSize: '0.8rem', color: 'rgba(226,232,240,0.5)', marginBottom: '0.5rem' }}>
                Study Streak
              </div>
              <div style={{
                fontSize: '1.75rem',
                fontWeight: 700,
                color: overview.study_streak > 0 ? '#f97316' : 'rgba(226,232,240,0.5)',
              }}>
                {overview.study_streak > 0 ? `🔥 ${overview.study_streak}` : '0'}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'rgba(226,232,240,0.4)', marginTop: '0.25rem' }}>
                consecutive day{overview.study_streak !== 1 ? 's' : ''}
              </div>
            </div>

            {/* KPI 5: Total Exam Attempts */}
            <div style={CARD_STYLE}>
              <div style={{ fontSize: '0.8rem', color: 'rgba(226,232,240,0.5)', marginBottom: '0.5rem' }}>
                Total Exam Attempts
              </div>
              <div style={{
                fontSize: '1.75rem',
                fontWeight: 700,
                color: 'rgba(226,232,240,0.7)',
              }}>
                {overview.exam_attempts_count}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'rgba(226,232,240,0.4)', marginTop: '0.25rem' }}>
                last 30 days
              </div>
            </div>
          </div>

          {/* ═══════════════════════════════════════════════
              SECTION 2+3 — TWO-COLUMN (Flashcards | Exams)
              ═══════════════════════════════════════════════ */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
            gap: '1.5rem',
            marginBottom: SECTION_GAP,
          }}>
            {/* LEFT: Flashcards Performance */}
            <div style={CARD_STYLE}>
              <h2 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1.25rem' }}>
                🃏 Flashcards Performance
              </h2>

              {/* Mastery Donut */}
              {hasMasteryData ? (
                <div style={{ marginBottom: '1.5rem' }}>
                  <div style={{ fontSize: '0.85rem', color: 'rgba(226,232,240,0.5)', marginBottom: '0.5rem' }}>
                    Mastery Distribution
                  </div>
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie
                        data={masteryData}
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={80}
                        paddingAngle={3}
                        dataKey="value"
                        stroke="none"
                      >
                        {masteryData.map((entry, idx) => (
                          <Cell key={idx} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          background: 'rgba(15,23,42,0.95)',
                          border: '1px solid rgba(99,102,241,0.2)',
                          borderRadius: 8,
                          fontSize: '0.8rem',
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                  {/* Legend */}
                  <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', marginTop: '0.5rem' }}>
                    {masteryData.map((d) => (
                      <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem' }}>
                        <span style={{
                          width: 10, height: 10, borderRadius: '50%',
                          background: d.color, display: 'inline-block',
                        }} />
                        <span style={{ color: 'rgba(226,232,240,0.6)' }}>{d.name}: {d.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <EmptyState message="No flashcards yet." />
              )}
            </div>

            {/* RIGHT: Exam Performance */}
            <div style={CARD_STYLE}>
              <h2 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1.25rem' }}>
                📝 Exam Performance
              </h2>

              {/* Score Trend */}
              {details.score_trend.length > 1 ? (
                <div style={{ marginBottom: '1.5rem' }}>
                  <div style={{ fontSize: '0.85rem', color: 'rgba(226,232,240,0.5)', marginBottom: '0.5rem' }}>
                    Score Trend (Last 30 Days)
                  </div>
                  <ResponsiveContainer width="100%" height={180}>
                    <LineChart data={details.score_trend}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(99,102,241,0.1)" />
                      <XAxis
                        dataKey="date"
                        tick={{ fontSize: 10, fill: 'rgba(226,232,240,0.4)' }}
                        tickFormatter={(v: string) => v.slice(5)}
                        stroke="rgba(99,102,241,0.1)"
                      />
                      <YAxis
                        domain={[0, 100]}
                        tick={{ fontSize: 10, fill: 'rgba(226,232,240,0.4)' }}
                        stroke="rgba(99,102,241,0.1)"
                      />
                      <Tooltip
                        contentStyle={{
                          background: 'rgba(15,23,42,0.95)',
                          border: '1px solid rgba(99,102,241,0.2)',
                          borderRadius: 8,
                          fontSize: '0.8rem',
                        }}
                        formatter={(value: number | undefined) => [`${value ?? 0}%`, 'Avg Score']}
                      />
                      <Line
                        type="monotone"
                        dataKey="avg_score"
                        stroke="#6366f1"
                        strokeWidth={2}
                        dot={{ fill: '#6366f1', r: 3 }}
                        activeDot={{ r: 5 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : details.score_trend.length === 1 ? (
                <div style={{
                  padding: '1rem',
                  background: 'rgba(99,102,241,0.08)',
                  borderRadius: 10,
                  fontSize: '0.85rem',
                  color: 'rgba(226,232,240,0.5)',
                  textAlign: 'center',
                  marginBottom: '1.5rem',
                }}>
                  Complete more exams to see trends.
                </div>
              ) : (
                <EmptyState message="No exam data yet." />
              )}

              {/* Weak Topics */}
              {details.weak_topics.length > 0 ? (
                <div>
                  <div style={{ fontSize: '0.85rem', color: 'rgba(226,232,240,0.5)', marginBottom: '0.5rem' }}>
                    Weak Topics (Most Incorrect)
                  </div>
                  <ResponsiveContainer width="100%" height={Math.max(120, details.weak_topics.length * 32)}>
                    <BarChart
                      data={details.weak_topics}
                      layout="vertical"
                      margin={{ left: 10, right: 20, top: 0, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(99,102,241,0.1)" />
                      <XAxis
                        type="number"
                        tick={{ fontSize: 10, fill: 'rgba(226,232,240,0.4)' }}
                        stroke="rgba(99,102,241,0.1)"
                      />
                      <YAxis
                        type="category"
                        dataKey="topic"
                        tick={{ fontSize: 10, fill: 'rgba(226,232,240,0.5)' }}
                        width={100}
                        stroke="rgba(99,102,241,0.1)"
                      />
                      <Tooltip
                        contentStyle={{
                          background: 'rgba(15,23,42,0.95)',
                          border: '1px solid rgba(99,102,241,0.2)',
                          borderRadius: 8,
                          fontSize: '0.8rem',
                        }}
                        formatter={(value: number | undefined) => [`${value ?? 0} incorrect`, 'Errors']}
                      />
                      <Bar dataKey="incorrect_count" fill="#ef4444" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <EmptyState message="No weak topics detected yet." />
              )}
            </div>
          </div>

          {/* ═══════════════════════════════════════════════
              SECTION 4 — STUDY ACTIVITY (Full Width)
              ═══════════════════════════════════════════════ */}
          <div style={{ ...CARD_STYLE, marginBottom: SECTION_GAP }}>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1.25rem' }}>
              📅 Study Activity (Last 30 Days)
            </h2>

            {details.study_activity.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={details.study_activity}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(99,102,241,0.1)" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 10, fill: 'rgba(226,232,240,0.4)' }}
                    tickFormatter={(v: string) => v.slice(5)}
                    stroke="rgba(99,102,241,0.1)"
                  />
                  <YAxis
                    tick={{ fontSize: 10, fill: 'rgba(226,232,240,0.4)' }}
                    stroke="rgba(99,102,241,0.1)"
                    allowDecimals={false}
                  />
                  <Tooltip
                    contentStyle={{
                      background: 'rgba(15,23,42,0.95)',
                      border: '1px solid rgba(99,102,241,0.2)',
                      borderRadius: 8,
                      fontSize: '0.8rem',
                    }}
                    formatter={(value: number | undefined) => [`${value ?? 0} actions`, 'Activity']}
                  />
                  <Bar dataKey="actions" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState message="No study activity recorded yet." />
            )}
          </div>

          {/* ═══════════════════════════════════════════════
              SECTION 5 — RECOMMENDATIONS PANEL (Full Width)
              ═══════════════════════════════════════════════ */}
          <div style={CARD_STYLE}>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1rem' }}>
              🎯 Recommended Focus
            </h2>

            {overview.recommendations.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {overview.recommendations.map((rec, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: '0.75rem 1rem',
                      background: 'rgba(99,102,241,0.06)',
                      border: '1px solid rgba(99,102,241,0.12)',
                      borderRadius: 10,
                      fontSize: '0.9rem',
                      color: 'rgba(226,232,240,0.75)',
                      lineHeight: 1.5,
                    }}
                  >
                    {rec}
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState message="No recommendations available yet." />
            )}
          </div>
        </>
      )}

      {/* Empty state when no data at all */}
      {!loading && !overview && !error && (
        <div style={{
          textAlign: 'center',
          padding: '4rem 2rem',
          color: 'rgba(226,232,240,0.4)',
        }}>
          <span style={{ fontSize: '3rem', display: 'block', marginBottom: '1rem' }}>📊</span>
          <p style={{ fontSize: '1.1rem' }}>Select a scope to view your analytics.</p>
        </div>
      )}
    </div>
  );
}
