/**
 * Flashcards page — Generate and review flashcards with spaced repetition pools.
 *
 * Features:
 * - Generate flashcards from study materials with count selector
 * - Flip card interaction (front/back)
 * - Spaced repetition with pool system
 * - Export to Anki / JSON / TXT
 * - Import from JSON with metadata display
 * - Hide packages (frontend-only)
 * - Safe error handling (no raw object rendering)
 */

import { useState, useEffect } from 'react';
import { listWorkspaces, listCourses, listSubjects } from '../api/workspaces';
import {
  generateFlashcards,
  listFlashcards,
  reviewFlashcard,
  exportFlashcardsCSV,
  deleteFlashcard,
  deleteAllFlashcards,
  exportFlashcardsJSON,
  importFlashcardsJSON,
  type Flashcard,
  type FlashcardGenerateRequest,
} from '../api/flashcards';
import { formatDateTime } from '../utils/formatters';

interface ScopeOption {
  id: string;
  name: string;
  label: string;
  type: 'subject' | 'course' | 'workspace';
}

interface ImportMeta {
  total: number;
  exported_at: string;
}

type Pool = 'new' | 'learning' | 'mastered';

function getCardPool(card: Flashcard): Pool {
  if (card.times_reviewed === 0) return 'new';
  if (card.ease_factor >= 2.5 && card.times_reviewed >= 3) return 'mastered';
  if (card.times_reviewed >= 1 && card.ease_factor >= 2.0) return 'learning';
  return 'new';
}

const POOL_CONFIG = {
  new: { label: '🔴 New / Failed', color: '#ef4444', bg: 'rgba(239,68,68,0.15)' },
  learning: { label: '🟡 Learning', color: '#eab308', bg: 'rgba(234,179,8,0.15)' },
  mastered: { label: '🟢 Mastered', color: '#22c55e', bg: 'rgba(34,197,94,0.15)' },
};

