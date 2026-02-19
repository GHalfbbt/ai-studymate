/**
 * Login page component.
 *
 * Provides email/password authentication form.
 * Redirects to dashboard on successful login.
 */

import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { login as apiLogin } from '../api/auth';
import { getMe } from '../api/auth';

export default function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const { setAuth } = useAuthStore();
    const navigate = useNavigate();

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            // 1. Login to get token
            const tokenData = await apiLogin({ email, password });

            // 2. Get user profile with the token
            localStorage.setItem('access_token', tokenData.access_token);
            const user = await getMe();

            // 3. Set auth state
            setAuth(user, tokenData.access_token);

            // 4. Redirect to dashboard
            navigate('/dashboard', { replace: true });
        } catch (err: any) {
            const message = err?.response?.data?.detail || 'Invalid email or password';
            setError(message);
            localStorage.removeItem('access_token');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center relative" style={{ padding: '1rem' }}>
            {/* Background decorations */}
            <div className="bg-glow bg-glow-primary" />
            <div className="bg-glow bg-glow-accent" />

            <div className="card w-full relative z-10" style={{ maxWidth: 440, padding: '2.5rem' }}>
                {/* Logo */}
                <div className="text-center" style={{ marginBottom: '2rem' }}>
                    <div
                        className="mx-auto rounded-2xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center text-white font-bold"
                        style={{ width: 56, height: 56, fontSize: '1.5rem', marginBottom: '1rem' }}
                    >
                        S
                    </div>
                    <h1 className="gradient-text font-bold" style={{ fontSize: '1.75rem' }}>
                        Welcome back
                    </h1>
                    <p style={{ color: 'rgba(226,232,240,0.5)', marginTop: '0.5rem' }}>
                        Sign in to your StudyMate account
                    </p>
                </div>

                {/* Error message */}
                {error && (
                    <div className="badge-danger" style={{
                        padding: '0.75rem 1rem',
                        borderRadius: '0.75rem',
                        marginBottom: '1.5rem',
                        display: 'block',
                        textAlign: 'center',
                        fontSize: '0.875rem',
                    }}>
                        {error}
                    </div>
                )}

                {/* Login form */}
                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.875rem', color: 'rgba(226,232,240,0.7)', marginBottom: '0.5rem' }}>
                            Email
                        </label>
                        <input
                            id="login-email"
                            type="email"
                            className="input"
                            placeholder="you@example.com"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                            autoFocus
                        />
                    </div>

                    <div>
                        <label style={{ display: 'block', fontSize: '0.875rem', color: 'rgba(226,232,240,0.7)', marginBottom: '0.5rem' }}>
                            Password
                        </label>
                        <input
                            id="login-password"
                            type="password"
                            className="input"
                            placeholder="••••••••"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            minLength={8}
                        />
                    </div>

                    <button
                        id="login-submit"
                        type="submit"
                        className="btn-primary"
                        disabled={loading}
                        style={{
                            width: '100%',
                            justifyContent: 'center',
                            padding: '0.75rem',
                            fontSize: '1rem',
                            marginTop: '0.5rem',
                        }}
                    >
                        {loading ? '⏳ Signing in...' : '🔐 Sign In'}
                    </button>
                </form>

                {/* Register link */}
                <p style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: '0.875rem', color: 'rgba(226,232,240,0.5)' }}>
                    Don't have an account?{' '}
                    <Link to="/register" className="gradient-text font-semibold" style={{ textDecoration: 'none' }}>
                        Sign up
                    </Link>
                </p>
            </div>
        </div>
    );
}
