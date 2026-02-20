import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { listDocuments } from '../api/documents';
import { listWorkspaces, listCourses, listSubjects } from '../api/workspaces';
import type { Document, Workspace, Course, Subject } from '../types';
import DropZone from '../components/Upload/DropZone';
import Spinner from '../components/common/Spinner';
import {
    formatFileSize,
    formatDate,
    getFileTypeIcon,
    getStatusBadgeClass,
} from '../utils/formatters';

export default function Dashboard() {
    const location = useLocation();
    const urlParams = new URLSearchParams(location.search);
    const preselectedSubject = urlParams.get('subject') || '';

    const [documents, setDocuments] = useState<Document[]>([]);
    const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
    const [courses, setCourses] = useState<Course[]>([]);
    const [subjects, setSubjects] = useState<Subject[]>([]);

    const [selectedWorkspace, setSelectedWorkspace] = useState<string>('');
    const [selectedCourse, setSelectedCourse] = useState<string>('');
    const [selectedSubject, setSelectedSubject] = useState<string>('');

    const [isLoading, setIsLoading] = useState(false);
    const [isLoadingHierarchy, setIsLoadingHierarchy] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Initial load: Fetch workspaces
    useEffect(() => {
        const init = async () => {
            setIsLoadingHierarchy(true);
            try {
                const wsList = await listWorkspaces();
                setWorkspaces(wsList);
                if (wsList.length > 0) {
                    setSelectedWorkspace(wsList[0].id);
                }
            } catch (err) {
                console.error("Failed to fetch workspaces", err);
            } finally {
                setIsLoadingHierarchy(false);
            }
        };
        init();
    }, []);

    // When workspace changes, fetch courses
    useEffect(() => {
        if (!selectedWorkspace) return;
        const fetchCourses = async () => {
            try {
                const cList = await listCourses(selectedWorkspace);
                setCourses(cList);
                if (cList.length > 0) {
                    setSelectedCourse(cList[0].id);
                } else {
                    setSelectedCourse('');
                    setSubjects([]);
                    setSelectedSubject('');
                }
            } catch (err) {
                console.error("Failed to fetch courses", err);
            }
        };
        fetchCourses();
    }, [selectedWorkspace]);

    // When course changes, fetch subjects
    useEffect(() => {
        if (!selectedWorkspace || !selectedCourse) return;
        const fetchS = async () => {
            try {
                const sList = await listSubjects(selectedWorkspace, selectedCourse);
                setSubjects(sList);
                if (preselectedSubject && sList.some(s => s.id === preselectedSubject)) {
                    setSelectedSubject(preselectedSubject);
                } else if (sList.length > 0 && !selectedSubject) {
                    setSelectedSubject(sList[0].id);
                } else if (sList.length === 0) {
                    setSelectedSubject('');
                }
            } catch (err) {
                console.error("Failed to fetch subjects", err);
            }
        };
        fetchS();
    }, [selectedWorkspace, selectedCourse]);

    const fetchDocuments = async () => {
        setIsLoading(true);
        try {
            // Fetch all documents or filter by subject if selected
            const filters: Record<string, string> = {};
            if (selectedSubject) filters.subject_id = selectedSubject;
            else if (selectedCourse) filters.course_id = selectedCourse;
            else if (selectedWorkspace) filters.workspace_id = selectedWorkspace;
            const response = await listDocuments(Object.keys(filters).length > 0 ? filters : undefined);
            setDocuments(response.documents);
            setError(null);
        } catch {
            setDocuments([]);
        } finally {
            setIsLoading(false);
        }
    };

    // Refetch documents when selected subject changes
    useEffect(() => {
        fetchDocuments();
    }, [selectedSubject]);

    return (
        <div className="max-w-7xl mx-auto space-y-8 animate-fade-in">
            {/* Page Header */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                <div>
                    <h1 className="text-3xl font-bold gradient-text">Dashboard</h1>
                    <p className="text-surface-200/50 mt-1">
                        Manage your study materials and track your progress
                    </p>
                </div>

                {/* Hierarchy Selectors */}
                <div className="flex flex-wrap items-center gap-3">
                    <div className="flex flex-col gap-1">
                        <span className="text-[10px] uppercase tracking-wider text-surface-200/40 ml-1 font-semibold">Workspace</span>
                        <select
                            className="input !py-1.5 !px-3 text-sm min-w-[140px]"
                            value={selectedWorkspace}
                            onChange={(e) => setSelectedWorkspace(e.target.value)}
                            disabled={isLoadingHierarchy}
                        >
                            {workspaces.map(ws => <option key={ws.id} value={ws.id}>{ws.name}</option>)}
                            {workspaces.length === 0 && <option value="">No Workspaces</option>}
                        </select>
                    </div>

                    <div className="flex flex-col gap-1">
                        <span className="text-[10px] uppercase tracking-wider text-surface-200/40 ml-1 font-semibold">Course</span>
                        <select
                            className="input !py-1.5 !px-3 text-sm min-w-[140px]"
                            value={selectedCourse}
                            onChange={(e) => setSelectedCourse(e.target.value)}
                            disabled={!selectedWorkspace || courses.length === 0}
                        >
                            {courses.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                            {courses.length === 0 && <option value="">No Courses</option>}
                        </select>
                    </div>

                    <div className="flex flex-col gap-1">
                        <span className="text-[10px] uppercase tracking-wider text-surface-200/40 ml-1 font-semibold">Subject</span>
                        <select
                            className="input !py-1.5 !px-3 text-sm min-w-[140px]"
                            value={selectedSubject}
                            onChange={(e) => setSelectedSubject(e.target.value)}
                            disabled={!selectedCourse || subjects.length === 0}
                        >
                            {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                            {subjects.length === 0 && <option value="">No Subjects</option>}
                        </select>
                    </div>
                </div>
            </div>

            {/* Quick Stats */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                    { label: 'Documents', value: documents.length, icon: '📄', color: 'from-primary-500/20 to-primary-600/10' },
                    { label: 'Processed', value: documents.filter(d => d.processing_status === 'completed').length, icon: '✅', color: 'from-accent-500/20 to-accent-600/10' },
                    { label: 'Processing', value: documents.filter(d => d.processing_status === 'processing').length, icon: '⏳', color: 'from-warning-500/20 to-warning-400/10' },
                    { label: 'Total Chunks', value: documents.reduce((sum, d) => sum + d.chunk_count, 0), icon: '🧩', color: 'from-primary-400/20 to-accent-500/10' },
                ].map((stat) => (
                    <div
                        key={stat.label}
                        className={`card bg-gradient-to-br ${stat.color} !border-transparent`}
                    >
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-surface-200/50">{stat.label}</p>
                                <p className="text-3xl font-bold text-surface-100 mt-1">
                                    {stat.value}
                                </p>
                            </div>
                            <span className="text-3xl opacity-80">{stat.icon}</span>
                        </div>
                    </div>
                ))}
            </div>

            {/* Upload Section */}
            <div className="card">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold text-surface-100">
                        📤 Upload Study Materials
                    </h2>
                    {!selectedSubject && (
                        <span className="text-xs text-warning-400 bg-warning-400/10 px-2 py-1 rounded-md animate-pulse">
                            Please select a subject first
                        </span>
                    )}
                </div>
                <DropZone
                    subjectId={selectedSubject}
                    onUploadComplete={fetchDocuments}
                />
            </div>

            {/* Documents List */}
            <div className="card">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-lg font-semibold text-surface-100">
                        📚 Your Documents
                    </h2>
                    <button
                        onClick={fetchDocuments}
                        className="btn-secondary text-xs"
                        disabled={isLoading}
                    >
                        🔄 Refresh
                    </button>
                </div>

                {isLoading ? (
                    <div className="flex justify-center py-12">
                        <Spinner size="lg" label="Loading documents..." />
                    </div>
                ) : error ? (
                    <div className="text-center py-12">
                        <p className="text-danger-400">{error}</p>
                    </div>
                ) : documents.length === 0 ? (
                    <div className="text-center py-12">
                        <span className="text-5xl opacity-30">📭</span>
                        <p className="text-surface-200/40 mt-4 text-lg">
                            No documents uploaded yet
                        </p>
                        <p className="text-surface-200/30 text-sm mt-1">
                            Upload your first study material above to get started
                        </p>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {documents.map((doc) => (
                            <div
                                key={doc.id}
                                className="flex items-center gap-4 p-4 rounded-xl bg-surface-900/40 border border-primary-500/5 hover:border-primary-500/15 transition-all duration-200 animate-slide-up"
                            >
                                {/* File type icon */}
                                <span className="text-2xl flex-shrink-0">
                                    {getFileTypeIcon(doc.file_type)}
                                </span>

                                {/* File info */}
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium text-surface-100 truncate">
                                        {doc.filename}
                                    </p>
                                    <div className="flex items-center gap-3 mt-1 text-xs text-surface-200/40">
                                        <span>{formatFileSize(doc.file_size)}</span>
                                        <span>•</span>
                                        <span>{doc.chunk_count} chunks</span>
                                        <span>•</span>
                                        <span>{formatDate(doc.created_at)}</span>
                                    </div>
                                </div>

                                {/* Processing status badge */}
                                <span className={`badge ${getStatusBadgeClass(doc.processing_status)}`}>
                                    {doc.processing_status === 'processing' && (
                                        <span className="inline-block w-2 h-2 rounded-full bg-current animate-pulse mr-1" />
                                    )}
                                    {doc.processing_status}
                                </span>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
