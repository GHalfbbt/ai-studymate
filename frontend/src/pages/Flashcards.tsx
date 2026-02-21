/**
 * Flashcards page — Generate and review flashcards with spaced repetition pools.
 *
 * Features:
 * - Generate flashcards from study materials with count selector
 * - Flip card interaction (front/back)
 * - Spaced repetition with pool system:
 *   - Pool 1 (New/Failed): Cards not yet learned or answered incorrectly
 *   - Pool 2 (Learning): Cards answered correctly once
 *   - Pool 3 (Mastered): Cards answered correctly multiple times
 * - Export to Anki-compatible format (TSV with tags)
 * - Clear old cards before generating new ones
 */

import { useState, useEffect } from 'react';
import { listWorkspaces, listCourses, listSubjects } from '../api/workspaces';
import {
  generateFlashcards,
  listFlashcards,
  reviewFlashcard,
  exportFlashcardsCSV,
  deleteAllFlashcards,
  type Flashcard,
} from '../api/flashcards';

interface ScopeOption {
  id: string;
  name: string;
  label: string;
  type: 'subject' | 'course' | 'workspace';
}

// Pool classification based on review history
type Pool = 'new' | 'learning' | 'mastered';

function getCardPool(card: Flashcard): Pool {
  if (card.times_reviewed === 0) return 'new';
  if (card.ease_factor >= 2.5 && card.times_reviewed >= 3) return 'mastered';
  if (card.times_reviewed >= 1 && card.ease_factor >= 2.0) return 'learning';
  return 'new'; // Failed cards reset to new pool
}

const POOL_CONFIG = {
  new: { label: '🔴 New / Failed', color: '#ef4444', bg: 'rgba(239,68,68,0.15)' },
  learning: { label: '🟡 Learning', color: '#eab308', bg: 'rgba(234,179,8,0.15)' },
  mastered: { label: '🟢 Mastered', color: '#22c55e', bg: 'rgba(34,197,94,0.15)' },
};

