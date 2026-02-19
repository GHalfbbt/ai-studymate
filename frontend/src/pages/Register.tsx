/**
 * Register page component.
 *
 * Provides user registration form with email, password, and name.
 * Redirects to login on successful registration.
 */

import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { register as apiRegister } from '../api/auth';

export default function Register() {
    const [fullName, setFullName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError('');

        // Client-side validation
        if (password !== confirmPassword) {
            setError('Passwords do not match');
            return;
        }

        setLoading(true);
        try {
            await apiRegister({ email, password, full_name: fullName || undefined });
            // Redirect to login after successful registration
            navigate('/login', { replace: true });
        } catch (err: any) {
            const message = err?.response?.data?.detail || 'Registration failed. Please try again.';
            setError(message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center relative" style={{ padding: '1rem' }}>
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
                        Create account
                    </h1>
                    <p style={{ color: 'rgba(226,232,240,0.5)', marginTop: '0.5rem' }}>
                        Start your AI-powered learning journey
                    </p>
                </div>

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

                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.875rem', color: 'rgba(226,232,240,0.7)', marginBottom: '0.5rem' }}>
                            Full Name (optional)
                        </label>
                        <input
                            id="register-name"
                            type="text"
                            className="input"
                            placeholder="John Doe"
                            value={fullName}
                            onChange={(e) => setFullName(e.target.value)}
                        />
                    </div>

                    <div>
                        <label style={{ display: 'block', fontSize: '0.875rem', color: 'rgba(226,232,240,0.7)', marginBottom: '0.5rem' }}>
                            Email
                        </label>
                        <input
                            id="register-email"
                            type="email"
                            className="input"
                            placeholder="you@example.com"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                        />
                    </div>

                    <div>
                        <label style={{ display: 'block', fontSize: '0.875rem', color: 'rgba(226,232,240,0.7)', marginBottom: '0.5rem' }}>
                            Password
                        </label>
                        <input
                            id="register-password"
                            type="password"
                            className="input"
                            placeholder="Minimum 8 characters"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            minLength={8}
                        />
                    </div>

                    <div>
                        <label style={{ display: 'block', fontSize: '0.875rem', color: 'rgba(226,232,240,0.7)', marginBottom: '0.5rem' }}>
                            Confirm Password
                        </label>
                        <input
                            id="register-confirm-password"
                            type="password"
                            className="input"
                            placeholder="Repeat your password"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            required
                            minLength={8}
                        />
                    </div>

                    <button
                        id="register-submit"
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
                        {loading ? '⏳ Creating account...' : '🚀 Create Account'}
                    </button>
                </form>

                <p style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: '0.875rem', color: 'rgba(226,232,240,0.5)' }}>
                    Already have an account?{' '}
                    <Link to="/login" className="gradient-text font-semibold" style={{ textDecoration: 'none' }}>
                        Sign in
                    </Link>
                </p>
            </div>
        </div>
    );
}
