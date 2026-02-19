/**
 * Auth API service.
 *
 * Handles user registration, login, and profile retrieval.
 */

import apiClient from './client';
import type { User, AuthToken, LoginCredentials, RegisterData } from '../types';

/**
 * Register a new user account.
 *
 * @param data - Registration data (email, password, name)
 * @returns Created user profile
 */
export async function register(data: RegisterData): Promise<User> {
    const response = await apiClient.post<User>('/auth/register', data);
    return response.data;
}

/**
 * Login with email and password.
 *
 * @param credentials - Login credentials
 * @returns JWT access token
 */
export async function login(credentials: LoginCredentials): Promise<AuthToken> {
    const response = await apiClient.post<AuthToken>('/auth/login', credentials);
    return response.data;
}

/**
 * Get the current authenticated user's profile.
 *
 * @returns User profile data
 */
export async function getMe(): Promise<User> {
    const response = await apiClient.get<User>('/auth/me');
    return response.data;
}
