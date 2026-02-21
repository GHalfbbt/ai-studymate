/**
 * Exams page — Generate, take, and review exams.
 *
 * Three views in one page:
 * 1. Generate: Select subject, configure, and generate exam
 * 2. Take: Answer questions with timer
 * 3. Results: View score and feedback
 */

import { useState, useEffect } from 'react';
import { listWorkspaces, listCourses, listSubjects } from '../api/workspaces';
import {
  generateExam,
  listExams,
  submitExam,
  type Exam,
  type ExamQuestion,
  type ExamResult,
  type SubmitAnswer,
} from '../api/exams';

type View = 'list' | 'generate' | 'take' | 'results';

interface ScopeOption {
  id: string;
  name: string;
  label: string;
  type: 'subject' | 'course' | 'workspace';
  courseId?: string;
  workspaceId?: string;
}

export default function Exams() {
  // View state
  const [view, setView] = useState<View>('list');

  // Scope selection (subject, course, or workspace)
  const [scopes, setScopes] = useState<ScopeOption[]>([]);
  const [selectedScope, setSelectedScope] = useState('');
  const [selectedType, setSelectedType] = useState<'subject' | 'course' | 'workspace'>('subject');

  // Exam list
  const [exams, setExams] = useState<Exam[]>([]);

  // Generation config
  const [mcCount, setMcCount] = useState(5);
  const [shortCount, setShortCount] = useState(2);
  const [difficulty, setDifficulty] = useState<'easy' | 'medium' | 'hard'>('medium');
  const [numOptions, setNumOptions] = useState<3 | 4>(4);
  const [customTitle, setCustomTitle] = useState('');

  // Current exam (taking)
  const [currentExam, setCurrentExam] = useState<Exam | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [timeElapsed, setTimeElapsed] = useState(0);

  // Results
  const [result, setResult] = useState<ExamResult | null>(null);

  // UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Load scopes on mount
  useEffect(() => {
    loadScopes();
  }, []);

  // Timer for exam taking
  useEffect(() => {
    if (view !== 'take') return;
    const timer = setInterval(() => setTimeElapsed((t) => t + 1), 1000);
    return () => clearInterval(timer);
  }, [view]);

  async function loadScopes() {
    try {
      const wsList = await listWorkspaces();
      const opts: ScopeOption[] = [];
      for (const ws of wsList) {
        // Add workspace-level option
        opts.push({
          id: ws.id, name: ws.name,
          label: `🗂️ ${ws.name} (all docs)`,
          type: 'workspace', workspaceId: ws.id,
        });
        const courses = await listCourses(ws.id);
        for (const course of courses) {
          // Add course-level option
          opts.push({
            id: course.id, name: course.name,
            label: `  📖 ${course.name} (all docs)`,
            type: 'course', courseId: course.id, workspaceId: ws.id,
          });
          const subjects = await listSubjects(ws.id, course.id);
          for (const subject of subjects) {
            opts.push({
              id: subject.id, name: subject.name,
              label: `    📝 ${course.name} → ${subject.name}`,
              type: 'subject', courseId: course.id, workspaceId: ws.id,
            });
          }
        }
      }
      setScopes(opts);
      if (opts.length > 0) {
        setSelectedScope(opts[0].id);
        setSelectedType(opts[0].type);
        if (opts[0].type === 'subject') loadExams(opts[0].id);
      }
    } catch {
      console.error('Failed to load scopes');
    }
  }

  async function loadExams(subjectId: string) {
    try {
      const list = await listExams(subjectId);
      setExams(list);
    } catch {
      setExams([]);
    }
  }

  async function handleGenerate() {
    if (!selectedScope) return;
    setLoading(true);
    setError('');
    try {
      const scope = scopes.find(s => s.id === selectedScope);
      const req: any = {
        mc_count: mcCount,
        short_answer_count: shortCount,
        difficulty,
        num_options: numOptions,
        title: customTitle || undefined,
      };
      if (scope?.type === 'subject') req.subject_id = selectedScope;
      else if (scope?.type === 'course') req.course_id = selectedScope;
      else if (scope?.type === 'workspace') req.workspace_id = selectedScope;

      const exam = await generateExam(req);
      setCurrentExam(exam);
      setAnswers({});
      setTimeElapsed(0);
      setView('take');
      if (selectedType === 'subject') loadExams(selectedScope);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate exam');
    } finally {
      setLoading(false);
    }
  }

  function startExam(exam: Exam) {
    setCurrentExam(exam);
    setAnswers({});
    setTimeElapsed(0);
    setView('take');
  }

  async function handleSubmit() {
    if (!currentExam) return;
    setLoading(true);
    setError('');
    try {
      const submitAnswers: SubmitAnswer[] = currentExam.questions.map((q) => ({
        question_id: q.id,
        user_answer: answers[q.id] || '',
      }));
      const res = await submitExam(currentExam.id, submitAnswers);
      setResult(res);
      setView('results');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit exam');
    } finally {
      setLoading(false);
    }
  }

  function formatTime(seconds: number) {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }

  // ── LIST VIEW ──
  if (view === 'list') {
    return (
      <div style={{ padding: '2rem', maxWidth: 900, margin: '0 auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>📝 Exams</h1>
          <button
            className="btn btn-primary"
            onClick={() => setView('generate')}
          >
            + Generate Exam
          </button>
        </div>

        {/* Scope filter */}
        <select
          className="input"
          value={selectedScope}
          onChange={(e) => {
            const scope = scopes.find(s => s.id === e.target.value);
            setSelectedScope(e.target.value);
            setSelectedType(scope?.type || 'subject');
            if (scope?.type === 'subject') loadExams(e.target.value);
            else setExams([]);
          }}
          style={{ marginBottom: '1rem', maxWidth: 400 }}
        >
          {scopes.map((s) => (
            <option key={`${s.type}-${s.id}`} value={s.id}>
              {s.label}
            </option>
          ))}
        </select>

        {exams.length === 0 ? (
          <div className="card" style={{ padding: '2rem', textAlign: 'center', opacity: 0.7 }}>
            No exams yet. Generate one to get started!
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {exams.map((exam) => (
              <div key={exam.id} className="card" style={{ padding: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h3 style={{ fontWeight: 600 }}>{exam.title}</h3>
                  <p style={{ fontSize: '0.85rem', opacity: 0.7 }}>
                    {exam.mc_count} MC + {exam.short_answer_count} short answer · {new Date(exam.created_at).toLocaleDateString()}
                  </p>
                </div>
                <button className="btn btn-primary" onClick={() => startExam(exam)}>
                  Take Exam →
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // ── GENERATE VIEW ──
  if (view === 'generate') {
    return (
      <div style={{ padding: '2rem', maxWidth: 600, margin: '0 auto' }}>
        <button onClick={() => setView('list')} style={{ marginBottom: '1rem', opacity: 0.7, background: 'none', border: 'none', color: 'inherit', cursor: 'pointer' }}>
          ← Back to exams
        </button>

        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '1.5rem' }}>🎯 Generate Exam</h1>

        {error && (
          <div style={{ padding: '0.75rem', background: 'rgba(239,68,68,0.15)', borderRadius: 8, marginBottom: '1rem', color: '#ef4444' }}>
            {error}
          </div>
        )}

        <div className="card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* Scope */}
          <label>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, display: 'block', marginBottom: '0.25rem' }}>Source</span>
            <select className="input" value={selectedScope} onChange={(e) => {
              const scope = scopes.find(s => s.id === e.target.value);
              setSelectedScope(e.target.value);
              setSelectedType(scope?.type || 'subject');
            }}>
              {scopes.map((s) => (
                <option key={`${s.type}-${s.id}`} value={s.id}>{s.label}</option>
              ))}
            </select>
          </label>

          {/* Title */}
          <label>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, display: 'block', marginBottom: '0.25rem' }}>Custom Title (optional)</span>
            <input className="input" value={customTitle} onChange={(e) => setCustomTitle(e.target.value)} placeholder="Auto-generated if empty" />
          </label>

          {/* MC count */}
          <label>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, display: 'block', marginBottom: '0.25rem' }}>Multiple Choice Questions: {mcCount}</span>
            <input type="range" min={0} max={20} value={mcCount} onChange={(e) => setMcCount(Number(e.target.value))} style={{ width: '100%' }} />
          </label>

          {/* Short answer count */}
          <label>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, display: 'block', marginBottom: '0.25rem' }}>Short Answer Questions: {shortCount}</span>
            <input type="range" min={0} max={10} value={shortCount} onChange={(e) => setShortCount(Number(e.target.value))} style={{ width: '100%' }} />
          </label>

          {/* Number of options per MC question */}
          {mcCount > 0 && (
            <label>
              <span style={{ fontSize: '0.85rem', fontWeight: 600, display: 'block', marginBottom: '0.25rem' }}>Options per MC Question</span>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                {([3, 4] as const).map((n) => (
                  <button
                    key={n}
                    onClick={() => setNumOptions(n)}
                    style={{
                      flex: 1,
                      padding: '0.5rem',
                      borderRadius: 8,
                      border: numOptions === n ? '2px solid #6366f1' : '2px solid rgba(255,255,255,0.1)',
                      background: numOptions === n ? 'rgba(99,102,241,0.2)' : 'rgba(255,255,255,0.05)',
                      color: 'inherit',
                      cursor: 'pointer',
                      fontWeight: numOptions === n ? 700 : 400,
                    }}
                  >
                    {n === 3 ? '🔤 3 options (A, B, C)' : '🔤 4 options (A, B, C, D)'}
                  </button>
                ))}
              </div>
            </label>
          )}

          {/* Difficulty */}
          <label>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, display: 'block', marginBottom: '0.25rem' }}>Difficulty</span>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              {(['easy', 'medium', 'hard'] as const).map((d) => (
                <button
                  key={d}
                  onClick={() => setDifficulty(d)}
                  style={{
                    flex: 1,
                    padding: '0.5rem',
                    borderRadius: 8,
                    border: difficulty === d ? '2px solid #6366f1' : '2px solid rgba(255,255,255,0.1)',
                    background: difficulty === d ? 'rgba(99,102,241,0.2)' : 'rgba(255,255,255,0.05)',
                    color: 'inherit',
                    cursor: 'pointer',
                    fontWeight: difficulty === d ? 700 : 400,
                    textTransform: 'capitalize',
                  }}
                >
                  {d === 'easy' ? '🟢' : d === 'medium' ? '🟡' : '🔴'} {d}
                </button>
              ))}
            </div>
          </label>

          <button
            className="btn btn-primary"
            onClick={handleGenerate}
            disabled={loading || mcCount + shortCount === 0}
            style={{ marginTop: '0.5rem', padding: '0.75rem', fontSize: '1rem' }}
          >
            {loading ? '⏳ Generating...' : `🚀 Generate ${mcCount + shortCount} Questions`}
          </button>
        </div>
      </div>
    );
  }

  // ── TAKE VIEW ──
  if (view === 'take' && currentExam) {
    const answeredCount = Object.values(answers).filter((a) => a.trim()).length;
    const totalQ = currentExam.questions.length;

    return (
      <div style={{ padding: '2rem', maxWidth: 800, margin: '0 auto' }}>
        {/* Header with timer */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', position: 'sticky', top: 0, background: 'var(--bg-primary, #0f172a)', padding: '0.5rem 0', zIndex: 10 }}>
          <div>
            <h1 style={{ fontSize: '1.25rem', fontWeight: 700 }}>{currentExam.title}</h1>
            <p style={{ fontSize: '0.85rem', opacity: 0.7 }}>{answeredCount}/{totalQ} answered</p>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '1.5rem', fontFamily: 'monospace', fontWeight: 700 }}>
              ⏱ {formatTime(timeElapsed)}
            </div>
          </div>
        </div>

        {/* Progress bar */}
        <div style={{ height: 4, background: 'rgba(255,255,255,0.1)', borderRadius: 2, marginBottom: '1.5rem' }}>
          <div style={{ height: '100%', width: `${(answeredCount / totalQ) * 100}%`, background: '#6366f1', borderRadius: 2, transition: 'width 0.3s' }} />
        </div>

        {/* Questions */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {currentExam.questions.map((q, idx) => (
            <QuestionCard
              key={q.id}
              question={q}
              index={idx}
              answer={answers[q.id] || ''}
              onAnswer={(val) => setAnswers((prev) => ({ ...prev, [q.id]: val }))}
            />
          ))}
        </div>

        {/* Submit button */}
        <div style={{ marginTop: '2rem', textAlign: 'center' }}>
          {error && (
            <div style={{ padding: '0.75rem', background: 'rgba(239,68,68,0.15)', borderRadius: 8, marginBottom: '1rem', color: '#ef4444' }}>
              {error}
            </div>
          )}
          <button
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={loading}
            style={{ padding: '0.75rem 2rem', fontSize: '1.1rem' }}
          >
            {loading ? '⏳ Evaluating...' : `✅ Submit Exam (${answeredCount}/${totalQ})`}
          </button>
        </div>
      </div>
    );
  }

  // ── RESULTS VIEW ──
  if (view === 'results' && result) {
    const scoreColor = result.score >= 70 ? '#22c55e' : result.score >= 50 ? '#eab308' : '#ef4444';

    return (
      <div style={{ padding: '2rem', maxWidth: 800, margin: '0 auto' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '1.5rem' }}>📊 Exam Results</h1>

        {/* Score summary */}
        <div className="card" style={{ padding: '2rem', textAlign: 'center', marginBottom: '2rem' }}>
          <div style={{ fontSize: '3rem', fontWeight: 700, color: scoreColor }}>
            {result.score.toFixed(1)}%
          </div>
          <p style={{ fontSize: '1.1rem', opacity: 0.8 }}>
            {result.correct_answers} / {result.total_questions} correct
          </p>
          <p style={{ fontSize: '0.85rem', opacity: 0.6, marginTop: '0.5rem' }}>
            {result.exam_title} · {formatTime(timeElapsed)}
          </p>
        </div>

        {/* Answer feedback */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {result.answers.map((a, idx) => (
            <div
              key={a.question_id}
              className="card"
              style={{
                padding: '1rem',
                borderLeft: `4px solid ${a.is_correct ? '#22c55e' : '#ef4444'}`,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <span style={{ fontWeight: 600 }}>Q{idx + 1}. {a.question_type === 'mc' ? '📋' : '✏️'}</span>
                <span style={{ fontWeight: 700, color: a.is_correct ? '#22c55e' : '#ef4444' }}>
                  {a.is_correct ? '✓ Correct' : '✗ Incorrect'}
                  {a.score !== undefined && a.question_type !== 'mc' && ` (${a.score}/10)`}
                </span>
              </div>
              <p style={{ marginBottom: '0.5rem' }}>{a.question_text}</p>
              <p style={{ fontSize: '0.9rem' }}>
                <strong>Your answer:</strong> {a.user_answer || '(no answer)'}
              </p>
              {!a.is_correct && a.correct_answer && (
                <p style={{ fontSize: '0.9rem', color: '#22c55e' }}>
                  <strong>Correct:</strong> {a.correct_answer}
                </p>
              )}
              {a.feedback && (
                <p style={{ fontSize: '0.85rem', opacity: 0.8, marginTop: '0.5rem', fontStyle: 'italic' }}>
                  💡 {a.feedback}
                </p>
              )}
              {a.explanation && (
                <p style={{ fontSize: '0.85rem', opacity: 0.7, marginTop: '0.25rem' }}>
                  📖 {a.explanation}
                </p>
              )}
            </div>
          ))}
        </div>

        {/* Actions */}
        <div style={{ marginTop: '2rem', display: 'flex', gap: '1rem', justifyContent: 'center' }}>
          <button className="btn btn-primary" onClick={() => { setView('list'); setResult(null); }}>
            Back to Exams
          </button>
          <button
            className="btn"
            style={{ background: 'rgba(255,255,255,0.1)' }}
            onClick={() => { if (currentExam) startExam(currentExam); }}
          >
            🔄 Retake
          </button>
        </div>
      </div>
    );
  }

  return null;
}

// ── Question Card Component ──
function QuestionCard({
  question,
  index,
  answer,
  onAnswer,
}: {
  question: ExamQuestion;
  index: number;
  answer: string;
  onAnswer: (val: string) => void;
}) {
  return (
    <div className="card" style={{ padding: '1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
        <span style={{ fontWeight: 600 }}>
          Question {index + 1} {question.question_type === 'mc' ? '📋' : '✏️'}
        </span>
        <span style={{
          fontSize: '0.75rem',
          padding: '0.15rem 0.5rem',
          borderRadius: 12,
          background: question.difficulty === 'easy' ? 'rgba(34,197,94,0.2)' : question.difficulty === 'hard' ? 'rgba(239,68,68,0.2)' : 'rgba(234,179,8,0.2)',
          color: question.difficulty === 'easy' ? '#22c55e' : question.difficulty === 'hard' ? '#ef4444' : '#eab308',
        }}>
          {question.difficulty}
        </span>
      </div>

      <p style={{ marginBottom: '1rem', lineHeight: 1.5 }}>{question.question_text}</p>

      {question.question_type === 'mc' && question.options ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {question.options.map((opt, i) => {
            const letter = String.fromCharCode(65 + i); // A, B, C, D
            const isSelected = answer === letter;
            return (
              <button
                key={letter}
                onClick={() => onAnswer(letter)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                  padding: '0.75rem 1rem',
                  borderRadius: 8,
                  border: isSelected ? '2px solid #6366f1' : '2px solid rgba(255,255,255,0.1)',
                  background: isSelected ? 'rgba(99,102,241,0.15)' : 'rgba(255,255,255,0.03)',
                  color: 'inherit',
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'all 0.15s',
                }}
              >
                <span style={{
                  width: 28,
                  height: 28,
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 700,
                  fontSize: '0.85rem',
                  background: isSelected ? '#6366f1' : 'rgba(255,255,255,0.1)',
                  flexShrink: 0,
                }}>
                  {letter}
                </span>
                <span>{opt}</span>
              </button>
            );
          })}
        </div>
      ) : (
        <textarea
          className="input"
          value={answer}
          onChange={(e) => onAnswer(e.target.value)}
          placeholder="Type your answer here..."
          rows={3}
          style={{ resize: 'vertical' }}
        />
      )}
    </div>
  );
}
