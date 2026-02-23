/**
 * Main application component with routing configuration.
 *
 * Sets up routes for all pages within the Layout wrapper.
 * Authenticated routes require login, public routes don't.
 */

import { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout/Layout';
import Dashboard from './pages/Dashboard';
import Chat from './pages/Chat';
import Workspaces from './pages/Workspaces';
import Exams from './pages/Exams';
import Flashcards from './pages/Flashcards';
import Analytics from './pages/Analytics';
import Settings from './pages/Settings';
import Login from './pages/Login';
import Register from './pages/Register';
import { useAuthStore } from './store/authStore';
import { getMe } from './api/auth';
import './App.css';

/**
 * Placeholder page for features not yet implemented.
 */
function ComingSoon({ title }: { title: string }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] animate-fade-in">
      <div className="text-center">
        <span className="text-7xl block mb-6 animate-pulse-soft">🚧</span>
        <h2 className="text-2xl font-bold gradient-text mb-3">{title}</h2>
        <p className="text-surface-200/40 text-lg">
          Coming soon — this feature will be implemented in upcoming days
        </p>
      </div>
    </div>
  );
}

/**
 * Auth guard: redirects to /login if not authenticated.
 */
function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuthStore();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center animate-fade-in">
          <span className="text-5xl block mb-4">⏳</span>
          <p style={{ color: 'rgba(226,232,240,0.5)' }}>Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

export default function App() {
  const { token, setAuth, setLoading, logout } = useAuthStore();

  // On mount: try to restore session from stored token
  useEffect(() => {
    const restoreSession = async () => {
      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const user = await getMe();
        setAuth(user, token);
      } catch {
        // Token invalid or expired
        logout();
      }
    };

    restoreSession();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Routes>
      {/* Authenticated routes (inside Layout with sidebar) */}
      <Route element={<RequireAuth><Layout /></RequireAuth>}>
        <Route path="/workspaces" element={<Workspaces />} />
        <Route path="/dashboard" element={<Navigate to="/workspaces" replace />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/exams" element={<Exams />} />
        <Route path="/flashcards" element={<Flashcards />} />
        <Route path="/voice" element={<ComingSoon title="Voice Practice" />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/settings" element={<Settings />} />
      </Route>

      {/* Public routes (no auth required) */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Default redirect */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
