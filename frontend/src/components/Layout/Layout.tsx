/**
 * Main layout wrapper component.
 *
 * Provides the sidebar + header + content area structure
 * for authenticated pages. Includes background decorations.
 */

import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';

export default function Layout() {
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

    return (
        <div className="min-h-screen relative">
            {/* Background glow decorations */}
            <div className="bg-glow bg-glow-primary" />
            <div className="bg-glow bg-glow-accent" />

            {/* Sidebar */}
            <Sidebar isCollapsed={sidebarCollapsed} />

            {/* Main content area */}
            <div
                className={`layout-transition min-h-screen ${sidebarCollapsed ? 'ml-[72px]' : 'ml-[260px]'
                    }`}
            >
                <Header
                    onToggleSidebar={() => setSidebarCollapsed(!sidebarCollapsed)}
                />

                {/* Page content - rendered by React Router */}
                <main className="p-6 relative z-10">
                    <Outlet />
                </main>
            </div>
        </div>
    );
}
