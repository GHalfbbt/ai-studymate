/**
 * Document API service.
 *
 * Handles document upload, listing, and deletion.
 */

import apiClient from './client';
import type { Document, DocumentListResponse } from '../types';

/**
 * Upload a document file to a subject.
 *
 * @param file - File object to upload
 * @param subjectId - Target subject UUID
 * @returns Created document record
 */
export async function uploadDocument(
    file: File,
    subjectId: string
): Promise<Document> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('subject_id', subjectId);

    const response = await apiClient.post<Document>('/documents/upload', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return response.data;
}

/**
 * List documents, optionally filtered by subject.
 *
 * @param subjectId - Optional subject UUID filter
 * @returns Document list with total count
 */
export async function listDocuments(
    subjectId?: string
): Promise<DocumentListResponse> {
    const params = subjectId ? { subject_id: subjectId } : {};
    const response = await apiClient.get<DocumentListResponse>('/documents/list', {
        params,
    });
    return response.data;
}

/**
 * Get a single document by ID.
 *
 * @param documentId - Document UUID
 * @returns Document details
 */
export async function getDocument(documentId: string): Promise<Document> {
    const response = await apiClient.get<Document>(`/documents/${documentId}`);
    return response.data;
}

/**
 * Delete a document by ID.
 *
 * @param documentId - Document UUID to delete
 */
export async function deleteDocument(documentId: string): Promise<void> {
    await apiClient.delete(`/documents/${documentId}`);
}
