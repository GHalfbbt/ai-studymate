/**
 * Document API service.
 * Supports uploading to any hierarchy level: workspace, course, subject, or topic.
 */

import apiClient from './client';
import type { Document, DocumentListResponse } from '../types';

interface UploadTarget {
    workspace_id?: string;
    course_id?: string;
    subject_id?: string;
    topic_id?: string;
}

/**
 * Upload a document to any hierarchy level.
 */
export async function uploadDocument(file: File, target: UploadTarget): Promise<Document> {
    const formData = new FormData();
    formData.append('file', file);
    if (target.workspace_id) formData.append('workspace_id', target.workspace_id);
    if (target.course_id) formData.append('course_id', target.course_id);
    if (target.subject_id) formData.append('subject_id', target.subject_id);
    if (target.topic_id) formData.append('topic_id', target.topic_id);

    const response = await apiClient.post<Document>('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
}

/**
 * List documents with optional hierarchy filters.
 */
export async function listDocuments(filters?: {
    workspace_id?: string;
    course_id?: string;
    subject_id?: string;
    topic_id?: string;
}): Promise<DocumentListResponse> {
    const response = await apiClient.get<DocumentListResponse>('/documents/list', {
        params: filters || {},
    });
    return response.data;
}

export async function getDocument(documentId: string): Promise<Document> {
    const response = await apiClient.get<Document>(`/documents/${documentId}`);
    return response.data;
}

export async function deleteDocument(documentId: string): Promise<void> {
    await apiClient.delete(`/documents/${documentId}`);
}
