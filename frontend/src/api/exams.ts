/**
 * Exam API service.
 * Handles exam generation, retrieval, submission, and evaluation.
 */

import apiClient from './client';

// --- Types ---

export interface ExamGenerateRequest {
  subject_id?: string;
  course_id?: string;
  workspace_id?: string;
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
  options?: string[];
  difficulty: string;
  topic?: string;
}

export interface Exam {
  id: string;
  subject_id: string;
  title: string;
  description?: string;
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

export interface AnswerFeedback {
  question_id: string;
  question_text: string;
  question_type: string;
  user_answer: string;
  correct_answer?: string;
  is_correct: boolean;
  score?: number;
  feedback?: string;
  explanation?: string;
}

export interface ExamResult {
  attempt_id: string;
  exam_id: string;
  exam_title: string;
  score: number;
  total_questions: number;
  correct_answers: number;
  answers: AnswerFeedback[];
  completed_at: string;
}

export interface ExamAttempt {
  attempt_id: string;
  started_at: string;
  completed_at?: string;
  status: string;
  score?: number;
  correct_answers?: number;
  total_questions: number;
}

// --- API calls ---

/**
 * Generate an exam from study materials.
 */
export async function generateExam(data: ExamGenerateRequest): Promise<Exam> {
  const res = await apiClient.post('/exams/generate', data);
  return res.data;
}

/**
 * List exams, optionally filtered by subject.
 */
export async function listExams(subjectId?: string): Promise<Exam[]> {
  const params = subjectId ? { subject_id: subjectId } : {};
  const res = await apiClient.get('/exams/', { params });
  return res.data;
}

/**
 * Get a specific exam by ID.
 */
export async function getExam(examId: string): Promise<Exam> {
  const res = await apiClient.get(`/exams/${examId}`);
  return res.data;
}

/**
 * Start a new exam attempt.
 */
export async function startExamAttempt(examId: string): Promise<{ attempt_id: string }> {
  const res = await apiClient.post(`/exams/${examId}/start`);
  return res.data;
}

/**
 * Submit exam answers for evaluation.
 */
export async function submitExam(examId: string, answers: SubmitAnswer[]): Promise<ExamResult> {
  const res = await apiClient.post(`/exams/${examId}/submit`, { answers });
  return res.data;
}

/**
 * List attempts for a specific exam.
 */
export async function listAttempts(examId: string): Promise<ExamAttempt[]> {
  const res = await apiClient.get(`/exams/${examId}/attempts`);
  return res.data;
}

/**
 * Delete an exam.
 */
export async function deleteExam(examId: string): Promise<void> {
  await apiClient.delete(`/exams/${examId}`);
}
