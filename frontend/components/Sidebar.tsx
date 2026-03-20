'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface NavItem {
  icon: string;
  label: string;
  href: string;
}

const navItems: NavItem[] = [
  { icon: '🔍', label: 'Legal Research', href: '/dashboard/research' },
  { icon: '📄', label: 'Contract Review', href: '/dashboard/contracts' },
  { icon: '📚', label: 'Section Search', href: '/dashboard/sections' },
  { icon: '⚖️', label: 'Case Law', href: '/dashboard/cases' },
  { icon: '📊', label: 'Recent Queries', href: '/dashboard/history' },
  { icon: '⚙️', label: 'Settings', href: '/dashboard/settings' },
];

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();

  return (
    <aside
      className={`fixed left-0 top-0 h-screen bg-[#1F3864] text-white transition-all duration-300 flex flex-col ${
        collapsed ? 'w-16' : 'w-64'
      }`}
    >
      {/* Logo */}
      <div className="p-6 border-b border-white/10">
        {!collapsed ? (
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight">
              LexAI<span className="text-[#C8A951]">.</span>
            </h1>
          </div>
        ) : (
          <div className="flex justify-center">
            <span className="text-2xl font-bold text-[#C8A951]">L</span>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-6 overflow-y-auto">
        <ul className="space-y-1 px-3">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-[#2E5499] text-white'
                      : 'text-white/70 hover:bg-white/5 hover:text-white'
                  }`}
                  title={collapsed ? item.label : ''}
                >
                  <span className="text-xl">{item.icon}</span>
                  {!collapsed && (
                    <span className="font-medium text-sm">{item.label}</span>
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Collapse Button */}
      <div className="p-3 border-t border-white/10">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 text-white/70 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <span className="text-lg">{collapsed ? '→' : '←'}</span>
          {!collapsed && <span className="text-sm">Collapse</span>}
        </button>
      </div>

      {/* User */}
      <div className="p-4 border-t border-white/10">
        {!collapsed ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-[#C8A951] flex items-center justify-center text-[#1F3864] font-bold text-sm">
                U
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">User</p>
                <p className="text-xs text-white/50">Advocate</p>
              </div>
            </div>
            <button className="w-full text-left px-3 py-1.5 text-xs text-white/70 hover:text-white hover:bg-white/5 rounded transition-colors">
              Logout
            </button>
          </div>
        ) : (
          <button
            className="w-full flex justify-center py-2 text-white/70 hover:text-white"
            title="Logout"
          >
            <span className="text-lg">⏻</span>
          </button>
        )}
      </div>
    </aside>
  );
}