/** Safe error extraction — never renders raw objects in JSX */
function extractErrorMessage(err: unknown): string {
  if (!err) return 'Unknown error';
  if (typeof err === 'string') return err;
  if (typeof err === 'object') {
    const e = err as Record<string, unknown>;
    // Axios-style error
    const detail = (e.response as Record<string, unknown>)?.data;
    if (detail) {
      const d = detail as Record<string, unknown>;
      if (typeof d.detail === 'string') return d.detail;
      if (Array.isArray(d.detail)) {
        return d.detail.map((item: unknown) => {
          if (typeof item === 'string') return item;
          if (typeof item === 'object' && item !== null) {
            const p = item as Record<string, unknown>;
            return p.msg ? String(p.msg) : JSON.stringify(item);
          }
          return String(item);
        }).join('; ');
      }
      if (d.detail !== undefined) return JSON.stringify(d.detail);
    }
    if ('message' in e && typeof e.message === 'string') return e.message;
    try { return JSON.stringify(err); } catch { return 'Unknown error'; }
  }
  return String(err);
}

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

  // Step 4: Hide packages (frontend-only)
  const [hiddenPackageIds, setHiddenPackageIds] = useState<Set<string>>(new Set());

  // Step 5: Import metadata
  const [importMeta, setImportMeta] = useState<ImportMeta | null>(null);

  // Safe error setter
  function setSafeError(err: unknown) {
    setError(extractErrorMessage(err));
  }

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
        loadCards(opts[0].type === 'subject' ? opts[0].id : undefined);
      }
    } catch {
      console.error('Failed to load scopes');
    }
  }

  async function loadCards(subjectId?: string) {
    try {
      const res = await listFlashcards(subjectId);
      setCards(res.flashcards);
    } catch {
      setCards([]);
    }
  }

  /** Resolve a valid subject_id for import. Priority: selected > JSON > first available */
  function resolveSubjectId(jsonData?: Record<string, unknown>): string | null {
    // 1. Currently selected subject
    if (selectedType === 'subject' && selectedScope) return selectedScope;
    // 2. subject_id from imported JSON
    if (jsonData && typeof jsonData.subject_id === 'string' && jsonData.subject_id) {
      const found = scopes.find(s => s.id === jsonData.subject_id && s.type === 'subject');
      if (found) return found.id;
    }
    // 3. First available subject in scopes
    const firstSubject = scopes.find(s => s.type === 'subject');
    if (firstSubject) return firstSubject.id;
    return null;
  }

  async function handleGenerate() {
    if (!selectedScope) return;
    setLoading(true);
    setError('');
    try {
      if (clearBeforeGenerate) {
        await deleteAllFlashcards(selectedScope, selectedType);
      }
      const scope = scopes.find(s => s.id === selectedScope);
      const req: FlashcardGenerateRequest = { count: genCount };
      if (scope?.type === 'subject') req.subject_id = selectedScope;
      else if (scope?.type === 'course') req.course_id = selectedScope;
      else if (scope?.type === 'workspace') req.workspace_id = selectedScope;

      const newCards = await generateFlashcards(req);

      if (clearBeforeGenerate) {
        setCards(newCards);
      } else {
        setCards((prev) => [...newCards, ...prev]);
      }
    } catch (err: unknown) {
      setSafeError(err);
    } finally {
      setLoading(false);
    }
  }

  function getReviewCards(): Flashcard[] {
    if (reviewPool === 'all') return cards;
    return cards.filter(c => getCardPool(c) === reviewPool);
  }

  async function handleReview(quality: number) {
    const reviewCards = getReviewCards();
    const card = reviewCards[currentIndex];
    if (!card) return;

    setLastAnswer(quality >= 3 ? 'correct' : 'incorrect');

    try {
      const updated = await reviewFlashcard(card.id, quality);
      setCards(prev => prev.map(c => c.id === updated.id ? updated : c));
    } catch {
      // Continue even if review save fails
    }

    setTimeout(() => {
      setLastAnswer(null);
      if (currentIndex < reviewCards.length - 1) {
        setCurrentIndex(currentIndex + 1);
        setFlipped(false);
      } else {
        setMode('list');
        setCurrentIndex(0);
        setFlipped(false);
        if (selectedType === 'subject') loadCards(selectedScope);
      }
    }, 600);
  }

  async function handleExportAnki() {
    if (!selectedScope || selectedType !== 'subject') return;
    try {
      await exportFlashcardsCSV(selectedScope);
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
    } catch (err: unknown) {
      setSafeError(err);
    }
  }

  async function handleExportJSON() {
    if (!selectedScope || selectedType !== 'subject') {
      setError('Please select a subject to export JSON.');
      return;
    }
    try {
      const data = await exportFlashcardsJSON(selectedScope);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `flashcards_${selectedScope}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      setSafeError(err);
    }
  }

  async function handleExportTXT() {
    if (cards.length === 0) return;
    try {
      const txt = cards.map((c, i) => `${i + 1}. Q: ${c.front}\n   A: ${c.back}\n   [${c.difficulty}] Reviews: ${c.times_reviewed}`).join('\n\n');
      const blob = new Blob([txt], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'flashcards.txt';
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      setSafeError(err);
    }
  }

  async function handleImportJSON(file: File) {
    try {
      const text = await file.text();
      let data: Record<string, unknown>;
      try {
        data = JSON.parse(text);
      } catch {
        setError('Invalid JSON file. Please check the file format.');
        return;
      }

      const subjectId = resolveSubjectId(data);
      if (!subjectId) {
        setError('Please select a subject before importing flashcards.');
        return;
      }

      const imported = await importFlashcardsJSON(subjectId, data);
      setCards(prev => [...imported, ...prev]);
      setError('');

      // Store import metadata
      const meta: ImportMeta = {
        total: typeof data.total === 'number' ? data.total : imported.length,
        exported_at: typeof data.exported_at === 'string' ? data.exported_at : new Date().toISOString(),
      };
      setImportMeta(meta);
    } catch (err: unknown) {
      setSafeError(err);
    }
  }

  function startReview(pool: Pool | 'all' = 'all') {
    setReviewPool(pool);
    setCurrentIndex(0);
    setFlipped(false);
    setLastAnswer(null);
    setMode('review');
  }

  async function handleDeleteCard(cardId: string) {
    if (!confirm('Delete this flashcard permanently?')) return;
    try {
      await deleteFlashcard(cardId);
      setCards(prev => prev.filter(c => c.id !== cardId));
      setError('');
    } catch (err: unknown) {
      setSafeError(err);
    }
  }

  async function handleDeleteAll() {
    const scopeLabel = selectedType === 'subject' ? 'subject' : selectedType === 'course' ? 'course' : 'workspace';
    if (!confirm(`Delete ALL ${cards.length} flashcards for this ${scopeLabel}? This cannot be undone.`)) return;
    try {
      await deleteAllFlashcards(selectedScope, selectedType);
      setCards([]);
      setError('');
    } catch (err: unknown) {
      setSafeError(err);
    }
  }

  function handleScopeChange(newScopeId: string) {
    const scope = scopes.find(s => s.id === newScopeId);
    setSelectedScope(newScopeId);
    setSelectedType(scope?.type || 'subject');
    setHiddenPackageIds(new Set()); // Reset hidden on scope change
    setImportMeta(null);
    loadCards(scope?.type === 'subject' ? newScopeId : undefined);
  }

  // Pool statistics
  const poolStats = {
    new: cards.filter(c => getCardPool(c) === 'new').length,
    learning: cards.filter(c => getCardPool(c) === 'learning').length,
    mastered: cards.filter(c => getCardPool(c) === 'mastered').length,
  };

  // Visible cards (filtered by hidden)
  const visibleCards = cards.filter(c => !hiddenPackageIds.has(c.id));

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
            {card.times_reviewed > 0 && (
              <span style={{ fontSize: '0.7rem', opacity: 0.4 }}>
                Reviewed {card.times_reviewed}×
              </span>
            )}
          </div>
        </div>

        {/* Review buttons */}
        {flipped && !lastAnswer && (
          <div style={{ marginTop: '1.5rem' }}>
            <p style={{ textAlign: 'center', fontSize: '0.85rem', opacity: 0.7, marginBottom: '0.75rem' }}>
              Did you know the answer?
            </p>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button
                onClick={() => handleReview(1)}
                style={{
                  flex: 1, padding: '0.75rem', borderRadius: 12, border: 'none',
                  background: 'rgba(239,68,68,0.15)', color: '#ef4444',
                  cursor: 'pointer', fontWeight: 700, fontSize: '0.9rem',
                }}
              >
                ❌ Incorrect
              </button>
              <button
                onClick={() => handleReview(4)}
                style={{
                  flex: 1, padding: '0.75rem', borderRadius: 12, border: 'none',
                  background: 'rgba(34,197,94,0.15)', color: '#22c55e',
                  cursor: 'pointer', fontWeight: 700, fontSize: '0.9rem',
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
            marginTop: '1.5rem', textAlign: 'center', fontSize: '1.2rem', fontWeight: 700,
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
      {/* Title */}
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '1rem' }}>🃏 Flashcards</h1>

      {/* Step 3: Always-visible top action bar */}
      <div style={{
        display: 'flex', gap: '0.5rem', marginBottom: '1.25rem', flexWrap: 'wrap',
      }}>
        <label
          className="btn btn-secondary"
          style={{ cursor: 'pointer', borderRadius: 12 }}
          title="Import flashcards from a previously exported JSON file"
        >
          📂 Import JSON
          <input
            type="file"
            accept=".json"
            style={{ display: 'none' }}
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (file) await handleImportJSON(file);
              e.target.value = '';
            }}
          />
        </label>
        <button
          className="btn"
          onClick={handleExportJSON}
          disabled={cards.length === 0}
          style={{ background: 'rgba(255,255,255,0.08)', borderRadius: 12, border: '1px solid rgba(255,255,255,0.1)' }}
        >
          📥 Export JSON
        </button>
        <button
          className="btn"
          onClick={handleExportTXT}
          disabled={cards.length === 0}
          style={{ background: 'rgba(255,255,255,0.08)', borderRadius: 12, border: '1px solid rgba(255,255,255,0.1)' }}
        >
          📥 Export TXT
        </button>
        <button
          className="btn"
          onClick={handleExportAnki}
          disabled={cards.length === 0 || selectedType !== 'subject'}
          style={{ background: 'rgba(255,255,255,0.08)', borderRadius: 12, border: '1px solid rgba(255,255,255,0.1)' }}
          title="Download as Anki-compatible file (.txt with tags)"
        >
          📥 Export Anki
        </button>
        {/* Spacer to push delete to the right */}
        <div style={{ flex: 1 }} />
        <button
          className="btn"
          onClick={handleDeleteAll}
          disabled={cards.length === 0}
          style={{
            background: 'rgba(239,68,68,0.08)', borderRadius: 12,
            border: '1px solid rgba(239,68,68,0.2)', color: '#ef4444',
          }}
          title={`Delete all flashcards for the selected ${selectedType}`}
        >
          🗑️ Delete All
        </button>
      </div>

      {/* Error display */}
      {error && (
        <div style={{ padding: '0.75rem', background: 'rgba(239,68,68,0.15)', borderRadius: 8, marginBottom: '1rem', color: '#ef4444' }}>
          {error}
        </div>
      )}

      {/* Step 5: Import metadata banner */}
      {importMeta && (
        <div style={{
          padding: '0.75rem 1rem', background: 'rgba(99,102,241,0.1)',
          borderRadius: 10, marginBottom: '1rem', fontSize: '0.85rem',
          border: '1px solid rgba(99,102,241,0.2)', display: 'flex',
          justifyContent: 'space-between', alignItems: 'center',
        }}>
          <span>
            📦 Imported package — <strong>{importMeta.total}</strong> cards — {formatDateTime(importMeta.exported_at)}
          </span>
          <button
            onClick={() => setImportMeta(null)}
            style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', opacity: 0.5, fontSize: '1rem' }}
          >
            ×
          </button>
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
              onChange={(e) => handleScopeChange(e.target.value)}
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
                padding: '1rem', textAlign: 'center',
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

      {/* Review all button */}
      {cards.length > 0 && (
        <div style={{ marginBottom: '1.5rem' }}>
          <button className="btn btn-primary" onClick={() => startReview('all')} style={{ width: '100%' }}>
            🎯 Review All {cards.length} Cards
          </button>
        </div>
      )}

      {/* Card grid */}
      {visibleCards.length === 0 && cards.length === 0 ? (
        <div className="card" style={{ padding: '2rem', textAlign: 'center', opacity: 0.7 }}>
          No flashcards yet. Generate some from your study materials!
        </div>
      ) : visibleCards.length === 0 && cards.length > 0 ? (
        <div className="card" style={{ padding: '2rem', textAlign: 'center', opacity: 0.7 }}>
          All cards are hidden.{' '}
          <button
            onClick={() => setHiddenPackageIds(new Set())}
            style={{ background: 'none', border: 'none', color: '#6366f1', cursor: 'pointer', textDecoration: 'underline' }}
          >
            Show all
          </button>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
          {visibleCards.map((card) => {
            const pool = getCardPool(card);
            return (
              <div key={card.id} className="card" style={{ padding: '1rem', borderLeft: `3px solid ${POOL_CONFIG[pool].color}`, position: 'relative' }}>
                {/* Card action buttons: hide & delete */}
                <div style={{ position: 'absolute', top: 8, right: 8, display: 'flex', gap: 4 }}>
                  <button
                    onClick={() => setHiddenPackageIds(prev => new Set([...prev, card.id]))}
                    title="Hide this card (frontend only)"
                    style={{
                      width: 22, height: 22, borderRadius: '50%',
                      background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)',
                      color: 'rgba(255,255,255,0.4)', cursor: 'pointer',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: '0.7rem', lineHeight: 1, padding: 0,
                    }}
                  >
                    👁
                  </button>
                  <button
                    onClick={() => handleDeleteCard(card.id)}
                    title="Delete this flashcard permanently"
                    style={{
                      width: 22, height: 22, borderRadius: '50%',
                      background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)',
                      color: 'rgba(239,68,68,0.6)', cursor: 'pointer',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: '0.65rem', lineHeight: 1, padding: 0,
                    }}
                  >
                    🗑
                  </button>
                </div>

                <p style={{ fontWeight: 600, marginBottom: '0.5rem', fontSize: '0.95rem', paddingRight: '3.5rem' }}>
                  ❓ {card.front}
                </p>
                <p style={{ fontSize: '0.85rem', opacity: 0.7, lineHeight: 1.5 }}>
                  📖 {card.back}
                </p>

                {/* Step 6: Review stats */}
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.75rem', fontSize: '0.75rem', opacity: 0.5, flexWrap: 'wrap', gap: '0.25rem' }}>
                  <span style={{
                    padding: '0.1rem 0.4rem', borderRadius: 8,
                    background: POOL_CONFIG[pool].bg, color: POOL_CONFIG[pool].color,
                  }}>
                    {POOL_CONFIG[pool].label}
                  </span>
                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    {card.times_reviewed > 0 && (
                      <span style={{
                        padding: '0.1rem 0.4rem', borderRadius: 8,
                        background: 'rgba(99,102,241,0.15)', color: '#818cf8',
                      }}>
                        Reviewed {card.times_reviewed}×
                      </span>
                    )}
                    <span style={{
                      padding: '0.1rem 0.4rem', borderRadius: 8,
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
