/**
 * Flashcards page — Generate and review flashcards with flip animation.
 *
 * Features:
 * - Generate flashcards from study materials
 * - Flip card interaction (front/back)
 * - Spaced repetition review (quality 0-5)
 * - Export to CSV (Anki compatible)
 */

import { useState, useEffect } from 'react';
import { listWorkspaces, listCourses, listSubjects } from '../api/workspaces';
import {
  generateFlashcards,
  listFlashcards,
  reviewFlashcard,
  exportFlashcardsCSV,
  type Flashcard,
} from '../api/flashcards';

interface SubjectOption {
  id: string;
  name: string;
  courseName: string;
}

export default function Flashcards() {
  // Subject selection
  const [subjects, setSubjects] = useState<SubjectOption[]>([]);
  const [selectedSubject, setSelectedSubject] = useState('');

  // Flashcards data
  const [cards, setCards] = useState<Flashcard[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);

  // Generation
  const [genCount, setGenCount] = useState(10);

  // UI
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [mode, setMode] = useState<'list' | 'review'>('list');

  useEffect(() => {
    loadSubjects();
  }, []);

  async function loadSubjects() {
    try {
      const wsList = await listWorkspaces();
      const subs: SubjectOption[] = [];
      for (const ws of wsList) {
        const courses = await listCourses(ws.id);
        for (const course of courses) {
          const subjectList = await listSubjects(ws.id, course.id);
          for (const subject of subjectList) {
            subs.push({
              id: subject.id,
              name: subject.name,
              courseName: course.name,
            });
          }
        }
      }
      setSubjects(subs);
      if (subs.length > 0) {
        setSelectedSubject(subs[0].id);
        loadCards(subs[0].id);
      }
    } catch {
      console.error('Failed to load subjects');
    }
  }

  async function loadCards(subjectId: string) {
    try {
      const res = await listFlashcards(subjectId);
      setCards(res.flashcards);
    } catch {
      setCards([]);
    }
  }

  async function handleGenerate() {
    if (!selectedSubject) return;
    setLoading(true);
    setError('');
    try {
      const newCards = await generateFlashcards({
        subject_id: selectedSubject,
        count: genCount,
      });
      setCards((prev) => [...newCards, ...prev]);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate flashcards');
    } finally {
      setLoading(false);
    }
  }

  async function handleReview(quality: number) {
    const card = cards[currentIndex];
    if (!card) return;
    try {
      await reviewFlashcard(card.id, quality);
    } catch {
      // Continue even if review save fails
    }

    // Move to next card
    if (currentIndex < cards.length - 1) {
      setCurrentIndex(currentIndex + 1);
      setFlipped(false);
    } else {
      // All cards reviewed
      setMode('list');
      setCurrentIndex(0);
      setFlipped(false);
      loadCards(selectedSubject);
    }
  }

  async function handleExport() {
    if (!selectedSubject) return;
    try {
      const csv = await exportFlashcardsCSV(selectedSubject);
      const blob = new Blob([csv], { type: 'text/tab-separated-values' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'flashcards.csv';
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError('Failed to export flashcards');
    }
  }

  function startReview() {
    setCurrentIndex(0);
    setFlipped(false);
    setMode('review');
  }

  // ── REVIEW MODE ──
  if (mode === 'review' && cards.length > 0) {
    const card = cards[currentIndex];
    const progress = ((currentIndex + 1) / cards.length) * 100;

    return (
      <div style={{ padding: '2rem', maxWidth: 600, margin: '0 auto' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <button
            onClick={() => setMode('list')}
            style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', opacity: 0.7 }}
          >
            ← Back
          </button>
          <span style={{ fontSize: '0.85rem', opacity: 0.7 }}>
            {currentIndex + 1} / {cards.length}
          </span>
        </div>

        {/* Progress bar */}
        <div style={{ height: 4, background: 'rgba(255,255,255,0.1)', borderRadius: 2, marginBottom: '2rem' }}>
          <div style={{ height: '100%', width: `${progress}%`, background: '#6366f1', borderRadius: 2, transition: 'width 0.3s' }} />
        </div>

        {/* Flashcard */}
        <div
          onClick={() => setFlipped(!flipped)}
          style={{
            minHeight: 280,
            padding: '2rem',
            borderRadius: 16,
            background: flipped ? 'rgba(99,102,241,0.15)' : 'rgba(255,255,255,0.05)',
            border: '2px solid rgba(255,255,255,0.1)',
            cursor: 'pointer',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            textAlign: 'center',
            transition: 'all 0.3s',
            position: 'relative',
          }}
        >
          <span style={{ position: 'absolute', top: '1rem', left: '1rem', fontSize: '0.75rem', opacity: 0.5 }}>
            {flipped ? '📖 Answer' : '❓ Question'} · tap to flip
          </span>
          <p style={{ fontSize: '1.15rem', lineHeight: 1.6 }}>
            {flipped ? card.back : card.front}
          </p>
          <span style={{
            position: 'absolute',
            bottom: '1rem',
            right: '1rem',
            fontSize: '0.7rem',
            padding: '0.15rem 0.4rem',
            borderRadius: 8,
            background: card.difficulty === 'easy' ? 'rgba(34,197,94,0.2)' : card.difficulty === 'hard' ? 'rgba(239,68,68,0.2)' : 'rgba(234,179,8,0.2)',
            color: card.difficulty === 'easy' ? '#22c55e' : card.difficulty === 'hard' ? '#ef4444' : '#eab308',
          }}>
            {card.difficulty}
          </span>
        </div>

        {/* Review buttons (only show when flipped) */}
        {flipped && (
          <div style={{ marginTop: '1.5rem' }}>
            <p style={{ textAlign: 'center', fontSize: '0.85rem', opacity: 0.7, marginBottom: '0.75rem' }}>
              How well did you know this?
            </p>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              {[
                { quality: 0, label: '🔴 Again', color: '#ef4444' },
                { quality: 2, label: '🟠 Hard', color: '#f97316' },
                { quality: 3, label: '🟡 Good', color: '#eab308' },
                { quality: 4, label: '🟢 Easy', color: '#22c55e' },
                { quality: 5, label: '💎 Perfect', color: '#6366f1' },
              ].map((btn) => (
                <button
                  key={btn.quality}
                  onClick={() => handleReview(btn.quality)}
                  style={{
                    flex: 1,
                    padding: '0.6rem 0.25rem',
                    borderRadius: 8,
                    border: 'none',
                    background: `${btn.color}22`,
                    color: btn.color,
                    cursor: 'pointer',
                    fontWeight: 600,
                    fontSize: '0.75rem',
                  }}
                >
                  {btn.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // ── LIST MODE ──
  return (
    <div style={{ padding: '2rem', maxWidth: 900, margin: '0 auto' }}>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '1.5rem' }}>🃏 Flashcards</h1>

      {error && (
        <div style={{ padding: '0.75rem', background: 'rgba(239,68,68,0.15)', borderRadius: 8, marginBottom: '1rem', color: '#ef4444' }}>
          {error}
        </div>
      )}

      {/* Subject selector + generate */}
      <div className="card" style={{ padding: '1.25rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <label style={{ flex: 2 }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, display: 'block', marginBottom: '0.25rem' }}>Subject</span>
            <select
              className="input"
              value={selectedSubject}
              onChange={(e) => {
                setSelectedSubject(e.target.value);
                loadCards(e.target.value);
              }}
            >
              {subjects.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.courseName} → {s.name}
                </option>
              ))}
            </select>
          </label>
          <label style={{ flex: 1 }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, display: 'block', marginBottom: '0.25rem' }}>Count: {genCount}</span>
            <input type="range" min={5} max={30} value={genCount} onChange={(e) => setGenCount(Number(e.target.value))} style={{ width: '100%' }} />
          </label>
          <button
            className="btn btn-primary"
            onClick={handleGenerate}
            disabled={loading}
            style={{ height: 42 }}
          >
            {loading ? '⏳ ...' : '✨ Generate'}
          </button>
        </div>
      </div>

      {/* Actions bar */}
      {cards.length > 0 && (
        <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem' }}>
          <button className="btn btn-primary" onClick={startReview} style={{ flex: 1 }}>
            🎯 Review {cards.length} Cards
          </button>
          <button
            className="btn"
            onClick={handleExport}
            style={{ background: 'rgba(255,255,255,0.1)' }}
          >
            📥 Export CSV
          </button>
        </div>
      )}

      {/* Card grid */}
      {cards.length === 0 ? (
        <div className="card" style={{ padding: '2rem', textAlign: 'center', opacity: 0.7 }}>
          No flashcards yet. Generate some from your study materials!
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
          {cards.map((card) => (
            <div key={card.id} className="card" style={{ padding: '1rem' }}>
              <p style={{ fontWeight: 600, marginBottom: '0.5rem', fontSize: '0.95rem' }}>
                ❓ {card.front}
              </p>
              <p style={{ fontSize: '0.85rem', opacity: 0.7, lineHeight: 1.5 }}>
                📖 {card.back}
              </p>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.75rem', fontSize: '0.75rem', opacity: 0.5 }}>
                <span>Reviews: {card.times_reviewed}</span>
                <span style={{
                  padding: '0.1rem 0.4rem',
                  borderRadius: 8,
                  background: card.difficulty === 'easy' ? 'rgba(34,197,94,0.2)' : card.difficulty === 'hard' ? 'rgba(239,68,68,0.2)' : 'rgba(234,179,8,0.2)',
                }}>
                  {card.difficulty}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
