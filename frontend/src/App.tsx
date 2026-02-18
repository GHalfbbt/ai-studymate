/**
 * Main application component with routing configuration.
 *
 * Sets up routes for all pages within the Layout wrapper.
 * Unauthenticated routes (login/register) are outside the layout.
 */

import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout/Layout';
import Dashboard from './pages/Dashboard';
import './App.css';

/**
 * Placeholder page component for features not yet implemented.
 * Used for Day 2-5 pages to show they exist in navigation.
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

export default function App() {
  return (
    <Routes>
      {/* Authenticated routes (inside Layout with sidebar) */}
      <Route element={<Layout />}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/study" element={<ComingSoon title="Study Chat (RAG)" />} />
        <Route path="/exams" element={<ComingSoon title="Exam Generation" />} />
        <Route path="/flashcards" element={<ComingSoon title="Flashcards" />} />
        <Route path="/voice" element={<ComingSoon title="Voice Practice" />} />
        <Route path="/analytics" element={<ComingSoon title="Analytics" />} />
        <Route path="/settings" element={<ComingSoon title="Settings" />} />
      </Route>

      {/* Public routes (will be implemented in Day 2) */}
      <Route path="/login" element={<ComingSoon title="Login" />} />
      <Route path="/register" element={<ComingSoon title="Register" />} />

      {/* Default redirect */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
