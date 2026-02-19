/**
 * Workspace API service.
 * Handles listing, creation, and deletion of workspaces, courses, and subjects.
 */
import apiClient from './client';
import type { Workspace, Course, Subject } from '../types';

// ── Workspaces ──────────────────────────────────────────
export async function listWorkspaces(): Promise<Workspace[]> {
    const res = await apiClient.get<Workspace[]>('/workspaces/');
    return res.data;
}

export async function createWorkspace(name: string, description?: string): Promise<Workspace> {
    const res = await apiClient.post<Workspace>('/workspaces/', { name, description });
    return res.data;
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

// ── Subjects ────────────────────────────────────────────
export async function listSubjects(workspaceId: string, courseId: string): Promise<Subject[]> {
    const res = await apiClient.get<Subject[]>(`/workspaces/${workspaceId}/courses/${courseId}/subjects`);
    return res.data;
}

export async function createSubject(workspaceId: string, courseId: string, name: string, color: string): Promise<Subject> {
    const res = await apiClient.post<Subject>(`/workspaces/${workspaceId}/courses/${courseId}/subjects`, { name, color });
    return res.data;
}
