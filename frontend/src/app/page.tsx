'use client';

import { useEffect, useState } from 'react';

interface DatasetMetrics {
  num_merchants: number;
  num_customers: number;
  num_devices: number;
  num_payment_instruments: number;
  num_transactions: number;
  num_disputes: number;
  fraud_transactions_ground_truth: number;
  fraud_transactions_observed: number;
  fraud_prevalence: string;
  account_takeover_count: number;
  card_testing_count: number;
  coordinated_ring_count: number;
}

interface DatasetResponse {
  status: string;
  dataset_type: string;
  disclaimer: string;
  is_seeded: boolean;
  metrics: DatasetMetrics;
}

interface ExternalHandbookMeta {
  available: boolean;
  dataset_name: string;
  dataset_type: string;
  description: string;
  total_files: number;
  total_rows: number;
  total_fraud: number;
  fraud_rate_pct: number;
  date_range: { min: string; max: string };
  columns: string[];
  component_compatibility: Record<string, string>;
}

export default function RiskOverview() {
  const [dataset, setDataset] = useState<DatasetResponse | null>(null);
  const [handbookMeta, setHandbookMeta] = useState<ExternalHandbookMeta | null>(null);
  const [activeDataSource, setActiveDataSource] = useState<'SYNTHETIC' | 'HANDBOOK'>('SYNTHETIC');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    const fetchDatasetStatus = async () => {
      try {
        const [resSynthetic, resHandbook] = await Promise.all([
          fetch('http://localhost:8000/dataset/status', { signal: AbortSignal.timeout(4000) }),
          fetch('http://localhost:8000/stream/external/fraud-handbook/metadata', { signal: AbortSignal.timeout(4000) }),
        ]);

        if (resSynthetic.ok && mounted) {
          const data = await resSynthetic.json();
          setDataset(data);
        }
        if (resHandbook.ok && mounted) {
          const hbData = await resHandbook.json();
          setHandbookMeta(hbData);
        }
      } catch {
        // Backend might not be running or still loading
      } finally {
        if (mounted) setLoading(false);
      }
    };

    fetchDatasetStatus();
    const interval = setInterval(fetchDatasetStatus, 15000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const modules = [
    {
      title: 'Risk Scoring Engine',
      description: 'ML-based transaction risk scoring with calibrated probability outputs (LightGBM & Logistic Regression).',
      icon: '◈',
      stage: 'Stage 3-5',
    },
    {
      title: 'Graph Detection',
      description: 'NetworkX-based analysis of shared devices and payment instruments to detect coordinated fraud rings.',
      icon: '⬡',
      stage: 'Stage 6',
    },
    {
      title: 'Policy Engine',
      description: 'Configurable rule-based decisions and deterministic thresholds with complete audit logs.',
      icon: '⊞',
      stage: 'Stage 7',
    },
    {
      title: 'Investigation Agent',
      description: 'Autonomous multi-hop evidence gathering and structured investigation dossiers using LangGraph.',
      icon: '⊘',
      stage: 'Stage 8',
    },
    {
      title: 'Real-Time Pipeline',
      description: 'Sub-millisecond scoring service with idempotency, latency profiling, and fail-safe resilience.',
      icon: '⚡',
      stage: 'Stage 9',
    },
    {
      title: 'Operations Console & Replay',
      description: 'Multi-source real-time replay across synthetic world and Fraud Detection Handbook dataset.',
      icon: '☰',
      stage: 'Stage 10-11',
    },
  ];

  return (
    <>
      <div className="sr-page-header">
        <h1 className="sr-page-title">Risk Overview & Data Sources</h1>
        <p className="sr-page-description">
          Payment risk intelligence and multi-source transaction simulation ecosystem
        </p>
      </div>

      {/* Data Source Selector Tabs */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px' }}>
        <button
          onClick={() => setActiveDataSource('SYNTHETIC')}
          style={{
            background: activeDataSource === 'SYNTHETIC' ? '#1e3a8a' : 'var(--sr-bg-secondary)',
            borderColor: activeDataSource === 'SYNTHETIC' ? '#3b82f6' : 'var(--sr-border)',
            color: activeDataSource === 'SYNTHETIC' ? '#fff' : 'var(--sr-text-secondary)',
            padding: '8px 16px',
            borderRadius: '6px',
            border: '1px solid',
            fontWeight: 600,
            fontSize: '0.85rem',
            cursor: 'pointer',
          }}
        >
          ⚡ SentinelRisk Synthetic (Stage 1-10)
        </button>
        <button
          onClick={() => setActiveDataSource('HANDBOOK')}
          style={{
            background: activeDataSource === 'HANDBOOK' ? '#1e3a8a' : 'var(--sr-bg-secondary)',
            borderColor: activeDataSource === 'HANDBOOK' ? '#3b82f6' : 'var(--sr-border)',
            color: activeDataSource === 'HANDBOOK' ? '#fff' : 'var(--sr-text-secondary)',
            padding: '8px 16px',
            borderRadius: '6px',
            border: '1px solid',
            fontWeight: 600,
            fontSize: '0.85rem',
            cursor: 'pointer',
          }}
        >
          📚 Fraud Detection Handbook (Stage 11 External)
        </button>
      </div>

      {/* SYNTHETIC WORLD BANNER */}
      {activeDataSource === 'SYNTHETIC' && (
        <div className="sr-card" style={{ marginBottom: '32px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <h2 style={{ fontSize: '1.15rem', fontWeight: 600, color: 'var(--sr-text-primary)' }}>
                  Synthetic Simulation Ecosystem
                </h2>
                <span className="sr-stage-indicator" style={{ background: 'rgba(34, 197, 94, 0.12)', color: '#4ade80', borderColor: 'rgba(34, 197, 94, 0.25)' }}>
                  Ground Truth Active
                </span>
              </div>
              <p style={{ fontSize: '0.82rem', color: 'var(--sr-text-muted)', marginTop: '4px' }}>
                Deterministic 6-month simulated payments world (Seed: 42)
              </p>
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--sr-text-secondary)', background: 'var(--sr-bg-secondary)', padding: '6px 14px', borderRadius: '6px', border: '1px solid var(--sr-border)' }}>
              Status: {dataset?.is_seeded ? 'Populated in SQLite' : 'Ready'}
            </div>
          </div>

          {dataset?.is_seeded ? (
            <>
              {/* Primary KPI Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '14px', marginBottom: '18px' }}>
                <div style={{ background: 'var(--sr-bg-secondary)', padding: '16px', borderRadius: '8px', border: '1px solid var(--sr-border-subtle)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--sr-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Total Transactions</div>
                  <div style={{ fontSize: '1.45rem', fontWeight: 700, color: 'var(--sr-text-primary)', marginTop: '4px' }}>
                    {dataset.metrics.num_transactions.toLocaleString()}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--sr-text-secondary)', marginTop: '2px' }}>6-month timeline</div>
                </div>

                <div style={{ background: 'var(--sr-bg-secondary)', padding: '16px', borderRadius: '8px', border: '1px solid var(--sr-border-subtle)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--sr-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Merchants</div>
                  <div style={{ fontSize: '1.45rem', fontWeight: 700, color: 'var(--sr-text-primary)', marginTop: '4px' }}>
                    {dataset.metrics.num_merchants.toLocaleString()}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--sr-text-secondary)', marginTop: '2px' }}>10 business categories</div>
                </div>

                <div style={{ background: 'var(--sr-bg-secondary)', padding: '16px', borderRadius: '8px', border: '1px solid var(--sr-border-subtle)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--sr-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Customers</div>
                  <div style={{ fontSize: '1.45rem', fontWeight: 700, color: 'var(--sr-text-primary)', marginTop: '4px' }}>
                    {dataset.metrics.num_customers.toLocaleString()}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--sr-text-secondary)', marginTop: '2px' }}>4 behavioral profiles</div>
                </div>

                <div style={{ background: 'var(--sr-bg-secondary)', padding: '16px', borderRadius: '8px', border: '1px solid var(--sr-border-subtle)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--sr-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Fraud Prevalence (GT)</div>
                  <div style={{ fontSize: '1.45rem', fontWeight: 700, color: '#f87171', marginTop: '4px' }}>
                    {dataset.metrics.fraud_prevalence}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--sr-text-muted)', marginTop: '2px' }}>
                    {dataset.metrics.fraud_transactions_ground_truth} labeled fraud txns
                  </div>
                </div>
              </div>

              {/* Injected Archetypes Breakdown */}
              <div style={{ background: 'rgba(17, 24, 39, 0.6)', padding: '14px 18px', borderRadius: '8px', border: '1px solid var(--sr-border-subtle)', marginBottom: '14px' }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--sr-text-secondary)', marginBottom: '10px' }}>
                  Injected Fraud Archetypes (Ground Truth):
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px', fontSize: '0.82rem' }}>
                  <div>
                    <span style={{ color: 'var(--sr-text-muted)' }}>Account Takeover: </span>
                    <span style={{ fontWeight: 600, color: 'var(--sr-text-primary)' }}>{dataset.metrics.account_takeover_count} txns</span>
                  </div>
                  <div>
                    <span style={{ color: 'var(--sr-text-muted)' }}>Card Testing Velocity: </span>
                    <span style={{ fontWeight: 600, color: 'var(--sr-text-primary)' }}>{dataset.metrics.card_testing_count} txns</span>
                  </div>
                  <div>
                    <span style={{ color: 'var(--sr-text-muted)' }}>Coordinated Rings: </span>
                    <span style={{ fontWeight: 600, color: 'var(--sr-text-primary)' }}>{dataset.metrics.coordinated_ring_count} txns (15 rings)</span>
                  </div>
                  <div>
                    <span style={{ color: 'var(--sr-text-muted)' }}>Disputes: </span>
                    <span style={{ fontWeight: 600, color: 'var(--sr-text-primary)' }}>{dataset.metrics.num_disputes} records</span>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="sr-empty-state" style={{ padding: '36px 20px', minHeight: 'auto' }}>
              <div className="sr-empty-icon" style={{ width: '48px', height: '48px', fontSize: '20px' }}>◈</div>
              <h3 className="sr-empty-title" style={{ fontSize: '1rem' }}>Dataset Ready for Seeding</h3>
              <p className="sr-empty-description" style={{ fontSize: '0.82rem' }}>
                Generated CSVs are available. Run <code>python scripts/seed_database.py</code> to load data into SQLite.
              </p>
            </div>
          )}
        </div>
      )}

      {/* FRAUD DETECTION HANDBOOK BANNER */}
      {activeDataSource === 'HANDBOOK' && (
        <div className="sr-card" style={{ marginBottom: '32px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <h2 style={{ fontSize: '1.15rem', fontWeight: 600, color: 'var(--sr-text-primary)' }}>
                  Fraud Detection Handbook Dataset
                </h2>
                <span className="sr-stage-indicator" style={{ background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', borderColor: 'rgba(59, 130, 246, 0.3)' }}>
                  External Replay Active
                </span>
              </div>
              <p style={{ fontSize: '0.82rem', color: 'var(--sr-text-muted)', marginTop: '4px' }}>
                Open-source simulated benchmark (data/external/fraud_handbook/data/*.pkl)
              </p>
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--sr-text-secondary)', background: 'var(--sr-bg-secondary)', padding: '6px 14px', borderRadius: '6px', border: '1px solid var(--sr-border)' }}>
              183 Daily PKL Files
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '14px', marginBottom: '18px' }}>
            <div style={{ background: 'var(--sr-bg-secondary)', padding: '16px', borderRadius: '8px', border: '1px solid var(--sr-border-subtle)' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--sr-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Total Available Rows</div>
              <div style={{ fontSize: '1.45rem', fontWeight: 700, color: '#60a5fa', marginTop: '4px' }}>
                {handbookMeta?.total_rows.toLocaleString() || '1,754,155'}
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--sr-text-secondary)', marginTop: '2px' }}>183 daily partitions</div>
            </div>

            <div style={{ background: 'var(--sr-bg-secondary)', padding: '16px', borderRadius: '8px', border: '1px solid var(--sr-border-subtle)' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--sr-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Date Timeline</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--sr-text-primary)', marginTop: '6px' }}>
                2018-04-01 to 09-30
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--sr-text-secondary)', marginTop: '2px' }}>6-month range</div>
            </div>

            <div style={{ background: 'var(--sr-bg-secondary)', padding: '16px', borderRadius: '8px', border: '1px solid var(--sr-border-subtle)' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--sr-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Ground Truth Fraud</div>
              <div style={{ fontSize: '1.45rem', fontWeight: 700, color: '#f87171', marginTop: '4px' }}>
                {handbookMeta?.total_fraud.toLocaleString() || '14,681'}
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--sr-text-muted)', marginTop: '2px' }}>
                Prevalence: {handbookMeta?.fraud_rate_pct || '0.8369'}%
              </div>
            </div>

            <div style={{ background: 'var(--sr-bg-secondary)', padding: '16px', borderRadius: '8px', border: '1px solid var(--sr-border-subtle)' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--sr-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Pipeline Status</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#4ade80', marginTop: '6px' }}>
                VELOCITY & POLICY
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--sr-text-secondary)', marginTop: '2px' }}>ML/Graph honestly unforced</div>
            </div>
          </div>

          <div style={{ background: 'rgba(17, 24, 39, 0.6)', padding: '14px 18px', borderRadius: '8px', border: '1px solid var(--sr-border-subtle)', marginBottom: '14px' }}>
            <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--sr-text-secondary)', marginBottom: '8px' }}>
              Replay via CLI or Web Operations Console:
            </div>
            <div style={{ fontSize: '0.82rem', fontFamily: 'monospace', color: '#93c5fd', background: 'rgba(0,0,0,0.4)', padding: '8px 12px', borderRadius: '4px' }}>
              python scripts/replay_fraud_handbook.py --limit 1000
            </div>
          </div>
        </div>
      )}

      {/* Planned Modules Architecture */}
      <div className="sr-page-header">
        <h2 className="sr-page-title" style={{ fontSize: '1.15rem' }}>System Capabilities Architecture</h2>
        <p className="sr-page-description">
          Modular payment risk intelligence and streaming authorization pipeline.
        </p>
      </div>

      <div className="sr-overview-grid">
        {modules.map((mod) => (
          <div key={mod.title} className="sr-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
              <span style={{ fontSize: '1.5rem', color: 'var(--sr-text-muted)' }}>{mod.icon}</span>
              <span className="sr-stage-indicator">{mod.stage}</span>
            </div>
            <div className="sr-card-title">{mod.title}</div>
            <div className="sr-card-description">{mod.description}</div>
          </div>
        ))}
      </div>
    </>
  );
}
