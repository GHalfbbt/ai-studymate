/**
 * Header component with user info and search.
 *
 * Displays the current page context, search bar, and user menu.
 */

import { useAuthStore } from '../../store/authStore';

interface HeaderProps {
    /** Current page title */
    title?: string;
    /** Toggle sidebar callback */
    onToggleSidebar?: () => void;
}

export default function Header({ title = 'Dashboard', onToggleSidebar }: HeaderProps) {
    const { user, logout } = useAuthStore();

    return (
        <header className="glass-strong sticky top-0 z-30 px-6 py-4 flex items-center justify-between border-b border-primary-500/10">
            {/* Left - Menu toggle & Title */}
            <div className="flex items-center gap-4">
                <button
                    onClick={onToggleSidebar}
                    className="p-2 rounded-lg hover:bg-surface-800/50 transition-colors text-surface-200/60 hover:text-surface-100"
                    aria-label="Toggle sidebar"
                >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                    </svg>
                </button>
                <h2 className="text-xl font-semibold text-surface-100">{title}</h2>
            </div>

            {/* Right - User menu */}
            <div className="flex items-center gap-4">
                {/* Notification bell placeholder */}
                <button className="p-2 rounded-lg hover:bg-surface-800/50 transition-colors text-surface-200/60 hover:text-surface-100 relative">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                    </svg>
                    <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-accent-500 rounded-full" />
                </button>

                {/* User profile */}
                <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center text-white font-semibold text-sm">
                        {user?.full_name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || '?'}
                    </div>
                    <div className="hidden md:block">
                        <p className="text-sm font-semibold text-surface-100">
                            {user?.full_name || 'User'}
                        </p>
                        <p className="text-xs text-surface-200/50">{user?.email || ''}</p>
                    </div>
                    <button
                        onClick={logout}
                        className="px-3 py-1.5 rounded-lg hover:bg-danger-500/10 text-surface-200/50 hover:text-danger-400 transition-colors font-medium text-xs"
                        title="Logout"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                        </svg>
                    </button>
                </div>
            </div>
        </header>
    );
}
