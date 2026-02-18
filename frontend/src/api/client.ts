/**
 * Axios HTTP client instance with authentication interceptor.
 *
 * Automatically attaches JWT token to requests and handles
 * 401 responses by clearing auth state and redirecting to login.
 */

import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios';

// Base API URL from environment variable
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Pre-configured Axios instance for API communication.
 *
 * Features:
 * - Base URL set to backend API
 * - Automatic JWT token attachment
 * - 401 response handling (redirect to login)
 * - JSON content type by default
 */
const apiClient: AxiosInstance = axios.create({
    baseURL: `${API_URL}/api/v1`,
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 30000, // 30 second timeout
});

// Request interceptor: Attach JWT token to every request
apiClient.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
        const token = localStorage.getItem('access_token');
        if (token && config.headers) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Response interceptor: Handle authentication errors
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            // Token expired or invalid - clear auth and redirect to login
            localStorage.removeItem('access_token');
            // Only redirect if not already on login page
            if (window.location.pathname !== '/login') {
                window.location.href = '/login';
            }
        }
        return Promise.reject(error);
    }
);

export default apiClient;
