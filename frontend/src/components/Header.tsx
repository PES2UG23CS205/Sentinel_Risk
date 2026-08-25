'use client';

import BackendStatus from '@/components/BackendStatus';

export default function Header() {
  return (
    <header className="sr-header">
      <div className="sr-header-title">
        Defense-only Payment Risk Intelligence
      </div>
      <div className="sr-header-actions">
        <BackendStatus />
      </div>
    </header>
  );
}
