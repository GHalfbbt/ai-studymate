/**
 * RAG (Retrieval-Augmented Generation) API service.
 * 
 * Handles queries to the AI study assistant.
 */

import apiClient from './client';
import type { RAGQuery, RAGResponse } from '../types';

/**
 * Send a question to the AI study assistant.
 * 
 * @param query - Query configuration (question, subject filter, etc.)
 * @returns AI response with grounding sources
 */
export async function queryRAG(query: RAGQuery): Promise<RAGResponse> {
    const response = await apiClient.post<RAGResponse>('/rag/query', query);
    return response.data;
}

/**
 * Check the status of the RAG pipeline components.
 */
export async function getRAGStatus(): Promise<{
    service: string;
    status: string;
    components: Record<string, boolean>;
}> {
    const response = await apiClient.get('/rag/status');
    return response.data;
}
