/**
 * Sidebar navigation component.
 *
 * Provides navigation links to all major sections of the app.
 * Includes workspace/course/subject context selection.
 */

import { NavLink } from 'react-router-dom';

// Navigation icon components (using unicode/emoji for MVP)
const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: '🏠' },
    { path: '/study', label: 'Study', icon: '💬' },
    { path: '/exams', label: 'Exams', icon: '📝' },
    { path: '/flashcards', label: 'Flashcards', icon: '🃏' },
    { path: '/voice', label: 'Voice', icon: '🎤' },
    { path: '/analytics', label: 'Analytics', icon: '📊' },
];

interface SidebarProps {
    /** Whether the sidebar is collapsed */
    isCollapsed?: boolean;
}

export default function Sidebar({ isCollapsed = false }: SidebarProps) {
    return (
        <aside
            className={`fixed left-0 top-0 h-screen glass-strong z-40 flex flex-col transition-all duration-300 ${isCollapsed ? 'w-[72px]' : 'w-[260px]'
                }`}
        >
            {/* Logo / Brand */}
            <div className="flex items-center gap-3 px-5 py-6 border-b border-primary-500/10">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center text-white font-bold text-lg flex-shrink-0">
                    S
                </div>
                {!isCollapsed && (
                    <div className="animate-fade-in">
                        <h1 className="text-lg font-bold gradient-text">StudyMate</h1>
                        <p className="text-xs text-surface-200/40">AI-Powered Learning</p>
                    </div>
                )}
            </div>

            {/* Navigation Links */}
            <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
                {navItems.map((item) => (
                    <NavLink
                        key={item.path}
                        to={item.path}
                        className={({ isActive }) =>
                            `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${isActive
                                ? 'bg-primary-500/15 text-primary-300 shadow-lg shadow-primary-500/5'
                                : 'text-surface-200/60 hover:text-surface-100 hover:bg-surface-800/50'
                            }`
                        }
                    >
                        <span className="text-lg flex-shrink-0">{item.icon}</span>
                        {!isCollapsed && (
                            <span className="animate-fade-in">{item.label}</span>
                        )}
                    </NavLink>
                ))}
            </nav>

            {/* Bottom Section */}
            <div className="p-4 border-t border-primary-500/10">
                <NavLink
                    to="/settings"
                    className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-surface-200/40 hover:text-surface-100 hover:bg-surface-800/50 transition-all"
                >
                    <span className="text-lg">⚙️</span>
                    {!isCollapsed && <span>Settings</span>}
                </NavLink>
            </div>
        </aside>
    );
}
