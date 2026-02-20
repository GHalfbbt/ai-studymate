/**
 * Workspaces page — Main study hub.
 *
 * Full hierarchy explorer: Workspace → Course → Subject → Topic
 * Upload documents at any level, rename, delete, view documents.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    listWorkspaces, createWorkspace, updateWorkspace, deleteWorkspace,
    listCourses, createCourse, updateCourse, deleteCourse,
    listSubjects, createSubject, updateSubject, deleteSubject,
    listTopics, createTopic, updateTopic, deleteTopic,
} from '../api/workspaces';
import { uploadDocument, listDocuments, deleteDocument, getDocumentDownloadUrl } from '../api/documents';
import type { Workspace, Course, Subject, Topic, Document } from '../types';
import Spinner from '../components/common/Spinner';

const COLORS = ['#6366F1', '#8B5CF6', '#06B6D4', '#10B981', '#F59E0B', '#EF4444', '#EC4899', '#14B8A6'];

// Inline editable name component
function EditableName({ value, onSave, className = '' }: {
    value: string; onSave: (v: string) => void; className?: string;
}) {
    const [editing, setEditing] = useState(false);
    const [draft, setDraft] = useState(value);
    const ref = useRef<HTMLInputElement>(null);

    useEffect(() => { if (editing) ref.current?.focus(); }, [editing]);

    if (!editing) {
        return (
            <span
                className={`cursor-pointer hover:underline decoration-dotted ${className}`}
                onDoubleClick={() => { setDraft(value); setEditing(true); }}
                title="Double-click to rename"
            >
                {value}
            </span>
        );
    }
    return (
        <input
            ref={ref}
            className="bg-transparent border-b border-primary-400 outline-none text-inherit font-inherit w-full"
            value={draft}
            onChange={e => setDraft(e.target.value)}
            onBlur={() => { if (draft.trim() && draft !== value) onSave(draft.trim()); setEditing(false); }}
            onKeyDown={e => {
                if (e.key === 'Enter') { if (draft.trim() && draft !== value) onSave(draft.trim()); setEditing(false); }
                if (e.key === 'Escape') setEditing(false);
            }}
        />
    );
}

export default function Workspaces() {
    const navigate = useNavigate();

    // Hierarchy state
    const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
    const [selWs, setSelWs] = useState<Workspace | null>(null);
    const [courses, setCourses] = useState<Course[]>([]);
    const [selCourse, setSelCourse] = useState<Course | null>(null);
    const [subjects, setSubjects] = useState<Subject[]>([]);
    const [selSubject, setSelSubject] = useState<Subject | null>(null);
    const [topics, setTopics] = useState<Topic[]>([]);
    const [selTopic, setSelTopic] = useState<Topic | null>(null);

    // Documents at current level
    const [docs, setDocs] = useState<Document[]>([]);

    // UI state
    const [loading, setLoading] = useState(true);
    const [modal, setModal] = useState<null | 'workspace' | 'course' | 'subject' | 'topic'>(null);
    const [inputName, setInputName] = useState('');
    const [inputDesc, setInputDesc] = useState('');
    const [inputColor, setInputColor] = useState(COLORS[0]);
    const [saving, setSaving] = useState(false);
    const [uploading, setUploading] = useState(false);
    const fileRef = useRef<HTMLInputElement>(null);

    // ── Load workspaces ────────────────────────────────
    useEffect(() => {
        setLoading(true);
        listWorkspaces().then(list => {
            setWorkspaces(list);
            if (list.length > 0) setSelWs(list[0]);
        }).finally(() => setLoading(false));
    }, []);

    // ── Load courses when workspace changes ────────────
    useEffect(() => {
        if (!selWs) { setCourses([]); setSelCourse(null); return; }
        setCourses([]); setSelCourse(null); setSubjects([]); setSelSubject(null); setTopics([]); setSelTopic(null);
        listCourses(selWs.id).then(list => { setCourses(list); if (list.length > 0) setSelCourse(list[0]); });
    }, [selWs]);

    // ── Load subjects when course changes ──────────────
    useEffect(() => {
        if (!selWs || !selCourse) { setSubjects([]); setSelSubject(null); return; }
        setSubjects([]); setSelSubject(null); setTopics([]); setSelTopic(null);
        listSubjects(selWs.id, selCourse.id).then(list => { setSubjects(list); if (list.length > 0) setSelSubject(list[0]); });
    }, [selCourse]);

    // ── Load topics when subject changes ───────────────
    useEffect(() => {
        if (!selWs || !selCourse || !selSubject) { setTopics([]); setSelTopic(null); return; }
        setTopics([]); setSelTopic(null);
        listTopics(selWs.id, selCourse.id, selSubject.id).then(setTopics);
    }, [selSubject]);

    // ── Load documents at current level ────────────────
    const loadDocs = useCallback(() => {
        const filters: Record<string, string> = {};
        if (selTopic) filters.topic_id = selTopic.id;
        else if (selSubject) filters.subject_id = selSubject.id;
        else if (selCourse) filters.course_id = selCourse.id;
        else if (selWs) filters.workspace_id = selWs.id;
        else return;
        listDocuments(filters).then(r => setDocs(r.documents));
    }, [selWs, selCourse, selSubject, selTopic]);

    useEffect(() => { loadDocs(); }, [loadDocs]);

    // ── Upload handler ─────────────────────────────────
    const handleUpload = async (files: FileList) => {
        if (!selWs) return;
        setUploading(true);
        const target: Record<string, string> = { workspace_id: selWs.id };
        if (selCourse) target.course_id = selCourse.id;
        if (selSubject) target.subject_id = selSubject.id;
        if (selTopic) target.topic_id = selTopic.id;

        for (const file of Array.from(files)) {
            try {
                await uploadDocument(file, target);
            } catch (err) {
                console.error('Upload failed:', err);
            }
        }
        setUploading(false);
        loadDocs();
    };

    // ── Delete document ────────────────────────────────
    const handleDeleteDoc = async (docId: string) => {
        if (!confirm('Delete this document? This cannot be undone.')) return;
        await deleteDocument(docId);
        loadDocs();
    };

    // ── Create handler ─────────────────────────────────
    const openModal = (type: typeof modal) => {
        setInputName(''); setInputDesc('');
        setInputColor(COLORS[Math.floor(Math.random() * COLORS.length)]);
        setModal(type);
    };

    const handleCreate = async () => {
        if (!inputName.trim()) return;
        setSaving(true);
        try {
            if (modal === 'workspace') {
                const ws = await createWorkspace(inputName, inputDesc || undefined);
                setWorkspaces(p => [ws, ...p]); setSelWs(ws);
            } else if (modal === 'course' && selWs) {
                const c = await createCourse(selWs.id, inputName);
                setCourses(p => [...p, c]); setSelCourse(c);
            } else if (modal === 'subject' && selWs && selCourse) {
                const s = await createSubject(selWs.id, selCourse.id, inputName, inputColor);
                setSubjects(p => [...p, s]); setSelSubject(s);
            } else if (modal === 'topic' && selWs && selCourse && selSubject) {
                const t = await createTopic(selWs.id, selCourse.id, selSubject.id, inputName);
                setTopics(p => [...p, t]); setSelTopic(t);
            }
            setModal(null);
        } finally { setSaving(false); }
    };

    // ── Delete hierarchy items ─────────────────────────
    const handleDeleteWs = async (ws: Workspace) => {
        if (!confirm(`Delete workspace "${ws.name}" and ALL its contents?`)) return;
        await deleteWorkspace(ws.id);
        setWorkspaces(p => p.filter(w => w.id !== ws.id));
        if (selWs?.id === ws.id) setSelWs(null);
    };
    const handleDeleteCourse = async (c: Course) => {
        if (!selWs || !confirm(`Delete course "${c.name}" and all its subjects?`)) return;
        await deleteCourse(selWs.id, c.id);
        setCourses(p => p.filter(x => x.id !== c.id));
        if (selCourse?.id === c.id) setSelCourse(null);
    };
    const handleDeleteSubject = async (s: Subject) => {
        if (!selWs || !selCourse || !confirm(`Delete subject "${s.name}"?`)) return;
        await deleteSubject(selWs.id, selCourse.id, s.id);
        setSubjects(p => p.filter(x => x.id !== s.id));
        if (selSubject?.id === s.id) setSelSubject(null);
    };
    const handleDeleteTopic = async (t: Topic) => {
        if (!selWs || !selCourse || !selSubject || !confirm(`Delete topic "${t.name}"?`)) return;
        await deleteTopic(selWs.id, selCourse.id, selSubject.id, t.id);
        setTopics(p => p.filter(x => x.id !== t.id));
        if (selTopic?.id === t.id) setSelTopic(null);
    };

    // ── Breadcrumb for current location ────────────────
    const breadcrumb = [
        selWs?.name,
        selCourse?.name,
        selSubject?.name,
        selTopic?.name,
    ].filter(Boolean).join(' › ') || 'Select a workspace';

    if (loading) return <div className="flex items-center justify-center min-h-[60vh]"><Spinner size="lg" label="Loading..." /></div>;

    return (
        <div className="max-w-7xl mx-auto animate-fade-in space-y-4">
            {/* Header */}
            <div className="flex items-end justify-between">
                <div>
                    <h1 className="text-2xl font-bold gradient-text">📚 My Study Space</h1>
                    <p className="text-surface-200/50 text-xs mt-1">{breadcrumb}</p>
                </div>
                <button className="btn-primary text-sm" onClick={() => openModal('workspace')}>+ New Workspace</button>
            </div>

            {/* 4-column hierarchy explorer */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
                {/* Col 1: Workspaces */}
                <HierarchyColumn
                    title="🗂️ Workspaces"
                    items={workspaces}
                    selected={selWs}
                    onSelect={setSelWs}
                    onAdd={() => openModal('workspace')}
                    renderItem={(ws) => (
                        <div className="flex justify-between items-start">
                            <div className="min-w-0 flex-1">
                                <EditableName
                                    value={ws.name}
                                    className="font-medium text-sm"
                                    onSave={(name) => updateWorkspace(ws.id, { name }).then(u => setWorkspaces(p => p.map(w => w.id === u.id ? u : w)))}
                                />
                                <div className="text-xs opacity-60 text-surface-200">{ws.course_count} courses</div>
                            </div>
                            <button onClick={e => { e.stopPropagation(); handleDeleteWs(ws); }} className="text-red-400/50 hover:text-red-400 text-xs ml-1">✕</button>
                        </div>
                    )}
                />

                {/* Col 2: Courses */}
                <HierarchyColumn
                    title="📖 Courses"
                    items={courses}
                    selected={selCourse}
                    onSelect={setSelCourse}
                    onAdd={selWs ? () => openModal('course') : undefined}
                    placeholder={!selWs ? '← Select workspace' : 'No courses'}
                    renderItem={(c) => (
                        <div className="flex justify-between items-start">
                            <div className="min-w-0 flex-1">
                                <EditableName
                                    value={c.name}
                                    className="font-medium text-sm"
                                    onSave={(name) => selWs && updateCourse(selWs.id, c.id, { name }).then(u => setCourses(p => p.map(x => x.id === u.id ? u : x)))}
                                />
                                <div className="text-xs opacity-60 text-surface-200">{c.subject_count} subjects</div>
                            </div>
                            <button onClick={e => { e.stopPropagation(); handleDeleteCourse(c); }} className="text-red-400/50 hover:text-red-400 text-xs ml-1">✕</button>
                        </div>
                    )}
                />

                {/* Col 3: Subjects */}
                <HierarchyColumn
                    title="📝 Subjects"
                    items={subjects}
                    selected={selSubject}
                    onSelect={setSelSubject}
                    onAdd={selCourse ? () => openModal('subject') : undefined}
                    placeholder={!selCourse ? '← Select course' : 'No subjects'}
                    renderItem={(s) => (
                        <div className="flex justify-between items-start">
                            <div className="flex items-start gap-2 min-w-0 flex-1">
                                <div className="w-2.5 h-2.5 rounded-full mt-1.5 flex-shrink-0" style={{ backgroundColor: s.color }} />
                                <div className="min-w-0">
                                    <EditableName
                                        value={s.name}
                                        className="font-medium text-sm"
                                        onSave={(name) => selWs && selCourse && updateSubject(selWs.id, selCourse.id, s.id, { name }).then(u => setSubjects(p => p.map(x => x.id === u.id ? u : x)))}
                                    />
                                    <div className="text-xs opacity-60 text-surface-200">{s.document_count} docs · {s.topic_count || 0} topics</div>
                                </div>
                            </div>
                            <button onClick={e => { e.stopPropagation(); handleDeleteSubject(s); }} className="text-red-400/50 hover:text-red-400 text-xs ml-1">✕</button>
                        </div>
                    )}
                />

                {/* Col 4: Topics */}
                <HierarchyColumn
                    title="🏷️ Topics"
                    items={topics}
                    selected={selTopic}
                    onSelect={setSelTopic}
                    onAdd={selSubject ? () => openModal('topic') : undefined}
                    placeholder={!selSubject ? '← Select subject' : 'No topics (optional)'}
                    renderItem={(t) => (
                        <div className="flex justify-between items-start">
                            <div className="min-w-0 flex-1">
                                <EditableName
                                    value={t.name}
                                    className="font-medium text-sm"
                                    onSave={(name) => selWs && selCourse && selSubject && updateTopic(selWs.id, selCourse.id, selSubject.id, t.id, { name }).then(u => setTopics(p => p.map(x => x.id === u.id ? u : x)))}
                                />
                                <div className="text-xs opacity-60 text-surface-200">{t.document_count} docs</div>
                            </div>
                            <button onClick={e => { e.stopPropagation(); handleDeleteTopic(t); }} className="text-red-400/50 hover:text-red-400 text-xs ml-1">✕</button>
                        </div>
                    )}
                />
            </div>

            {/* Upload + Documents panel */}
            {selWs && (
                <div className="card space-y-4">
                    <div className="flex items-center justify-between">
                        <h2 className="text-lg font-semibold text-surface-50">
                            📄 Documents <span className="text-sm font-normal text-surface-200/70">({docs.length})</span>
                        </h2>
                        <div className="flex gap-2">
                            {selSubject && (
                                <button
                                    className="btn-secondary text-xs"
                                    onClick={() => navigate(`/chat?subject_id=${selSubject.id}`)}
                                >
                                    💬 Chat with these docs
                                </button>
                            )}
                            <input ref={fileRef} type="file" className="hidden" multiple accept=".pdf,.docx,.txt,.png,.jpg,.jpeg"
                                onChange={e => e.target.files && handleUpload(e.target.files)} />
                            <button
                                className="btn-primary text-xs"
                                onClick={() => fileRef.current?.click()}
                                disabled={uploading}
                            >
                                {uploading ? '⏳ Uploading...' : '📤 Upload files here'}
                            </button>
                        </div>
                    </div>

                    {docs.length === 0 ? (
                        <div className="text-center py-10 text-surface-200/30 text-sm">
                            No documents at this level. Click "Upload files here" to add study materials.
                        </div>
                    ) : (
                        <div className="space-y-2">
                            {docs.map(doc => (
                                <div key={doc.id} className="flex items-center justify-between bg-surface-900/40 rounded-lg px-4 py-3 border border-surface-700/20">
                                    <div className="flex items-center gap-3 min-w-0">
                                        <span className="text-lg">{doc.file_type === 'pdf' ? '📕' : doc.file_type === 'docx' ? '📘' : '📄'}</span>
                                        <div className="min-w-0">
                                            <a
                                                href={getDocumentDownloadUrl(doc.id)}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="text-sm font-medium text-surface-100 truncate hover:text-primary-400 hover:underline cursor-pointer block"
                                                title="Click to open document"
                                                onClick={(e) => {
                                                    e.preventDefault();
                                                    const token = localStorage.getItem('token');
                                                    const url = getDocumentDownloadUrl(doc.id);
                                                    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
                                                        .then(r => r.blob())
                                                        .then(blob => {
                                                            const blobUrl = URL.createObjectURL(blob);
                                                            window.open(blobUrl, '_blank');
                                                        });
                                                }}
                                            >{doc.filename}</a>
                                            <div className="text-xs text-surface-200/70">
                                                {doc.file_size ? `${(doc.file_size / 1024 / 1024).toFixed(1)} MB` : '—'} · {doc.chunk_count} chunks
                                            </div>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${
                                            doc.processing_status === 'completed' ? 'bg-green-500/20 text-green-400'
                                            : doc.processing_status === 'processing' ? 'bg-yellow-500/20 text-yellow-400'
                                            : doc.processing_status === 'failed' ? 'bg-red-500/20 text-red-400'
                                            : 'bg-surface-700/30 text-surface-300'
                                        }`}>
                                            {doc.processing_status}
                                        </span>
                                        <button
                                            onClick={() => handleDeleteDoc(doc.id)}
                                            className="text-red-400/40 hover:text-red-400 text-sm"
                                            title="Delete document"
                                        >
                                            🗑️
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Create modal */}
            {modal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setModal(null)}>
                    <div className="card w-full max-w-md animate-slide-up" onClick={e => e.stopPropagation()}>
                        <h2 className="text-lg font-semibold text-surface-100 mb-4">
                            {modal === 'workspace' && '🗂️ New Workspace'}
                            {modal === 'course' && '📖 New Course'}
                            {modal === 'subject' && '📝 New Subject'}
                            {modal === 'topic' && '🏷️ New Topic'}
                        </h2>
                        <div className="space-y-4">
                            <input
                                className="input w-full"
                                placeholder={`Enter ${modal} name...`}
                                value={inputName}
                                onChange={e => setInputName(e.target.value)}
                                onKeyDown={e => e.key === 'Enter' && handleCreate()}
                                autoFocus
                            />
                            {modal === 'workspace' && (
                                <input className="input w-full" placeholder="Description (optional)" value={inputDesc} onChange={e => setInputDesc(e.target.value)} />
                            )}
                            {modal === 'subject' && (
                                <div>
                                    <label className="block text-sm text-surface-200/60 mb-2">Color</label>
                                    <div className="flex gap-2 flex-wrap">
                                        {COLORS.map(c => (
                                            <button key={c} className={`w-7 h-7 rounded-full border-2 ${inputColor === c ? 'scale-125 border-white' : 'border-transparent'}`}
                                                style={{ backgroundColor: c }} onClick={() => setInputColor(c)} />
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                        <div className="flex gap-3 mt-6">
                            <button className="btn-secondary flex-1" onClick={() => setModal(null)}>Cancel</button>
                            <button className="btn-primary flex-1" onClick={handleCreate} disabled={!inputName.trim() || saving}>
                                {saving ? '⏳ Saving...' : 'Create'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

// ── Generic hierarchy column component ──────────────────
function HierarchyColumn<T extends { id: string }>({
    title, items, selected, onSelect, onAdd, placeholder, renderItem,
}: {
    title: string;
    items: T[];
    selected: T | null;
    onSelect: (item: T) => void;
    onAdd?: () => void;
    placeholder?: string;
    renderItem: (item: T) => React.ReactNode;
}) {
    return (
        <div className="space-y-1.5">
            <div className="flex items-center justify-between mb-2">
                <h3 className="text-xs font-bold uppercase tracking-widest text-surface-200/80">{title}</h3>
                {onAdd && <button className="text-[11px] text-primary-400 hover:text-primary-300" onClick={onAdd}>+ Add</button>}
            </div>
            <div className="space-y-1 max-h-[220px] overflow-y-auto pr-1">
                {items.length === 0 ? (
                    <div className="text-center py-6 text-surface-200/20 text-xs">{placeholder || 'Empty'}</div>
                ) : items.map(item => (
                    <button
                        key={item.id}
                        onClick={() => onSelect(item)}
                        className={`w-full text-left rounded-lg p-2.5 border transition-all duration-100 ${
                            selected?.id === item.id
                                ? 'bg-primary-500/15 border-primary-500/30'
                                : 'bg-surface-900/30 border-surface-700/15 hover:border-primary-500/20 hover:bg-surface-800/40'
                        }`}
                    >
                        {renderItem(item)}
                    </button>
                ))}
            </div>
        </div>
    );
}