export default function Flashcards() {
  // Scope selection
  const [scopes, setScopes] = useState<ScopeOption[]>([]);
  const [selectedScope, setSelectedScope] = useState('');
  const [selectedType, setSelectedType] = useState<'subject' | 'course' | 'workspace'>('subject');

  // Flashcards data
  const [cards, setCards] = useState<Flashcard[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);

  // Generation
  const [genCount, setGenCount] = useState(10);
  const [clearBeforeGenerate, setClearBeforeGenerate] = useState(false);

  // Review pool filter
  const [reviewPool, setReviewPool] = useState<Pool | 'all'>('all');

  // UI
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [mode, setMode] = useState<'list' | 'review'>('list');
  const [lastAnswer, setLastAnswer] = useState<'correct' | 'incorrect' | null>(null);

  useEffect(() => {
    loadScopes();
  }, []);

  async function loadScopes() {
    try {
      const wsList = await listWorkspaces();
      const opts: ScopeOption[] = [];
      for (const ws of wsList) {
        opts.push({ id: ws.id, name: ws.name, label: `🗂️ ${ws.name} (all docs)`, type: 'workspace' });
        const courses = await listCourses(ws.id);
        for (const course of courses) {
          opts.push({ id: course.id, name: course.name, label: `  📖 ${course.name} (all docs)`, type: 'course' });
          const subjectList = await listSubjects(ws.id, course.id);
          for (const subject of subjectList) {
            opts.push({ id: subject.id, name: subject.name, label: `    📝 ${course.name} → ${subject.name}`, type: 'subject' });
          }
        }
      }
      setScopes(opts);
      if (opts.length > 0) {
        setSelectedScope(opts[0].id);
        setSelectedType(opts[0].type);
        if (opts[0].type === 'subject') loadCards(opts[0].id);
      }
    } catch {
      console.error('Failed to load scopes');
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
    if (!selectedScope) return;
    setLoading(true);
    setError('');
    try {
      // Clear old cards if option is selected
      if (clearBeforeGenerate && selectedType === 'subject') {
        await deleteAllFlashcards(selectedScope);
      }

      const scope = scopes.find(s => s.id === selectedScope);
      const req: any = { count: genCount };
      if (scope?.type === 'subject') req.subject_id = selectedScope;
      else if (scope?.type === 'course') req.course_id = selectedScope;
      else if (scope?.type === 'workspace') req.workspace_id = selectedScope;

      const newCards = await generateFlashcards(req);

      if (clearBeforeGenerate) {
        setCards(newCards);
      } else {
        setCards((prev) => [...newCards, ...prev]);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate flashcards');
    } finally {
      setLoading(false);
    }
  }

  // Get cards filtered by pool for review
  function getReviewCards(): Flashcard[] {
    if (reviewPool === 'all') return cards;
    return cards.filter(c => getCardPool(c) === reviewPool);
  }

  async function handleReview(quality: number) {
    const reviewCards = getReviewCards();
    const card = reviewCards[currentIndex];
    if (!card) return;

    // Show visual feedback
    setLastAnswer(quality >= 3 ? 'correct' : 'incorrect');

    try {
      const updated = await reviewFlashcard(card.id, quality);
      // Update the card in our local state
      setCards(prev => prev.map(c => c.id === updated.id ? updated : c));
    } catch {
      // Continue even if review save fails
    }

    // Brief delay for visual feedback, then move to next card
    setTimeout(() => {
      setLastAnswer(null);
      const reviewCardsNow = getReviewCards();
      if (currentIndex < reviewCardsNow.length - 1) {
        setCurrentIndex(currentIndex + 1);
        setFlipped(false);
      } else {
        // All cards reviewed
        setMode('list');
        setCurrentIndex(0);
        setFlipped(false);
        if (selectedType === 'subject') loadCards(selectedScope);
      }
    }, 600);
  }

  async function handleExport() {
    if (!selectedScope || selectedType !== 'subject') return;
    try {
      const csv = await exportFlashcardsCSV(selectedScope);
      // Build Anki-compatible TSV with header
      const ankiHeader = '#separator:tab\n#html:true\n#tags column:3\n';
      const ankiContent = cards.map(c => {
        const front = c.front.replace(/\t/g, ' ').replace(/\n/g, '<br>');
        const back = c.back.replace(/\t/g, ' ').replace(/\n/g, '<br>');
        const tag = `difficulty::${c.difficulty} pool::${getCardPool(c)}`;
        return `${front}\t${back}\t${tag}`;
      }).join('\n');

      const blob = new Blob([ankiHeader + ankiContent], { type: 'text/tab-separated-values' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'flashcards_anki.txt';
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError('Failed to export flashcards');
    }
  }

  function startReview(pool: Pool | 'all' = 'all') {
    setReviewPool(pool);
    setCurrentIndex(0);
    setFlipped(false);
    setLastAnswer(null);
    setMode('review');
  }

  // Pool statistics
  const poolStats = {
    new: cards.filter(c => getCardPool(c) === 'new').length,
    learning: cards.filter(c => getCardPool(c) === 'learning').length,
    mastered: cards.filter(c => getCardPool(c) === 'mastered').length,
  };

  // ── REVIEW MODE ──
  if (mode === 'review') {
    const reviewCards = getReviewCards();
    if (reviewCards.length === 0) {
      return (
        <div style={{ padding: '2rem', maxWidth: 600, margin: '0 auto', textAlign: 'center' }}>
          <p style={{ fontSize: '1.1rem', opacity: 0.7, marginBottom: '1rem' }}>
            No cards in this pool to review!
          </p>
          <button className="btn btn-primary" onClick={() => setMode('list')}>
            ← Back to Cards
          </button>
        </div>
      );
    }

    const card = reviewCards[currentIndex];
    const progress = ((currentIndex + 1) / reviewCards.length) * 100;
    const cardPool = getCardPool(card);

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
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{
              fontSize: '0.75rem',
              padding: '0.15rem 0.5rem',
              borderRadius: 8,
              background: POOL_CONFIG[cardPool].bg,
              color: POOL_CONFIG[cardPool].color,
            }}>
              {POOL_CONFIG[cardPool].label}
            </span>
            <span style={{ fontSize: '0.85rem', opacity: 0.7 }}>
              {currentIndex + 1} / {reviewCards.length}
            </span>
          </div>
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
            background: lastAnswer === 'correct'
              ? 'rgba(34,197,94,0.2)'
              : lastAnswer === 'incorrect'
                ? 'rgba(239,68,68,0.2)'
                : flipped
                  ? 'rgba(99,102,241,0.15)'
                  : 'rgba(255,255,255,0.05)',
            border: lastAnswer === 'correct'
              ? '2px solid rgba(34,197,94,0.5)'
              : lastAnswer === 'incorrect'
                ? '2px solid rgba(239,68,68,0.5)'
                : '2px solid rgba(255,255,255,0.1)',
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
          <div style={{ position: 'absolute', bottom: '1rem', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <span style={{
              fontSize: '0.7rem',
              padding: '0.15rem 0.4rem',
              borderRadius: 8,
              background: card.difficulty === 'easy' ? 'rgba(34,197,94,0.2)' : card.difficulty === 'hard' ? 'rgba(239,68,68,0.2)' : 'rgba(234,179,8,0.2)',
              color: card.difficulty === 'easy' ? '#22c55e' : card.difficulty === 'hard' ? '#ef4444' : '#eab308',
            }}>
              {card.difficulty}
            </span>
            <span style={{ fontSize: '0.7rem', opacity: 0.4 }}>
              Reviews: {card.times_reviewed}
            </span>
          </div>
        </div>

        {/* Review buttons (only show when flipped) */}
        {flipped && !lastAnswer && (
          <div style={{ marginTop: '1.5rem' }}>
            <p style={{ textAlign: 'center', fontSize: '0.85rem', opacity: 0.7, marginBottom: '0.75rem' }}>
              Did you know the answer?
            </p>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button
                onClick={() => handleReview(1)}
                style={{
                  flex: 1,
                  padding: '0.75rem',
                  borderRadius: 12,
                  border: 'none',
                  background: 'rgba(239,68,68,0.15)',
                  color: '#ef4444',
                  cursor: 'pointer',
                  fontWeight: 700,
                  fontSize: '0.9rem',
                }}
              >
                ❌ Incorrect
              </button>
              <button
                onClick={() => handleReview(4)}
                style={{
                  flex: 1,
                  padding: '0.75rem',
                  borderRadius: 12,
                  border: 'none',
                  background: 'rgba(34,197,94,0.15)',
                  color: '#22c55e',
                  cursor: 'pointer',
                  fontWeight: 700,
                  fontSize: '0.9rem',
                }}
              >
                ✅ Correct
              </button>
            </div>
          </div>
        )}

        {/* Visual feedback */}
        {lastAnswer && (
          <div style={{
            marginTop: '1.5rem',
            textAlign: 'center',
            fontSize: '1.2rem',
            fontWeight: 700,
            color: lastAnswer === 'correct' ? '#22c55e' : '#ef4444',
          }}>
            {lastAnswer === 'correct' ? '✅ Correct! Moving to next pool...' : '❌ Incorrect. Card stays in review pool.'}
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

      {/* Scope selector + generate */}
      <div className="card" style={{ padding: '1.25rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <label style={{ flex: 2 }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, display: 'block', marginBottom: '0.25rem' }}>Source</span>
            <select
              className="input"
              value={selectedScope}
              onChange={(e) => {
                const scope = scopes.find(s => s.id === e.target.value);
                setSelectedScope(e.target.value);
                setSelectedType(scope?.type || 'subject');
                if (scope?.type === 'subject') loadCards(e.target.value);
                else setCards([]);
              }}
            >
              {scopes.map((s) => (
                <option key={`${s.type}-${s.id}`} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
          <label style={{ flex: 1 }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, display: 'block', marginBottom: '0.25rem' }}>Count: {genCount}</span>
            <input type="range" min={5} max={50} value={genCount} onChange={(e) => setGenCount(Number(e.target.value))} style={{ width: '100%' }} />
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
        {/* Clear before generate option */}
        <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <input
            type="checkbox"
            id="clearBeforeGen"
            checked={clearBeforeGenerate}
            onChange={(e) => setClearBeforeGenerate(e.target.checked)}
            style={{ accentColor: '#6366f1' }}
          />
          <label htmlFor="clearBeforeGen" style={{ fontSize: '0.8rem', opacity: 0.7, cursor: 'pointer' }}>
            Clear existing cards before generating new ones
          </label>
        </div>
      </div>

      {/* Pool statistics */}
      {cards.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem', marginBottom: '1.5rem' }}>
          {(['new', 'learning', 'mastered'] as Pool[]).map((pool) => (
            <div
              key={pool}
              className="card"
              onClick={() => poolStats[pool] > 0 ? startReview(pool) : undefined}
              style={{
                padding: '1rem',
                textAlign: 'center',
                cursor: poolStats[pool] > 0 ? 'pointer' : 'default',
                opacity: poolStats[pool] > 0 ? 1 : 0.5,
                borderColor: POOL_CONFIG[pool].color + '33',
              }}
            >
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: POOL_CONFIG[pool].color }}>
                {poolStats[pool]}
              </div>
              <div style={{ fontSize: '0.8rem', opacity: 0.8 }}>{POOL_CONFIG[pool].label}</div>
              {poolStats[pool] > 0 && (
                <div style={{ fontSize: '0.7rem', opacity: 0.5, marginTop: '0.25rem' }}>Click to review</div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Actions bar */}
      {cards.length > 0 && (
        <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem' }}>
          <button className="btn btn-primary" onClick={() => startReview('all')} style={{ flex: 1 }}>
            🎯 Review All {cards.length} Cards
          </button>
          <button
            className="btn"
            onClick={handleExport}
            style={{ background: 'rgba(255,255,255,0.1)' }}
            title="Export as Anki-compatible file with tags"
          >
            📥 Export Anki
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
          {cards.map((card) => {
            const pool = getCardPool(card);
            return (
              <div key={card.id} className="card" style={{ padding: '1rem', borderLeft: `3px solid ${POOL_CONFIG[pool].color}` }}>
                <p style={{ fontWeight: 600, marginBottom: '0.5rem', fontSize: '0.95rem' }}>
                  ❓ {card.front}
                </p>
                <p style={{ fontSize: '0.85rem', opacity: 0.7, lineHeight: 1.5 }}>
                  📖 {card.back}
                </p>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.75rem', fontSize: '0.75rem', opacity: 0.5 }}>
                  <span style={{
                    padding: '0.1rem 0.4rem',
                    borderRadius: 8,
                    background: POOL_CONFIG[pool].bg,
                    color: POOL_CONFIG[pool].color,
                  }}>
                    {POOL_CONFIG[pool].label}
                  </span>
                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
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
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
