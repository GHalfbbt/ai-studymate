/**
 * Authentication state management using Zustand.
 *
 * Manages user session, JWT token persistence in localStorage,
 * and provides login/logout/register actions.
 */

import { create } from 'zustand';
import type { User } from '../types';

interface AuthState {
    /** Currently authenticated user, or null if not logged in */
    user: User | null;
    /** JWT access token */
    token: string | null;
    /** Whether the auth state is being initialized (checking stored token) */
    isLoading: boolean;
    /** Whether the user is authenticated */
    isAuthenticated: boolean;

    /** Set user and token after successful login */
    setAuth: (user: User, token: string) => void;
    /** Clear auth state on logout */
    logout: () => void;
    /** Set loading state during initialization */
    setLoading: (loading: boolean) => void;
    /** Initialize auth from stored token */
    initialize: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
    user: null,
    token: localStorage.getItem('access_token'),
    isLoading: true,
    isAuthenticated: !!localStorage.getItem('access_token'),

    setAuth: (user: User, token: string) => {
        localStorage.setItem('access_token', token);
        set({
            user,
            token,
            isAuthenticated: true,
            isLoading: false,
        });
    },

    logout: () => {
        localStorage.removeItem('access_token');
        set({
            user: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,
        });
    },

    setLoading: (loading: boolean) => {
        set({ isLoading: loading });
    },

    initialize: () => {
        const token = localStorage.getItem('access_token');
        set({
            token,
            isAuthenticated: !!token,
            isLoading: false,
        });
    },
}));
