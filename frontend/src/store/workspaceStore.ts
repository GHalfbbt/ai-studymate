/**
 * Workspace & organization hierarchy state management.
 *
 * Manages the current workspace, course, and subject selection
 * for navigation and context-aware API calls.
 */

import { create } from 'zustand';
import type { Workspace, Course, Subject } from '../types';

interface WorkspaceState {
    /** All workspaces for the current user */
    workspaces: Workspace[];
    /** Currently selected workspace */
    currentWorkspace: Workspace | null;
    /** Courses in the current workspace */
    courses: Course[];
    /** Currently selected course */
    currentCourse: Course | null;
    /** Subjects in the current course */
    subjects: Subject[];
    /** Currently selected subject */
    currentSubject: Subject | null;
    /** Loading state */
    isLoading: boolean;

    /** Set all workspaces */
    setWorkspaces: (workspaces: Workspace[]) => void;
    /** Select a workspace and clear child selections */
    selectWorkspace: (workspace: Workspace) => void;
    /** Set courses for the current workspace */
    setCourses: (courses: Course[]) => void;
    /** Select a course and clear subject selection */
    selectCourse: (course: Course) => void;
    /** Set subjects for the current course */
    setSubjects: (subjects: Subject[]) => void;
    /** Select a subject */
    selectSubject: (subject: Subject) => void;
    /** Set loading state */
    setLoading: (loading: boolean) => void;
    /** Reset all state */
    reset: () => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
    workspaces: [],
    currentWorkspace: null,
    courses: [],
    currentCourse: null,
    subjects: [],
    currentSubject: null,
    isLoading: false,

    setWorkspaces: (workspaces) => set({ workspaces }),

    selectWorkspace: (workspace) =>
        set({
            currentWorkspace: workspace,
            courses: [],
            currentCourse: null,
            subjects: [],
            currentSubject: null,
        }),

    setCourses: (courses) => set({ courses }),

    selectCourse: (course) =>
        set({
            currentCourse: course,
            subjects: [],
            currentSubject: null,
        }),

    setSubjects: (subjects) => set({ subjects }),

    selectSubject: (subject) => set({ currentSubject: subject }),

    setLoading: (loading) => set({ isLoading: loading }),

    reset: () =>
        set({
            workspaces: [],
            currentWorkspace: null,
            courses: [],
            currentCourse: null,
            subjects: [],
            currentSubject: null,
            isLoading: false,
        }),
}));
