/**
 * Chat page for interacting with the AI study assistant (RAG).
 *
 * Features:
 * - Improved UI contrast and readability
 * - Clickable source links (open document downloads)
 * - Scope selector (Subject / Workspace / All Documents)
 * - Quiz Mode toggle (generate questions + evaluate answers)
 * - No-hallucination guard (backend returns canned message when no context)
 */

import { useState, useRef, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { listWorkspaces, listCourses, listSubjects } from '../api/workspaces';
import { queryRAG } from '../api/rag';
import type { ChatMessage, Workspace, RAGSource } from '../types';
import Spinner from '../components/common/Spinner';

// API base URL for document download links
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ─── Types ──────────────────────────────────────────────

interface SubjectOption {
    id: string;
    label: string;
    courseId: string;
    workspaceId: string;
}

interface WorkspaceOption {
    id: string;
    name: string;
}

type Scope = 'subject' | 'workspace' | 'all';
type ChatMode = 'chat' | 'quiz';

interface QuizState {
    currentQuestion: string | null;
    awaitingAnswer: boolean;
    feedbackShown: boolean;
}

// ─── Component ──────────────────────────────────────────

export default function Chat() {
    const location = useLocation();
    const queryParams = new URLSearchParams(location.search);
    const initialSubjectId = queryParams.get('subject_id') || '';

    // Messages
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    // Scope & selection
    const [scope, setScope] = useState<Scope>(initialSubjectId ? 'subject' : 'all');
    const [allSubjects, setAllSubjects] = useState<SubjectOption[]>([]);
    const [allWorkspaces, setAllWorkspaces] = useState<WorkspaceOption[]>([]);
    const [selectedSubject, setSelectedSubject] = useState(initialSubjectId);
    const [selectedWorkspace, setSelectedWorkspace] = useState('');

    // Mode
    const [chatMode, setChatMode] = useState<ChatMode>('chat');
    const [quizState, setQuizState] = useState<QuizState>({
        currentQuestion: null,
        awaitingAnswer: false,
        feedbackShown: false,
    });

    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Load all subjects and workspaces on mount
    useEffect(() => {
        const loadAll = async () => {
            try {
                const wsList = await listWorkspaces();
                const wsOpts: WorkspaceOption[] = wsList.map((ws) => ({
                    id: ws.id,
                    name: ws.name,
                }));
                setAllWorkspaces(wsOpts);

                const opts: SubjectOption[] = [];
                for (const ws of wsList) {
                    const courses = await listCourses(ws.id);
                    for (const course of courses) {
                        const subjects = await listSubjects(ws.id, course.id);
                        for (const s of subjects) {
                            opts.push({
                                id: s.id,
                                label: `${ws.name} → ${course.name} → ${s.name}`,
                                courseId: course.id,
                                workspaceId: ws.id,
                            });
                        }
                    }
                }
                setAllSubjects(opts);

                if (!selectedSubject && opts.length > 0 && initialSubjectId) {
                    setSelectedSubject(initialSubjectId);
                }
                if (wsOpts.length > 0 && !selectedWorkspace) {
                    setSelectedWorkspace(wsOpts[0].id);
                }
            } catch (err) {
                console.error('Failed to load subjects', err);
            }
        };
        loadAll();
    }, []);

    // ─── Quiz helpers ───────────────────────────────────

    const requestQuizQuestion = async () => {
        setIsLoading(true);

        const systemMsg: ChatMessage = {
            id: Date.now().toString(),
            role: 'assistant',
            content: '🎯 Generating a quiz question from your study materials...',
            timestamp: new Date(),
        };
        setMessages((prev) => [...prev, systemMsg]);

        try {
            const response = await queryRAG({
                question: 'Generate 1 quiz question from the study material.',
                subject_id: scope === 'subject' ? selectedSubject || undefined : undefined,
                workspace_id: scope === 'workspace' ? selectedWorkspace || undefined : undefined,
                scope,
                mode: 'quiz',
            });

            const questionMsg: ChatMessage = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: `📝 **Quiz Question:**\n\n${response.answer}`,
                sources: response.sources,
                timestamp: new Date(),
            };

            setMessages((prev) => {
                // Replace the "generating" message
                const filtered = prev.filter((m) => m.id !== systemMsg.id);
                return [...filtered, questionMsg];
            });

            setQuizState({
                currentQuestion: response.answer,
                awaitingAnswer: true,
                feedbackShown: false,
            });
        } catch (error) {
            console.error('Quiz generation failed', error);
            const errorMsg: ChatMessage = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: 'Sorry, I could not generate a quiz question. Please try again.',
                timestamp: new Date(),
            };
            setMessages((prev) => {
                const filtered = prev.filter((m) => m.id !== systemMsg.id);
                return [...filtered, errorMsg];
            });
        } finally {
            setIsLoading(false);
        }
    };

    const evaluateQuizAnswer = async (answer: string) => {
        if (!quizState.currentQuestion) return;

        setIsLoading(true);

        try {
            const response = await queryRAG({
                question: quizState.currentQuestion,
                mode: 'quiz_evaluate',
                quiz_question: quizState.currentQuestion,
                user_answer: answer,
                scope,
                subject_id: scope === 'subject' ? selectedSubject || undefined : undefined,
                workspace_id: scope === 'workspace' ? selectedWorkspace || undefined : undefined,
            });

            const feedbackMsg: ChatMessage = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: response.answer,
                timestamp: new Date(),
            };

            setMessages((prev) => [...prev, feedbackMsg]);
            setQuizState({
                currentQuestion: null,
                awaitingAnswer: false,
                feedbackShown: true,
            });
        } catch (error) {
            console.error('Quiz evaluation failed', error);
            const errorMsg: ChatMessage = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: 'Sorry, I could not evaluate your answer. Please try again.',
                timestamp: new Date(),
            };
            setMessages((prev) => [...prev, errorMsg]);
        } finally {
            setIsLoading(false);
        }
    };

    // ─── Send message handler ───────────────────────────

    const handleSendMessage = async (e?: React.FormEvent) => {
        e?.preventDefault();
        if (!inputValue.trim() || isLoading) return;

        const userMessage: ChatMessage = {
            id: Date.now().toString(),
            role: 'user',
            content: inputValue,
            timestamp: new Date(),
        };

        setMessages((prev) => [...prev, userMessage]);
        setInputValue('');

        // Quiz mode: if awaiting answer, evaluate it
        if (chatMode === 'quiz' && quizState.awaitingAnswer) {
            await evaluateQuizAnswer(userMessage.content);
            return;
        }

        // Normal chat mode
        setIsLoading(true);

        try {
            const response = await queryRAG({
                question: userMessage.content,
                subject_id: scope === 'subject' ? selectedSubject || undefined : undefined,
                workspace_id: scope === 'workspace' ? selectedWorkspace || undefined : undefined,
                scope,
                mode: 'chat',
            });

            const assistantMessage: ChatMessage = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: response.answer,
                sources: response.sources,
                timestamp: new Date(),
            };

            setMessages((prev) => [...prev, assistantMessage]);
        } catch (error) {
            console.error('RAG Query failed', error);
            const errorMessage: ChatMessage = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content:
                    'Sorry, I encountered an error while processing your request. Make sure your documents are processed and try again.',
                timestamp: new Date(),
            };
            setMessages((prev) => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    // ─── Source click handler ───────────────────────────

    const handleSourceClick = (source: RAGSource) => {
        if (source.document_id) {
            const token = localStorage.getItem('access_token');
            const url = `${API_URL}/api/v1/documents/${source.document_id}/download`;
            // Open in new tab with auth
            window.open(url, '_blank');
        }
    };

    // ─── Mode toggle handler ────────────────────────────

    const handleModeToggle = (mode: ChatMode) => {
        setChatMode(mode);
        setQuizState({ currentQuestion: null, awaitingAnswer: false, feedbackShown: false });
    };

    // ─── Render ─────────────────────────────────────────

    return (
        <div className="flex flex-col h-[calc(100vh-8rem)] max-w-5xl mx-auto animate-fade-in">
            {/* Header */}
            <div className="flex flex-col gap-4 mb-6">
                {/* Title row */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <h1 className="text-2xl font-bold gradient-text">AI Study Assistant</h1>
                        <p className="text-sm text-surface-200/70 mt-0.5">
                            {chatMode === 'quiz'
                                ? 'Quiz Mode — test your knowledge from study materials'
                                : 'Ask questions about your study materials'}
                        </p>
                    </div>

                    {/* Mode toggle */}
                    <div className="flex items-center gap-1 p-1 rounded-xl bg-surface-900/60 border border-surface-700/50">
                        <button
                            onClick={() => handleModeToggle('chat')}
                            className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                                chatMode === 'chat'
                                    ? 'bg-primary-600 text-white shadow-md'
                                    : 'text-surface-200/70 hover:text-surface-100'
                            }`}
                        >
                            💬 Chat
                        </button>
                        <button
                            onClick={() => handleModeToggle('quiz')}
                            className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                                chatMode === 'quiz'
                                    ? 'bg-accent-600 text-white shadow-md'
                                    : 'text-surface-200/70 hover:text-surface-100'
                            }`}
                        >
                            🧠 Quiz
                        </button>
                    </div>
                </div>

                {/* Scope selector row */}
                <div className="flex flex-wrap items-center gap-2">
                    {/* Scope buttons */}
                    <div className="flex items-center gap-1 p-0.5 rounded-lg bg-surface-900/40 border border-surface-700/30">
                        {(['subject', 'workspace', 'all'] as Scope[]).map((s) => (
                            <button
                                key={s}
                                onClick={() => setScope(s)}
                                className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                                    scope === s
                                        ? 'bg-surface-700 text-surface-100'
                                        : 'text-surface-200/60 hover:text-surface-200'
                                }`}
                            >
                                {s === 'subject' && '📝 Subject'}
                                {s === 'workspace' && '🗂️ Workspace'}
                                {s === 'all' && '🌐 All'}
                            </button>
                        ))}
                    </div>

                    {/* Conditional dropdown */}
                    {scope === 'subject' && (
                        <select
                            className="input !py-1.5 !px-2 text-xs min-w-[220px] max-w-[400px]"
                            value={selectedSubject}
                            onChange={(e) => setSelectedSubject(e.target.value)}
                        >
                            <option value="">Select a subject...</option>
                            {allSubjects.map((s) => (
                                <option key={s.id} value={s.id}>
                                    {s.label}
                                </option>
                            ))}
                        </select>
                    )}

                    {scope === 'workspace' && (
                        <select
                            className="input !py-1.5 !px-2 text-xs min-w-[180px] max-w-[300px]"
                            value={selectedWorkspace}
                            onChange={(e) => setSelectedWorkspace(e.target.value)}
                        >
                            <option value="">Select a workspace...</option>
                            {allWorkspaces.map((ws) => (
                                <option key={ws.id} value={ws.id}>
                                    {ws.name}
                                </option>
                            ))}
                        </select>
                    )}

                    {scope === 'all' && (
                        <span className="text-xs text-surface-200/50 italic">
                            Searching all your documents
                        </span>
                    )}
                </div>
            </div>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto pr-2 space-y-7 custom-scrollbar pb-4">
                {messages.length === 0 && (
                    <div className="h-full flex flex-col items-center justify-center text-center p-8">
                        <span className="text-6xl mb-6 opacity-20">
                            {chatMode === 'quiz' ? '🧠' : '🤖'}
                        </span>
                        <h2 className="text-xl font-semibold text-surface-100">
                            {chatMode === 'quiz'
                                ? 'Ready to test your knowledge?'
                                : 'How can I help you study today?'}
                        </h2>
                        <p className="text-surface-200/60 mt-2 max-w-md text-sm">
                            {chatMode === 'quiz'
                                ? 'Click "New Question" below to get a quiz question from your study materials.'
                                : 'I can answer questions based on the documents you\'ve uploaded. Select a scope above to narrow down the context.'}
                        </p>
                        {chatMode === 'quiz' && (
                            <button
                                onClick={requestQuizQuestion}
                                disabled={isLoading}
                                className="mt-6 btn-primary !px-8 !py-3"
                            >
                                🎯 Generate First Question
                            </button>
                        )}
                    </div>
                )}

                {messages.map((msg) => (
                    <div
                        key={msg.id}
                        className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-slide-up`}
                    >
                        <div
                            className={`max-w-[85%] rounded-2xl p-4 ${
                                msg.role === 'user'
                                    ? 'bg-primary-600/30 border border-primary-500/25 text-surface-100 rounded-tr-none'
                                    : 'bg-surface-800/90 border border-surface-700/80 text-surface-200 rounded-tl-none'
                            }`}
                        >
                            <div className="whitespace-pre-wrap text-sm leading-7">
                                {msg.content}
                            </div>

                            {/* Sources — clickable links */}
                            {msg.sources && msg.sources.length > 0 && (
                                <div className="mt-4 pt-3 border-t border-surface-700/40">
                                    <p className="text-[10px] uppercase tracking-wider text-surface-200/50 font-bold mb-2">
                                        Sources
                                    </p>
                                    <div className="flex flex-wrap gap-1.5">
                                        {msg.sources.map((source, idx) => (
                                            <button
                                                key={idx}
                                                onClick={() => handleSourceClick(source)}
                                                className={`text-xs px-2.5 py-1 rounded-full border transition-all ${
                                                    source.document_id
                                                        ? 'bg-primary-600/10 border-primary-500/20 text-primary-300 hover:bg-primary-600/20 hover:border-primary-500/40 cursor-pointer'
                                                        : 'bg-surface-900/50 border-surface-700/50 text-surface-200/70 cursor-default'
                                                }`}
                                                title={source.content}
                                            >
                                                📄 {source.document_name || 'Document'}
                                                {source.page != null && ` — p.${source.page}`}
                                                {!source.page && source.chunk_index != null && ` — chunk ${source.chunk_index}`}
                                                <span className="ml-1 opacity-50">
                                                    ({(source.relevance_score * 100).toFixed(0)}%)
                                                </span>
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}

                            <div className="mt-2 text-[10px] opacity-30 text-right">
                                {msg.timestamp.toLocaleTimeString([], {
                                    hour: '2-digit',
                                    minute: '2-digit',
                                })}
                            </div>
                        </div>
                    </div>
                ))}

                {isLoading && (
                    <div className="flex justify-start animate-pulse">
                        <div className="bg-surface-800/90 border border-surface-700/80 rounded-2xl rounded-tl-none p-4">
                            <Spinner
                                size="sm"
                                label={
                                    chatMode === 'quiz'
                                        ? 'Processing quiz...'
                                        : 'Searching knowledge base...'
                                }
                            />
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Quiz: Next Question button */}
            {chatMode === 'quiz' && quizState.feedbackShown && !isLoading && (
                <div className="flex justify-center py-2">
                    <button
                        onClick={() => {
                            setQuizState({
                                currentQuestion: null,
                                awaitingAnswer: false,
                                feedbackShown: false,
                            });
                            requestQuizQuestion();
                        }}
                        className="btn-primary !px-6"
                    >
                        🎯 Next Question
                    </button>
                </div>
            )}

            {/* Input Area */}
            <form onSubmit={handleSendMessage} className="mt-3 relative">
                <input
                    type="text"
                    className="input w-full !pr-24 !py-4 shadow-xl"
                    placeholder={
                        chatMode === 'quiz' && quizState.awaitingAnswer
                            ? 'Type your answer...'
                            : chatMode === 'quiz'
                            ? 'Click "New Question" or type a topic for a question...'
                            : 'Ask a question about your documents...'
                    }
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    disabled={isLoading}
                />
                <button
                    type="submit"
                    disabled={isLoading || !inputValue.trim()}
                    className="absolute right-2 top-2 bottom-2 btn-primary !px-6"
                >
                    {isLoading
                        ? '...'
                        : chatMode === 'quiz' && quizState.awaitingAnswer
                        ? 'Submit'
                        : 'Send'}
                </button>
            </form>
        </div>
    );
}
