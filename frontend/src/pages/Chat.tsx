/**
 * Chat page for interacting with the AI study assistant (RAG).
 * 
 * Provides a message-based interface for asking questions about
 * uploaded documents. Displays sources and relevance scores.
 */

import { useState, useRef, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { listWorkspaces, listCourses, listSubjects } from '../api/workspaces';
import { queryRAG } from '../api/rag';
import type { ChatMessage, Workspace, Course, Subject } from '../types';
import Spinner from '../components/common/Spinner';

export default function Chat() {
    const location = useLocation();
    const queryParams = new URLSearchParams(location.search);
    const initialSubjectId = queryParams.get('subject_id') || '';

    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    // Flattened subject list from all workspaces
    interface SubjectOption { id: string; label: string; courseId: string; }
    const [allSubjects, setAllSubjects] = useState<SubjectOption[]>([]);
    const [selectedSubject, setSelectedSubject] = useState(initialSubjectId);

    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Load all subjects from all workspaces on mount
    useEffect(() => {
        const loadAll = async () => {
            try {
                const wsList = await listWorkspaces();
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
                            });
                        }
                    }
                }
                setAllSubjects(opts);
                if (!selectedSubject && opts.length > 0) {
                    setSelectedSubject(initialSubjectId || opts[0].id);
                }
            } catch (err) {
                console.error("Failed to load subjects", err);
            }
        };
        loadAll();
    }, []);

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
        setIsLoading(true);

        try {
            const response = await queryRAG({
                question: userMessage.content,
                subject_id: selectedSubject || undefined,
            });

            // Map backend RAGSource format to frontend ChatMessage source format
            const mappedSources = response.sources?.map((s: any, idx: number) => ({
                source_number: idx + 1,
                document_id: null,
                filename: s.document_name || s.filename || null,
                chunk_index: s.chunk_index ?? null,
                relevance_score: s.relevance_score ?? 0,
                excerpt: s.content || s.excerpt || '',
            }));

            const assistantMessage: ChatMessage = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: response.answer,
                sources: mappedSources,
                confidence: response.confidence,
                timestamp: new Date(),
            };

            setMessages((prev) => [...prev, assistantMessage]);
        } catch (error) {
            console.error("RAG Query failed", error);
            const errorMessage: ChatMessage = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: "Sorry, I encountered an error while processing your request. Make sure your documents are processed and try again.",
                timestamp: new Date(),
            };
            setMessages((prev) => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-[calc(100vh-8rem)] max-w-5xl mx-auto animate-fade-in">
            {/* Header / Selector */}
            <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-4">
                <div>
                    <h1 className="text-2xl font-bold gradient-text">AI Study Assistant</h1>
                    <p className="text-sm text-surface-200/70 mt-0.5">Ask questions about your study materials</p>
                </div>

                <div className="flex items-center gap-2">
                    <select
                        className="input !py-1 !px-2 text-xs min-w-[200px]"
                        value={selectedSubject}
                        onChange={(e) => setSelectedSubject(e.target.value)}
                    >
                        <option value="">🌐 Full Knowledge Base</option>
                        {allSubjects.map(s => (
                            <option key={s.id} value={s.id}>
                                📝 {s.label}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto pr-2 space-y-6 custom-scrollbar pb-4">
                {messages.length === 0 && (
                    <div className="h-full flex flex-col items-center justify-center text-center p-8">
                        <span className="text-6xl mb-6 opacity-20">🤖</span>
                        <h2 className="text-xl font-semibold text-surface-100">How can I help you study today?</h2>
                        <p className="text-surface-200/60 mt-2 max-w-md text-sm">
                            I can answer questions based on the documents you've uploaded to your subjects.
                            Select a subject above to narrow down the context.
                        </p>
                    </div>
                )}

                {messages.map((msg) => (
                    <div
                        key={msg.id}
                        className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-slide-up`}
                    >
                        <div className={`max-w-[85%] rounded-2xl p-4 ${msg.role === 'user'
                            ? 'bg-primary-600/20 border border-primary-500/20 text-surface-100 rounded-tr-none'
                            : 'bg-surface-800 border border-surface-700 text-surface-200 rounded-tl-none'
                            }`}>
                            <div className="whitespace-pre-wrap text-sm leading-relaxed">
                                {msg.content}
                            </div>

                            {/* Sources */}
                            {msg.sources && msg.sources.length > 0 && (
                                <div className="mt-4 pt-3 border-t border-surface-700/50">
                                    <p className="text-xs uppercase tracking-wider text-surface-200/60 font-bold mb-2">Sources</p>
                                    <div className="flex flex-wrap gap-2">
                                        {msg.sources.map((source, idx) => (
                                            <div
                                                key={idx}
                                                className="text-xs px-2 py-1 rounded bg-surface-900/50 border border-surface-700 text-surface-200/80"
                                                title={source.excerpt}
                                            >
                                                📄 {source.filename || 'Document'} ({(source.relevance_score * 100).toFixed(0)}%)
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            <div className="mt-2 text-xs opacity-40 text-right">
                                {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </div>
                        </div>
                    </div>
                ))}

                {isLoading && (
                    <div className="flex justify-start animate-pulse">
                        <div className="bg-surface-800 border border-surface-700 rounded-2xl rounded-tl-none p-4">
                            <Spinner size="sm" label="Searching knowledge base..." />
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <form
                onSubmit={handleSendMessage}
                className="mt-4 relative"
            >
                <input
                    type="text"
                    className="input w-full !pr-24 !py-4 shadow-xl"
                    placeholder="Ask a question about your documents..."
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    disabled={isLoading}
                />
                <button
                    type="submit"
                    disabled={isLoading || !inputValue.trim()}
                    className="absolute right-2 top-2 bottom-2 btn-primary !px-6"
                >
                    {isLoading ? '...' : 'Send'}
                </button>
            </form>
        </div>
    );
}
