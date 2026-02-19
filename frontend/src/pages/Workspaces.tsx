/**
 * Workspaces page — Full hierarchy manager.
 *
 * Allows the user to browse and create:
 *   Workspace → Course → Subject
 *
 * From here they can navigate to upload documents to a subject,
 * or jump straight to the Chat with a subject pre-selected.
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    listWorkspaces, createWorkspace,
    listCourses, createCourse,
    listSubjects, createSubject,
} from '../api/workspaces';
import type { Workspace, Course, Subject } from '../types';
import Spinner from '../components/common/Spinner';

// Palette of colors for subjects
const SUBJECT_COLORS = [
    '#6366F1', '#8B5CF6', '#06B6D4', '#10B981',
    '#F59E0B', '#EF4444', '#EC4899', '#14B8A6',
];

export default function Workspaces() {
    const navigate = useNavigate();

    const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
    const [selectedWs, setSelectedWs] = useState<Workspace | null>(null);
    const [courses, setCourses] = useState<Course[]>([]);
    const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);
    const [subjects, setSubjects] = useState<Subject[]>([]);

    const [isLoading, setIsLoading] = useState(true);
    const [activeColor, setActiveColor] = useState(SUBJECT_COLORS[0]);

    // Modal state
    const [modal, setModal] = useState<null | 'workspace' | 'course' | 'subject'>(null);
    const [inputName, setInputName] = useState('');
    const [inputDesc, setInputDesc] = useState('');
    const [isSaving, setIsSaving] = useState(false);

    // ── Load workspaces ────────────────────────────────
    useEffect(() => {
        const load = async () => {
            setIsLoading(true);
            try {
                const list = await listWorkspaces();
                setWorkspaces(list);
                if (list.length > 0) setSelectedWs(list[0]);
            } finally {
                setIsLoading(false);
            }
        };
        load();
    }, []);

    // ── Load courses when workspace changes ────────────
    useEffect(() => {
        if (!selectedWs) return;
        setCourses([]);
        setSelectedCourse(null);
        setSubjects([]);
        listCourses(selectedWs.id).then(list => {
            setCourses(list);
            if (list.length > 0) setSelectedCourse(list[0]);
        });
    }, [selectedWs]);

    // ── Load subjects when course changes ──────────────
    useEffect(() => {
        if (!selectedWs || !selectedCourse) return;
        setSubjects([]);
        listSubjects(selectedWs.id, selectedCourse.id).then(setSubjects);
    }, [selectedCourse]);

    // ── CRUD handlers ──────────────────────────────────
    const openModal = (type: 'workspace' | 'course' | 'subject') => {
        setInputName('');
        setInputDesc('');
        setActiveColor(SUBJECT_COLORS[Math.floor(Math.random() * SUBJECT_COLORS.length)]);
        setModal(type);
    };

    const handleSave = async () => {
        if (!inputName.trim()) return;
        setIsSaving(true);
        try {
            if (modal === 'workspace') {
                const ws = await createWorkspace(inputName, inputDesc || undefined);
                setWorkspaces(prev => [ws, ...prev]);
                setSelectedWs(ws);
            } else if (modal === 'course' && selectedWs) {
                const course = await createCourse(selectedWs.id, inputName);
                setCourses(prev => [course, ...prev]);
                setSelectedCourse(course);
                // Update workspace course_count
                setWorkspaces(prev => prev.map(w => w.id === selectedWs.id ? { ...w, course_count: w.course_count + 1 } : w));
            } else if (modal === 'subject' && selectedWs && selectedCourse) {
                const subj = await createSubject(selectedWs.id, selectedCourse.id, inputName, activeColor);
                setSubjects(prev => [...prev, subj]);
            }
            setModal(null);
        } catch (err) {
            console.error('Error saving:', err);
        } finally {
            setIsSaving(false);
        }
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <Spinner size="lg" label="Loading your workspaces..." />
            </div>
        );
    }

    return (
        <div className="max-w-7xl mx-auto animate-fade-in space-y-6">
            {/* Header */}
            <div className="flex items-end justify-between">
                <div>
                    <h1 className="text-3xl font-bold gradient-text">My Workspaces</h1>
                    <p className="text-surface-200/50 mt-1 text-sm">
                        Organize your study materials: Workspace → Course → Subject
                    </p>
                </div>
                <button className="btn-primary" onClick={() => openModal('workspace')}>
                    + New Workspace
                </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* ── Column 1: Workspaces ── */}
                <div className="lg:col-span-3 space-y-2">
                    <div className="flex items-center justify-between mb-3">
                        <h2 className="text-xs font-bold uppercase tracking-widest text-surface-200/40">Workspaces</h2>
                    </div>
                    {workspaces.length === 0 ? (
                        <div className="text-center py-8 text-surface-200/30 text-sm">
                            No workspaces yet
                        </div>
                    ) : workspaces.map(ws => (
                        <button
                            key={ws.id}
                            onClick={() => setSelectedWs(ws)}
                            className={`w-full text-left rounded-xl p-3.5 border transition-all duration-150 ${selectedWs?.id === ws.id
                                    ? 'bg-primary-500/15 border-primary-500/30 text-primary-300'
                                    : 'bg-surface-900/30 border-surface-700/20 text-surface-300 hover:border-primary-500/20 hover:bg-surface-800/40'
                                }`}
                        >
                            <div className="font-medium text-sm truncate">{ws.name}</div>
                            <div className="text-[11px] mt-0.5 opacity-50">
                                {ws.course_count} course{ws.course_count !== 1 ? 's' : ''}
                            </div>
                        </button>
                    ))}
                </div>

                {/* ── Column 2: Courses ── */}
                <div className="lg:col-span-3 space-y-2">
                    <div className="flex items-center justify-between mb-3">
                        <h2 className="text-xs font-bold uppercase tracking-widest text-surface-200/40">Courses</h2>
                        {selectedWs && (
                            <button
                                className="text-xs text-primary-400 hover:text-primary-300"
                                onClick={() => openModal('course')}
                            >
                                + Add
                            </button>
                        )}
                    </div>
                    {!selectedWs ? (
                        <div className="text-center py-8 text-surface-200/20 text-sm">← Select a workspace</div>
                    ) : courses.length === 0 ? (
                        <div className="text-center py-8 space-y-2">
                            <div className="text-surface-200/30 text-sm">No courses yet</div>
                            <button className="btn-secondary text-xs" onClick={() => openModal('course')}>+ New Course</button>
                        </div>
                    ) : courses.map(course => (
                        <button
                            key={course.id}
                            onClick={() => setSelectedCourse(course)}
                            className={`w-full text-left rounded-xl p-3.5 border transition-all duration-150 ${selectedCourse?.id === course.id
                                    ? 'bg-accent-500/15 border-accent-500/30 text-accent-300'
                                    : 'bg-surface-900/30 border-surface-700/20 text-surface-300 hover:border-accent-500/20 hover:bg-surface-800/40'
                                }`}
                        >
                            <div className="font-medium text-sm truncate">📖 {course.name}</div>
                            <div className="text-[11px] mt-0.5 opacity-50">
                                {course.subject_count} subject{course.subject_count !== 1 ? 's' : ''}
                            </div>
                        </button>
                    ))}
                </div>

                {/* ── Column 3: Subjects ── */}
                <div className="lg:col-span-6">
                    <div className="flex items-center justify-between mb-3">
                        <h2 className="text-xs font-bold uppercase tracking-widest text-surface-200/40">
                            Subjects {selectedCourse ? `— ${selectedCourse.name}` : ''}
                        </h2>
                        {selectedCourse && (
                            <button
                                className="text-xs text-primary-400 hover:text-primary-300"
                                onClick={() => openModal('subject')}
                            >
                                + Add Subject
                            </button>
                        )}
                    </div>

                    {!selectedCourse ? (
                        <div className="text-center py-16 text-surface-200/20 text-sm">← Select a course</div>
                    ) : subjects.length === 0 ? (
                        <div className="text-center py-16 space-y-3">
                            <span className="text-5xl opacity-20">📝</span>
                            <div className="text-surface-200/30 text-sm">No subjects yet</div>
                            <button className="btn-secondary text-xs" onClick={() => openModal('subject')}>+ Add First Subject</button>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            {subjects.map(subj => (
                                <div
                                    key={subj.id}
                                    className="card hover:scale-[1.02] transition-all duration-150 cursor-pointer group"
                                    style={{ borderLeft: `3px solid ${subj.color}` }}
                                >
                                    <div className="flex items-start justify-between">
                                        <div className="flex-1 min-w-0">
                                            <h3 className="font-semibold text-surface-100 text-sm truncate">{subj.name}</h3>
                                            <p className="text-[11px] text-surface-200/40 mt-1">
                                                {subj.document_count} document{subj.document_count !== 1 ? 's' : ''}
                                            </p>
                                        </div>
                                        <div
                                            className="w-3 h-3 rounded-full flex-shrink-0 mt-1"
                                            style={{ backgroundColor: subj.color }}
                                        />
                                    </div>
                                    <div className="flex gap-2 mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button
                                            className="btn-secondary text-[10px] !py-1 !px-2"
                                            onClick={() => navigate(`/dashboard?subject=${subj.id}`)}
                                        >
                                            📤 Upload
                                        </button>
                                        <button
                                            className="btn-secondary text-[10px] !py-1 !px-2"
                                            onClick={() => navigate(`/chat?subject_id=${subj.id}`)}
                                        >
                                            💬 Chat
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* ── Modal ── */}
            {modal && (
                <div
                    className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
                    onClick={() => setModal(null)}
                >
                    <div
                        className="card w-full max-w-md animate-slide-up"
                        onClick={e => e.stopPropagation()}
                    >
                        <h2 className="text-lg font-semibold text-surface-100 mb-4">
                            {modal === 'workspace' && '🗂️ New Workspace'}
                            {modal === 'course' && '📖 New Course'}
                            {modal === 'subject' && '📝 New Subject'}
                        </h2>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm text-surface-200/60 mb-1">
                                    {modal === 'workspace' ? 'Workspace name' : modal === 'course' ? 'Course name' : 'Subject name'}
                                </label>
                                <input
                                    className="input w-full"
                                    placeholder={
                                        modal === 'workspace' ? 'e.g. Computer Science Degree'
                                            : modal === 'course' ? 'e.g. Year 1 — Semester 2'
                                                : 'e.g. Advanced Algorithms'
                                    }
                                    value={inputName}
                                    onChange={e => setInputName(e.target.value)}
                                    onKeyDown={e => e.key === 'Enter' && handleSave()}
                                    autoFocus
                                />
                            </div>

                            {modal === 'workspace' && (
                                <div>
                                    <label className="block text-sm text-surface-200/60 mb-1">Description (optional)</label>
                                    <input
                                        className="input w-full"
                                        placeholder="Brief description..."
                                        value={inputDesc}
                                        onChange={e => setInputDesc(e.target.value)}
                                    />
                                </div>
                            )}

                            {modal === 'subject' && (
                                <div>
                                    <label className="block text-sm text-surface-200/60 mb-2">Color</label>
                                    <div className="flex gap-2 flex-wrap">
                                        {SUBJECT_COLORS.map(c => (
                                            <button
                                                key={c}
                                                className={`w-7 h-7 rounded-full border-2 transition-transform ${activeColor === c ? 'scale-125 border-white' : 'border-transparent'}`}
                                                style={{ backgroundColor: c }}
                                                onClick={() => setActiveColor(c)}
                                            />
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>

                        <div className="flex gap-3 mt-6">
                            <button className="btn-secondary flex-1" onClick={() => setModal(null)}>Cancel</button>
                            <button
                                className="btn-primary flex-1"
                                onClick={handleSave}
                                disabled={!inputName.trim() || isSaving}
                            >
                                {isSaving ? '⏳ Saving...' : 'Create'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
