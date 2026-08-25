'use client';

import { useEffect, useState } from 'react';

type Status = 'checking' | 'connected' | 'disconnected';

interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export default function BackendStatus() {
  const [status, setStatus] = useState<Status>('checking');
  const [version, setVersion] = useState<string>('');

  useEffect(() => {
    let mounted = true;

    const checkHealth = async () => {
      try {
        const res = await fetch('http://localhost:8000/health', {
          signal: AbortSignal.timeout(5000),
        });

        if (!mounted) return;

        if (res.ok) {
          const data: HealthResponse = await res.json();
          if (data.status === 'ok') {
            setStatus('connected');
            setVersion(data.version || '');
          } else {
            setStatus('disconnected');
          }
        } else {
          setStatus('disconnected');
        }
      } catch {
        if (mounted) {
          setStatus('disconnected');
        }
      }
    };

    checkHealth();

    // Poll every 15 seconds
    const interval = setInterval(checkHealth, 15000);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const labels: Record<Status, string> = {
    checking: 'Checking backend…',
    connected: `Backend Connected${version ? ` (v${version})` : ''}`,
    disconnected: 'Backend Unavailable',
  };

  return (
    <div className={`sr-status-badge ${status}`}>
      <span className="sr-status-dot" />
      {labels[status]}
    </div>
  );
}
