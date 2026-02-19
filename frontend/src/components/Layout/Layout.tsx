/**
 * Main layout wrapper component.
 *
 * Provides the sidebar + header + content area structure.
 * Responsive: sidebar is hidden on mobile and shown as overlay.
 */

import { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';

export default function Layout() {
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [isMobile, setIsMobile] = useState(false);

    // Detect screen size for responsive behavior
    useEffect(() => {
        const checkMobile = () => {
            const mobile = window.innerWidth < 1024;
            setIsMobile(mobile);
            if (mobile) {
                setSidebarCollapsed(true);
                setSidebarOpen(false);
            } else {
                setSidebarOpen(true);
            }
        };

        checkMobile();
        window.addEventListener('resize', checkMobile);
        return () => window.removeEventListener('resize', checkMobile);
    }, []);

    const handleToggleSidebar = () => {
        if (isMobile) {
            setSidebarOpen(!sidebarOpen);
        } else {
            setSidebarCollapsed(!sidebarCollapsed);
        }
    };

    const handleCloseMobileSidebar = () => {
        if (isMobile) {
            setSidebarOpen(false);
        }
    };

    // Use inline style for margin since dynamic Tailwind classes don't work
    const contentMargin = isMobile ? 0 : sidebarCollapsed ? 72 : 260;

    return (
        <div className="min-h-screen relative">
            {/* Background glow decorations */}
            <div className="bg-glow bg-glow-primary" />
            <div className="bg-glow bg-glow-accent" />

            {/* Mobile overlay backdrop */}
            {isMobile && sidebarOpen && (
                <div
                    className="fixed inset-0 bg-black/60 z-30 backdrop-blur-sm"
                    onClick={handleCloseMobileSidebar}
                />
            )}

            {/* Sidebar */}
            <Sidebar
                isCollapsed={isMobile ? false : sidebarCollapsed}
                isVisible={isMobile ? sidebarOpen : true}
                isMobile={isMobile}
                onClose={handleCloseMobileSidebar}
            />

            {/* Main content area — use inline style for dynamic margin */}
            <div
                className="min-h-screen"
                style={{
                    marginLeft: `${contentMargin}px`,
                    transition: 'margin-left 0.3s ease',
                }}
            >
                <Header onToggleSidebar={handleToggleSidebar} />

                {/* Page content - rendered by React Router */}
                <main className="p-4 md:p-6 relative z-10">
                    <Outlet />
                </main>
            </div>
        </div>
    );
}
