/**
 * Dashboard page - Main overview of workspaces, courses, and subjects.
 *
 * Provides navigation through the organization hierarchy
 * and quick access to study features. Shows uploaded documents
 * and their processing status.
 */

import { useState, useEffect } from 'react';
import { listDocuments } from '../api/documents';
import type { Document } from '../types';
import DropZone from '../components/Upload/DropZone';
import Spinner from '../components/common/Spinner';
import {
    formatFileSize,
    formatDate,
    getFileTypeIcon,
    getStatusBadgeClass,
} from '../utils/formatters';

export default function Dashboard() {
    const [documents, setDocuments] = useState<Document[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // For MVP, we use a mock subject ID
    // This will be replaced with real workspace/course/subject selection
    const mockSubjectId = '00000000-0000-0000-0000-000000000001';

    const fetchDocuments = async () => {
        setIsLoading(true);
        try {
            const response = await listDocuments();
            setDocuments(response.documents);
            setError(null);
        } catch {
            // Expected to fail until auth is set up - show empty state
            setDocuments([]);
            setError(null);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchDocuments();
    }, []);

    return (
        <div className="max-w-7xl mx-auto space-y-8 animate-fade-in">
            {/* Page Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold gradient-text">Dashboard</h1>
                    <p className="text-surface-200/50 mt-1">
                        Manage your study materials and track your progress
                    </p>
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
                <h2 className="text-lg font-semibold text-surface-100 mb-4">
                    📤 Upload Study Materials
                </h2>
                <DropZone
                    subjectId={mockSubjectId}
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
