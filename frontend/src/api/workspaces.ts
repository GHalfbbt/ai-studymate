/**
 * Workspace hierarchy API service.
 * Full CRUD for Workspaces → Courses → Subjects → Topics.
 */
import apiClient from './client';
import type { Workspace, Course, Subject, Topic } from '../types';

// ── Workspaces ──────────────────────────────────────────
export async function listWorkspaces(): Promise<Workspace[]> {
    const res = await apiClient.get<Workspace[]>('/workspaces/');
    return res.data;
}

export async function createWorkspace(name: string, description?: string): Promise<Workspace> {
    const res = await apiClient.post<Workspace>('/workspaces/', { name, description });
    return res.data;
}

export async function updateWorkspace(id: string, data: { name?: string; description?: string }): Promise<Workspace> {
    const res = await apiClient.patch<Workspace>(`/workspaces/${id}`, data);
    return res.data;
}

export async function deleteWorkspace(id: string): Promise<void> {
    await apiClient.delete(`/workspaces/${id}`);
}

// ── Courses ─────────────────────────────────────────────
export async function listCourses(workspaceId: string): Promise<Course[]> {
    const res = await apiClient.get<Course[]>(`/workspaces/${workspaceId}/courses`);
    return res.data;
}

export async function createCourse(workspaceId: string, name: string): Promise<Course> {
    const res = await apiClient.post<Course>(`/workspaces/${workspaceId}/courses`, { name });
    return res.data;
}

export async function updateCourse(wsId: string, courseId: string, data: { name?: string; position?: number }): Promise<Course> {
    const res = await apiClient.patch<Course>(`/workspaces/${wsId}/courses/${courseId}`, data);
    return res.data;
}

export async function deleteCourse(wsId: string, courseId: string): Promise<void> {
    await apiClient.delete(`/workspaces/${wsId}/courses/${courseId}`);
}

// ── Subjects ────────────────────────────────────────────
export async function listSubjects(wsId: string, courseId: string): Promise<Subject[]> {
    const res = await apiClient.get<Subject[]>(`/workspaces/${wsId}/courses/${courseId}/subjects`);
    return res.data;
}

export async function createSubject(wsId: string, courseId: string, name: string, color: string): Promise<Subject> {
    const res = await apiClient.post<Subject>(`/workspaces/${wsId}/courses/${courseId}/subjects`, { name, color });
    return res.data;
}

export async function updateSubject(wsId: string, courseId: string, subjectId: string, data: { name?: string; color?: string; position?: number }): Promise<Subject> {
    const res = await apiClient.patch<Subject>(`/workspaces/${wsId}/courses/${courseId}/subjects/${subjectId}`, data);
    return res.data;
}

export async function deleteSubject(wsId: string, courseId: string, subjectId: string): Promise<void> {
    await apiClient.delete(`/workspaces/${wsId}/courses/${courseId}/subjects/${subjectId}`);
}

// ── Topics ──────────────────────────────────────────────
export async function listTopics(wsId: string, courseId: string, subjectId: string): Promise<Topic[]> {
    const res = await apiClient.get<Topic[]>(`/workspaces/${wsId}/courses/${courseId}/subjects/${subjectId}/topics`);
    return res.data;
}

export async function createTopic(wsId: string, courseId: string, subjectId: string, name: string): Promise<Topic> {
    const res = await apiClient.post<Topic>(`/workspaces/${wsId}/courses/${courseId}/subjects/${subjectId}/topics`, { name });
    return res.data;
}

export async function updateTopic(wsId: string, courseId: string, subjectId: string, topicId: string, data: { name?: string; position?: number }): Promise<Topic> {
    const res = await apiClient.patch<Topic>(`/workspaces/${wsId}/courses/${courseId}/subjects/${subjectId}/topics/${topicId}`, data);
    return res.data;
}

export async function deleteTopic(wsId: string, courseId: string, subjectId: string, topicId: string): Promise<void> {
    await apiClient.delete(`/workspaces/${wsId}/courses/${courseId}/subjects/${subjectId}/topics/${topicId}`);
}
