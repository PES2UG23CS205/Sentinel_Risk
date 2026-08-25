import type { Metadata } from 'next';
import './globals.css';
import Sidebar from '@/components/Sidebar';
import Header from '@/components/Header';

export const metadata: Metadata = {
  title: 'SentinelRisk — Payment Risk Intelligence',
  description: 'Defense-only payment risk intelligence system for detecting suspicious transactions and supporting safe, auditable risk decisions.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="sr-layout">
          <Sidebar />
          <main className="sr-main">
            <Header />
            <div className="sr-content">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
