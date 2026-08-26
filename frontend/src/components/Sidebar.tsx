'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const navItems = [
  { href: '/', label: 'Risk Overview', icon: '◈' },
  { href: '/live-feed', label: 'Live Risk Feed', icon: '◉' },
  { href: '/data-lab', label: 'Data Lab Assessment', icon: '📥' },
  { href: '/operations', label: 'Operations & Health', icon: '⚙' },
  { href: '/review-queue', label: 'Review Queue', icon: '☰' },
  { href: '/incidents', label: 'Incidents', icon: '⚡' },
  { href: '/model-evaluation', label: 'Model Evaluation', icon: '◧' },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sr-sidebar">
      {/* Brand */}
      <div className="sr-sidebar-header">
        <div className="sr-sidebar-brand">
          <div className="sr-sidebar-logo">S</div>
          <div>
            <div className="sr-sidebar-title">SentinelRisk</div>
            <div className="sr-sidebar-subtitle">Payment Risk Intelligence</div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="sr-sidebar-nav">
        <div className="sr-sidebar-section-label">Monitoring</div>
        {navItems.slice(0, 2).map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`sr-nav-link ${pathname === item.href ? 'active' : ''}`}
          >
            <span className="sr-nav-icon">{item.icon}</span>
            {item.label}
          </Link>
        ))}

        <div className="sr-sidebar-section-label">Operations</div>
        {navItems.slice(2, 5).map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`sr-nav-link ${pathname === item.href ? 'active' : ''}`}
          >
            <span className="sr-nav-icon">{item.icon}</span>
            {item.label}
          </Link>
        ))}

        <div className="sr-sidebar-section-label">Intelligence</div>
        {navItems.slice(5).map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`sr-nav-link ${pathname === item.href ? 'active' : ''}`}
          >
            <span className="sr-nav-icon">{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </nav>

      {/* Footer */}
      <div className="sr-sidebar-footer">
        <div className="sr-stage-indicator">Stage 1 — Foundation</div>
        <div className="sr-sidebar-version" style={{ marginTop: '8px' }}>
          v0.1.0
        </div>
      </div>
    </aside>
  );
}
