/**
 * Sidebar navigation component.
 *
 * Provides navigation links to all major sections of the app.
 * Responsive: slides in/out on mobile, collapses on desktop.
 */

import { NavLink } from 'react-router-dom';

// Navigation items with paths, labels and icons
const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: '🏠' },
    { path: '/study', label: 'Study', icon: '💬' },
    { path: '/exams', label: 'Exams', icon: '📝' },
    { path: '/flashcards', label: 'Flashcards', icon: '🃏' },
    { path: '/voice', label: 'Voice', icon: '🎤' },
    { path: '/analytics', label: 'Analytics', icon: '📊' },
];

interface SidebarProps {
    isCollapsed?: boolean;
    isVisible?: boolean;
    isMobile?: boolean;
    onClose?: () => void;
}

export default function Sidebar({
    isCollapsed = false,
    isVisible = true,
    isMobile = false,
    onClose,
}: SidebarProps) {
    const sidebarWidth = isCollapsed ? 72 : 260;

    return (
        <aside
            className="fixed left-0 top-0 h-screen glass-strong z-40 flex flex-col"
            style={{
                width: `${sidebarWidth}px`,
                transform: isMobile ? (isVisible ? 'translateX(0)' : 'translateX(-100%)') : 'translateX(0)',
                transition: 'width 0.3s ease, transform 0.3s ease',
            }}
        >
            {/* Logo / Brand */}
            <div className="flex items-center gap-3 px-5 py-6 border-b border-primary-500/10">
                <div
                    className="flex-shrink-0 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center text-white font-bold"
                    style={{ width: 40, height: 40, fontSize: '1.125rem' }}
                >
                    S
                </div>
                {!isCollapsed && (
                    <div className="animate-fade-in flex-1">
                        <h1 className="font-bold gradient-text" style={{ fontSize: '1.125rem' }}>
                            StudyMate
                        </h1>
                        <p style={{ fontSize: '0.75rem', color: 'rgba(226,232,240,0.4)' }}>
                            AI-Powered Learning
                        </p>
                    </div>
                )}
                {/* Close button for mobile */}
                {isMobile && (
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg hover:bg-surface-800/50"
                        style={{ color: 'rgba(226,232,240,0.6)', fontSize: '1.25rem' }}
                        aria-label="Close sidebar"
                    >
                        ✕
                    </button>
                )}
            </div>

            {/* Navigation Links */}
            <nav className="flex-1 py-4 px-3 overflow-y-auto" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {navItems.map((item) => (
                    <NavLink
                        key={item.path}
                        to={item.path}
                        onClick={isMobile ? onClose : undefined}
                        className={({ isActive }) =>
                            `flex items-center gap-3 rounded-xl font-medium transition-all duration-200 ${isActive
                                ? 'bg-primary-500/15 text-primary-300'
                                : 'hover:bg-surface-800/50'
                            }`
                        }
                        style={({ isActive }) => ({
                            padding: '12px 14px',
                            fontSize: '0.9375rem',
                            color: isActive ? undefined : 'rgba(226,232,240,0.6)',
                        })}
                    >
                        <span style={{ fontSize: '1.25rem', flexShrink: 0 }}>{item.icon}</span>
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
                    onClick={isMobile ? onClose : undefined}
                    className="flex items-center gap-3 rounded-xl hover:bg-surface-800/50 transition-all"
                    style={{
                        padding: '12px 14px',
                        fontSize: '0.9375rem',
                        color: 'rgba(226,232,240,0.4)',
                    }}
                >
                    <span style={{ fontSize: '1.25rem' }}>⚙️</span>
                    {!isCollapsed && <span>Settings</span>}
                </NavLink>
            </div>
        </aside>
    );
}
