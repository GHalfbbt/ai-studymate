/**
 * Flashcard API service.
 * Handles flashcard generation, listing, review, and export.
 */

import apiClient from './client';

// --- Types ---

export interface FlashcardGenerateRequest {
  subject_id: string;
  document_id?: string;
  count: number;
}

export interface Flashcard {
  id: string;
  subject_id: string;
  document_id?: string;
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

// --- API calls ---

/**
 * Generate flashcards from study materials.
 */
export async function generateFlashcards(data: FlashcardGenerateRequest): Promise<Flashcard[]> {
  const res = await apiClient.post('/flashcards/generate', data);
  return res.data;
}

/**
 * List flashcards for a subject.
 */
export async function listFlashcards(subjectId: string, dueOnly = false): Promise<FlashcardListResponse> {
  const res = await apiClient.get('/flashcards/', {
    params: { subject_id: subjectId, due_only: dueOnly },
  });
  return res.data;
}

/**
 * Submit a flashcard review result (SM-2 algorithm).
 * quality: 0-5 (0=blackout, 5=perfect)
 */
export async function reviewFlashcard(flashcardId: string, quality: number): Promise<Flashcard> {
  const res = await apiClient.post(`/flashcards/${flashcardId}/review`, { quality });
  return res.data;
}

/**
 * Export flashcards as CSV for Anki import.
 */
export async function exportFlashcardsCSV(subjectId: string): Promise<string> {
  const res = await apiClient.get('/flashcards/export/csv', {
    params: { subject_id: subjectId },
    responseType: 'text',
  });
  return res.data;
}

/**
 * Delete a specific flashcard.
 */
export async function deleteFlashcard(flashcardId: string): Promise<void> {
  await apiClient.delete(`/flashcards/${flashcardId}`);
}

/**
 * Delete all flashcards for a subject.
 */
export async function deleteAllFlashcards(subjectId: string): Promise<void> {
  await apiClient.delete('/flashcards/', {
    params: { subject_id: subjectId },
  });
}
