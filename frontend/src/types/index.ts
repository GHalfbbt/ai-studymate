/**
 * TypeScript type definitions for the AI StudyMate frontend.
 *
 * These interfaces mirror the backend Pydantic schemas
 * for type-safe API communication.
 */

// ============================================================
// User & Authentication
// ============================================================

export interface User {
    id: string;
    email: string;
    full_name: string | null;
    created_at: string;
}

export interface LoginCredentials {
    email: string;
    password: string;
}

export interface RegisterData {
    email: string;
    password: string;
    full_name?: string;
}

export interface AuthToken {
    access_token: string;
    token_type: string;
}

// ============================================================
// Organization Hierarchy
// ============================================================

export interface Workspace {
    id: string;
    name: string;
    description: string | null;
    created_at: string;
    course_count: number;
}

export interface Course {
    id: string;
    workspace_id: string;
    name: string;
    created_at: string;
    subject_count: number;
}

export interface Subject {
    id: string;
    course_id: string;
    name: string;
    color: string;
    created_at: string;
    document_count: number;
    topic_count?: number;
}

export interface Topic {
    id: string;
    subject_id: string;
    name: string;
    position: number;
    created_at: string;
    document_count: number;
}

// ============================================================
// Documents
// ============================================================

export interface Document {
    id: string;
    subject_id: string;
    filename: string;
    file_type: string;
    file_size: number | null;
    processing_status: 'pending' | 'processing' | 'completed' | 'failed';
    processing_error: string | null;
    language: string;
    chunk_count: number;
    created_at: string;
}

export interface DocumentListResponse {
    documents: Document[];
    total: number;
}

// ============================================================
// RAG (Retrieval-Augmented Generation)
// ============================================================

export interface RAGQuery {
    question: string;
    subject_id?: string;
    document_ids?: string[];
    top_k?: number;
}

export interface RAGSource {
    source_number: number;
    document_id: string | null;
    filename: string | null;
    chunk_index: number | null;
    relevance_score: number;
    excerpt: string;
}

export interface RAGResponse {
    answer: string;
    sources: RAGSource[];
    confidence: number;
}

// ============================================================
// Exams
// ============================================================

export interface ExamGenerateRequest {
    subject_id: string;
    title?: string;
    mc_count: number;
    short_answer_count: number;
    difficulty: 'easy' | 'medium' | 'hard';
    document_ids?: string[];
}

export interface ExamQuestion {
    id: string;
    question_order: number;
    question_type: 'mc' | 'short_answer';
    question_text: string;
    options: string[] | null;
    difficulty: string;
    topic: string | null;
}

export interface Exam {
    id: string;
    subject_id: string;
    title: string;
    description: string | null;
    question_count: number;
    mc_count: number;
    short_answer_count: number;
    questions: ExamQuestion[];
    created_at: string;
}

export interface SubmitAnswer {
    question_id: string;
    user_answer: string;
}

export interface ExamAnswerFeedback {
    question_id: string;
    question_text: string;
    question_type: string;
    user_answer: string;
    correct_answer: string | null;
    is_correct: boolean;
    score: number | null;
    feedback: string | null;
    explanation: string | null;
}

export interface ExamResult {
    attempt_id: string;
    exam_id: string;
    exam_title: string;
    score: number;
    total_questions: number;
    correct_answers: number;
    answers: ExamAnswerFeedback[];
    completed_at: string;
}

// ============================================================
// Flashcards
// ============================================================

export interface Flashcard {
    id: string;
    subject_id: string;
    document_id: string | null;
    front: string;
    back: string;
    difficulty: string;
    times_reviewed: number;
    ease_factor: number;
    created_at: string;
}

export interface FlashcardListResponse {
    flashcards: Flashcard[];
    total: number;
}

// ============================================================
// Voice
// ============================================================

export interface TranscribeResponse {
    text: string;
    language: string;
    duration_seconds: number | null;
    provider: string;
}

export interface SpeakingEvaluation {
    transcription: string;
    grammar_score: number;
    fluency_score: number;
    vocabulary_score: number;
    pronunciation_score: number;
    overall_score: number;
    feedback: Record<string, unknown>;
    corrections: Array<{ original: string; corrected: string }>;
}

// ============================================================
// Analytics
// ============================================================

export interface AnalyticsDashboard {
    total_documents: number;
    total_exams_taken: number;
    average_score: number;
    subjects_studied: number;
    accuracy_by_subject: Array<{
        subject_name: string;
        accuracy: number;
        exams_taken: number;
    }>;
    progress_over_time: Array<{
        date: string;
        score: number;
    }>;
    weak_topics: Array<{
        topic: string;
        accuracy: number;
        question_count: number;
    }>;
}

// ============================================================
// Chat Messages (for RAG interface)
// ============================================================

export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    sources?: RAGSource[];
    confidence?: number;
    timestamp: Date;
}
