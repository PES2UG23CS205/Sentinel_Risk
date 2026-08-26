'use client';

import React, { useState, useEffect } from 'react';

const API_BASE = 'http://localhost:8000';

interface DetectedColumn {
  original_name: string;
  suggested_field: string | null;
  confidence: string;
  detected_type: string;
  null_count: number;
  sample_values: string[];
}

interface ValidationIssue {
  severity: string;
  column?: string;
  message: string;
  affected_rows: number;
}

interface ValidationSummary {
  is_valid: boolean;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  timestamp_range?: [string, string];
  issues: ValidationIssue[];
}

interface SignalItem {
  signal_name: string;
  category: string;
  is_available: boolean;
  required_fields: string[];
  status_label: string;
  technical_rationale: string;
}

interface SignalMatrixReport {
  available_count: number;
  unavailable_count: number;
  available_signals: SignalItem[];
  unavailable_signals: SignalItem[];
}

interface AssessmentAnalytics {
  total_transactions: number;
  approved_count: number;
  challenged_count: number;
  review_count: number;
  hold_count: number;
  approval_rate_pct: number;
  challenge_rate_pct: number;
  review_rate_pct: number;
  hold_rate_pct: number;
  risk_flag_rate_pct: number;
  total_volume: number;
  amount_at_risk: number;
  avg_risk_score: number;
  max_risk_score: number;
  ground_truth_metrics?: {
    has_ground_truth: boolean;
    precision: number;
    recall: number;
    f1_score: number;
    true_positives: number;
    false_positives: number;
    true_negatives: number;
    false_negatives: number;
  };
}

function formatToLocalTime(utcStr: string | null | undefined): string {
  if (!utcStr) return '--';
  try {
    let iso = String(utcStr).trim();
    if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}/.test(iso)) {
      iso = iso.replace(' ', 'T');
      if (!iso.endsWith('Z') && !/[+-]\d{2}:\d{2}$/.test(iso)) {
        iso += 'Z';
      }
    } else if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(iso)) {
      iso += 'Z';
    }
    const d = new Date(iso);
    if (isNaN(d.getTime())) return utcStr;
    return d.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  } catch (e) {
    return utcStr;
  }
}

export default function DataLabPage() {
  const [assessmentId, setAssessmentId] = useState<string | null>(null);
  const [datasetName, setDatasetName] = useState<string>('');
  const [totalRows, setTotalRows] = useState<number>(0);
  const [headers, setHeaders] = useState<string[]>([]);
  const [detectedCols, setDetectedCols] = useState<DetectedColumn[]>([]);
  const [mapping, setMapping] = useState<Record<string, string | null>>({});
  const [validation, setValidation] = useState<ValidationSummary | null>(null);
  const [signalReport, setSignalReport] = useState<SignalMatrixReport | null>(null);
  const [mode, setMode] = useState<string>('QUICK_ASSESSMENT');
  const [excludeInvalid, setExcludeInvalid] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [analytics, setAnalytics] = useState<AssessmentAnalytics | null>(null);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [selectedTxn, setSelectedTxn] = useState<any | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [decisionFilter, setDecisionFilter] = useState<string>('ALL');
  const [history, setHistory] = useState<any[]>([]);

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_BASE}/data-lab/history`);
      if (res.ok) {
        const data = await res.json();
        setHistory(data.assessments || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setStatusMessage('Uploading and inspecting CSV schema...');
    const fd = new FormData();
    fd.append('file', file);
    try {
      const res = await fetch(`${API_BASE}/data-lab/upload`, { method: 'POST', body: fd });
      setLoading(false);
      if (res.ok) {
        const data = await res.json();
        populateWorkbench(data);
      } else {
        const err = await res.json();
        alert('Upload failed: ' + (err.detail || 'Error'));
      }
    } catch (err: any) {
      setLoading(false);
      alert('Upload error: ' + err.message);
    }
  };

  const handleLoadDemo = async () => {
    setLoading(true);
    setStatusMessage('Loading demo dataset (500 transactions)...');
    try {
      const res = await fetch(`${API_BASE}/data-lab/demo-load`, { method: 'POST' });
      setLoading(false);
      if (res.ok) {
        const data = await res.json();
        populateWorkbench(data);
      } else {
        const err = await res.json();
        alert('Demo load failed: ' + (err.detail || 'Error'));
      }
    } catch (err: any) {
      setLoading(false);
      alert('Demo error: ' + err.message);
    }
  };

  const populateWorkbench = (data: any) => {
    setAssessmentId(data.assessment_id);
    setDatasetName(data.dataset_name);
    setTotalRows(data.total_rows);
    setHeaders(data.headers || []);
    setDetectedCols(data.detected_columns || []);
    setMapping(data.inferred_mapping || {});
    setValidation(data.validation_summary || null);
    setSignalReport(data.signal_report || null);
    setAnalytics(null);
    setTransactions([]);
    setSelectedTxn(null);
    fetchHistory();
  };

  const handleApplyMapping = async () => {
    if (!assessmentId) return;
    try {
      const res = await fetch(`${API_BASE}/data-lab/${assessmentId}/mapping`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mapping }),
      });
      if (res.ok) {
        const data = await res.json();
        setValidation(data.validation_summary);
        setSignalReport(data.signal_report);
        alert('✓ Mapping updated and signals recalculated!');
      }
    } catch (e: any) {
      alert('Mapping error: ' + e.message);
    }
  };

  const handleRunAssessment = async () => {
    if (!assessmentId) return;
    setLoading(true);
    setStatusMessage('Executing calibrated SentinelRisk ML & Policy evaluation...');
    try {
      const res = await fetch(`${API_BASE}/data-lab/${assessmentId}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode, exclude_invalid_rows: excludeInvalid }),
      });
      setLoading(false);
      if (res.ok) {
        const data = await res.json();
        setAnalytics(data.analytics);
        fetchTransactions(data.assessment_id);
        fetchHistory();
      } else {
        const err = await res.json();
        alert('Assessment run failed: ' + (err.detail || 'Error'));
      }
    } catch (e: any) {
      setLoading(false);
      alert('Run error: ' + e.message);
    }
  };

  const fetchTransactions = async (asmId?: string) => {
    const id = asmId || assessmentId;
    if (!id) return;
    let url = `${API_BASE}/data-lab/${id}/transactions?limit=50&offset=0`;
    if (decisionFilter !== 'ALL') url += `&decision=${decisionFilter}`;
    if (searchQuery) url += `&search=${encodeURIComponent(searchQuery)}`;
    try {
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setTransactions(data.transactions || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (analytics && assessmentId) {
      fetchTransactions();
    }
  }, [decisionFilter, searchQuery]);

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto', color: '#f3f4f6' }}>
      {/* Header */}
      <div style={{ background: 'linear-gradient(135deg, rgba(30,58,138,0.4), rgba(88,28,135,0.3))', padding: '20px', borderRadius: '8px', border: '1px solid rgba(59,130,246,0.3)', marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h1 style={{ fontSize: '20px', fontWeight: '800', display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
              <span>📥 Data Lab Assessment Studio</span>
              <span style={{ fontSize: '11px', background: 'rgba(34,197,94,0.15)', color: '#4ade80', padding: '3px 8px', borderRadius: '4px', border: '1px solid #22c55e' }}>Zero Feature Fabrication Active</span>
            </h1>
            <p style={{ fontSize: '12px', color: 'rgba(255,255,255,0.7)', marginTop: '4px', margin: 0 }}>
              Ingest arbitrary external payment CSVs, validate data quality, map entity schemas, view honest signal availability, and score transactions.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button onClick={handleLoadDemo} style={{ background: '#16a34a', color: '#fff', border: '1px solid #22c55e', padding: '8px 14px', borderRadius: '4px', fontWeight: '600', fontSize: '12px', cursor: 'pointer' }}>
              ⚡ Try Demo Dataset (500 txns)
            </button>
            <a href={`${API_BASE}/data-lab/example-dataset`} target="_blank" rel="noreferrer" style={{ background: 'rgba(255,255,255,0.08)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)', padding: '8px 14px', borderRadius: '4px', fontWeight: '600', fontSize: '12px', textDecoration: 'none' }}>
              📄 Download Sample CSV
            </a>
          </div>
        </div>
      </div>

      {/* Upload Section */}
      {!assessmentId && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px', marginBottom: '20px' }}>
          <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '20px' }}>
            <h3 style={{ fontSize: '14px', fontWeight: '700', marginTop: 0 }}>Upload Your CSV Dataset</h3>
            <p style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)' }}>Supports standard tabular transaction records up to 25 MB.</p>
            <div style={{ border: '2px dashed rgba(255,255,255,0.2)', borderRadius: '8px', padding: '30px', textAlign: 'center', cursor: 'pointer' }} onClick={() => document.getElementById('nl-file-input')?.click()}>
              <input type="file" id="nl-file-input" accept=".csv,.txt" style={{ display: 'none' }} onChange={handleFileUpload} />
              <div style={{ fontSize: '28px', marginBottom: '8px' }}>📁</div>
              <div style={{ fontWeight: '700', fontSize: '13px' }}>Click to Browse CSV File</div>
            </div>
          </div>

          <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '20px' }}>
            <h3 style={{ fontSize: '14px', fontWeight: '700', marginTop: 0 }}>1-Click Presets</h3>
            <p style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)' }}>Instantly evaluate realistic pre-configured datasets:</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', padding: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: '700', fontSize: '12px' }}>💳 Mixed E-Commerce Traffic (500 txns)</div>
                  <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)' }}>Legitimate checkouts, card velocity bursts & ATO</div>
                </div>
                <button onClick={handleLoadDemo} style={{ background: 'rgba(255,255,255,0.08)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)', padding: '6px 12px', borderRadius: '4px', fontSize: '11px', cursor: 'pointer' }}>Load</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {loading && (
        <div style={{ padding: '16px', background: 'rgba(59,130,246,0.1)', border: '1px solid #3b82f6', borderRadius: '6px', textAlign: 'center', marginBottom: '16px', color: '#60a5fa' }}>
          ⏳ {statusMessage}
        </div>
      )}

      {/* Assessment Workbench */}
      {assessmentId && (
        <div>
          {/* Quality Summary */}
          {validation && (
            <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <h3 style={{ fontSize: '13px', fontWeight: '800', margin: 0, textTransform: 'uppercase' }}>Dataset Validation — {datasetName} ({assessmentId})</h3>
                <span style={{ fontSize: '11px', background: validation.is_valid ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)', color: validation.is_valid ? '#4ade80' : '#f87171', padding: '3px 8px', borderRadius: '4px' }}>
                  {validation.is_valid ? '✓ VALIDATED' : '⚠ QUALITY ISSUES'}
                </span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '8px' }}>
                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px', borderRadius: '6px' }}><div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.5)' }}>TOTAL ROWS</div><div style={{ fontSize: '14px', fontWeight: '700' }}>{totalRows}</div></div>
                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px', borderRadius: '6px' }}><div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.5)' }}>VALID ROWS</div><div style={{ fontSize: '14px', fontWeight: '700', color: '#4ade80' }}>{validation.valid_rows}</div></div>
                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px', borderRadius: '6px' }}><div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.5)' }}>INVALID ROWS</div><div style={{ fontSize: '14px', fontWeight: '700', color: '#f87171' }}>{validation.invalid_rows}</div></div>
                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px', borderRadius: '6px' }}><div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.5)' }}>TIME SPAN</div><div style={{ fontSize: '11px', fontWeight: '600' }}>{validation.timestamp_range ? `${validation.timestamp_range[0].slice(0,10)} → ${validation.timestamp_range[1].slice(0,10)}` : 'Single Window'}</div></div>
              </div>
            </div>
          )}

          {/* Column Mapping */}
          <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '13px', fontWeight: '800', marginTop: 0, textTransform: 'uppercase' }}>Interactive Column Mapping</h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px' }}>
                <thead>
                  <tr style={{ background: 'rgba(255,255,255,0.05)', textAlign: 'left' }}>
                    <th style={{ padding: '8px' }}>Target Field</th>
                    <th style={{ padding: '8px' }}>Mapped Column</th>
                    <th style={{ padding: '8px' }}>Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {['transaction_id', 'timestamp', 'amount', 'customer_id', 'merchant_id', 'device_id', 'payment_instrument_id', 'is_fraud'].map((f) => (
                    <tr key={f} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                      <td style={{ padding: '8px', fontWeight: '700' }}>{f}</td>
                      <td style={{ padding: '8px' }}>
                        <select
                          value={mapping[f] || ''}
                          onChange={(e) => setMapping({ ...mapping, [f]: e.target.value || null })}
                          style={{ background: 'rgba(0,0,0,0.5)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)', padding: '4px', borderRadius: '4px', fontSize: '11px' }}
                        >
                          <option value="">-- Unmapped --</option>
                          {headers.map((h) => (
                            <option key={h} value={h}>{h}</option>
                          ))}
                        </select>
                      </td>
                      <td style={{ padding: '8px', color: mapping[f] ? '#4ade80' : 'rgba(255,255,255,0.4)' }}>
                        {mapping[f] ? 'MAPPED' : 'NONE'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ marginTop: '10px', textAlign: 'right' }}>
              <button onClick={handleApplyMapping} style={{ background: 'rgba(255,255,255,0.08)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)', padding: '6px 12px', borderRadius: '4px', fontSize: '11px', cursor: 'pointer' }}>
                Apply & Recalculate Signals
              </button>
            </div>
          </div>

          {/* Signal Availability Matrix */}
          {signalReport && (
            <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '13px', fontWeight: '800', marginTop: 0, textTransform: 'uppercase', color: '#4ade80' }}>
                Signal Availability Matrix (Zero Fabrication Guarantee)
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <div style={{ fontSize: '11px', fontWeight: '700', color: '#4ade80', marginBottom: '6px' }}>AVAILABLE SIGNALS ({signalReport.available_count})</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {signalReport.available_signals.map((s, idx) => (
                      <div key={idx} style={{ background: 'rgba(34,197,94,0.05)', border: '1px solid rgba(34,197,94,0.2)', padding: '6px 8px', borderRadius: '4px', fontSize: '11px' }}>
                        <strong>✓ {s.signal_name}</strong>
                        <div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.6)' }}>{s.technical_rationale}</div>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '11px', fontWeight: '700', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>UNAVAILABLE SIGNALS ({signalReport.unavailable_count})</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {signalReport.unavailable_signals.map((s, idx) => (
                      <div key={idx} style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.05)', padding: '6px 8px', borderRadius: '4px', fontSize: '11px', opacity: 0.7 }}>
                        <span>✗ {s.signal_name}</span>
                        <div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)' }}>{s.technical_rationale}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Assessment Runner */}
          <div style={{ background: 'linear-gradient(135deg, rgba(34,197,94,0.08), rgba(59,130,246,0.08))', border: '1px solid rgba(34,197,94,0.3)', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '13px', fontWeight: '800', marginTop: 0 }}>Execute Risk Assessment</h3>
            <div style={{ display: 'flex', gap: '16px', marginBottom: '12px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', cursor: 'pointer' }}>
                <input type="radio" value="QUICK_ASSESSMENT" checked={mode === 'QUICK_ASSESSMENT'} onChange={() => setMode('QUICK_ASSESSMENT')} />
                Mode A: Quick Partial-Signal Assessment
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', cursor: 'pointer' }}>
                <input type="radio" value="HISTORICAL_REPLAY" checked={mode === 'HISTORICAL_REPLAY'} onChange={() => setMode('HISTORICAL_REPLAY')} />
                Mode B: Full Historical Replay
              </label>
            </div>
            <button onClick={handleRunAssessment} style={{ background: '#16a34a', color: '#fff', border: '1px solid #22c55e', padding: '10px 20px', borderRadius: '4px', fontWeight: '700', fontSize: '13px', cursor: 'pointer' }}>
              🚀 Run SentinelRisk Assessment
            </button>
          </div>

          {/* Results View */}
          {analytics && (
            <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '14px', fontWeight: '800', marginTop: 0, color: '#60a5fa' }}>Assessment Analytics Results</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '8px', marginBottom: '14px' }}>
                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px', borderRadius: '6px' }}><div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.5)' }}>TOTAL SCORED</div><div style={{ fontSize: '14px', fontWeight: '700' }}>{analytics.total_transactions}</div></div>
                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px', borderRadius: '6px' }}><div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.5)' }}>APPROVE</div><div style={{ fontSize: '14px', fontWeight: '700', color: '#4ade80' }}>{analytics.approved_count} ({analytics.approval_rate_pct}%)</div></div>
                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px', borderRadius: '6px' }}><div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.5)' }}>CHALLENGE</div><div style={{ fontSize: '14px', fontWeight: '700', color: '#38bdf8' }}>{analytics.challenged_count} ({analytics.challenge_rate_pct}%)</div></div>
                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px', borderRadius: '6px' }}><div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.5)' }}>REVIEW</div><div style={{ fontSize: '14px', fontWeight: '700', color: '#f59e0b' }}>{analytics.review_count} ({analytics.review_rate_pct}%)</div></div>
                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px', borderRadius: '6px' }}><div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.5)' }}>HOLD</div><div style={{ fontSize: '14px', fontWeight: '700', color: '#ef4444' }}>{analytics.hold_count} ({analytics.hold_rate_pct}%)</div></div>
                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px', borderRadius: '6px' }}><div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.5)' }}>AMOUNT AT RISK</div><div style={{ fontSize: '14px', fontWeight: '700', color: '#f59e0b' }}>₹{analytics.amount_at_risk.toLocaleString()}</div></div>
              </div>

              {/* Ground truth */}
              {analytics.ground_truth_metrics && analytics.ground_truth_metrics.has_ground_truth && (
                <div style={{ background: 'rgba(0,0,0,0.4)', padding: '12px', borderRadius: '6px', border: '1px solid #22c55e', marginBottom: '14px' }}>
                  <div style={{ fontWeight: '700', fontSize: '11px', color: '#4ade80', marginBottom: '6px' }}>SUPERVISED DETECTION PERFORMANCE</div>
                  <div style={{ display: 'flex', gap: '16px', fontSize: '12px' }}>
                    <div>Precision: <strong>{(analytics.ground_truth_metrics.precision * 100).toFixed(1)}%</strong></div>
                    <div>Recall: <strong>{(analytics.ground_truth_metrics.recall * 100).toFixed(1)}%</strong></div>
                    <div>F1: <strong>{analytics.ground_truth_metrics.f1_score.toFixed(3)}</strong></div>
                  </div>
                </div>
              )}

              {/* Transactions Explorer */}
              <h4 style={{ fontSize: '12px', fontWeight: '700', marginTop: '16px', marginBottom: '8px' }}>Scored Transactions</h4>
              <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                <input
                  type="text"
                  placeholder="Search Txn ID, Customer, Merchant..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{ flex: 1, background: 'rgba(0,0,0,0.5)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)', padding: '6px 10px', borderRadius: '4px', fontSize: '12px' }}
                />
                <select
                  value={decisionFilter}
                  onChange={(e) => setDecisionFilter(e.target.value)}
                  style={{ background: 'rgba(0,0,0,0.5)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)', padding: '6px', borderRadius: '4px', fontSize: '12px' }}
                >
                  <option value="ALL">All Decisions</option>
                  <option value="APPROVE">APPROVE</option>
                  <option value="CHALLENGE">CHALLENGE</option>
                  <option value="REVIEW">REVIEW</option>
                  <option value="HOLD">HOLD</option>
                </select>
              </div>

              <div style={{ overflowX: 'auto', maxHeight: '350px' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px' }}>
                  <thead>
                    <tr style={{ background: 'rgba(255,255,255,0.05)', textAlign: 'left' }}>
                      <th style={{ padding: '6px 8px' }}>Txn ID</th>
                      <th style={{ padding: '6px 8px' }}>Time</th>
                      <th style={{ padding: '6px 8px' }}>Amount</th>
                      <th style={{ padding: '6px 8px' }}>Decision</th>
                      <th style={{ padding: '6px 8px' }}>Risk Score</th>
                      <th style={{ padding: '6px 8px' }}>Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transactions.map((t, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                        <td style={{ padding: '6px 8px', fontWeight: '700' }}>{t.transaction_id}</td>
                        <td style={{ padding: '6px 8px' }}>{t.timestamp?.slice(11)}</td>
                        <td style={{ padding: '6px 8px' }}>₹{parseFloat(t.amount || 0).toLocaleString()}</td>
                        <td style={{ padding: '6px 8px' }}>
                          <span style={{ padding: '2px 6px', borderRadius: '4px', fontWeight: '700', fontSize: '10px', background: t.decision === 'APPROVE' ? 'rgba(34,197,94,0.15)' : (t.decision === 'CHALLENGE' ? 'rgba(56,189,248,0.15)' : (t.decision === 'REVIEW' ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)')), color: t.decision === 'APPROVE' ? '#4ade80' : (t.decision === 'CHALLENGE' ? '#38bdf8' : (t.decision === 'REVIEW' ? '#fbbf24' : '#f87171')) }}>
                            {t.decision}
                          </span>
                        </td>
                        <td style={{ padding: '6px 8px', fontWeight: '700', color: '#38bdf8' }}>{(parseFloat(t.risk_score || 0) * 100).toFixed(1)}%</td>
                        <td style={{ padding: '6px 8px', color: 'rgba(255,255,255,0.7)', maxWidth: '280px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.decision_reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Exports */}
              <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                <a href={`${API_BASE}/data-lab/${assessmentId}/export/csv`} target="_blank" rel="noreferrer" style={{ background: 'rgba(255,255,255,0.08)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)', padding: '6px 12px', borderRadius: '4px', fontSize: '11px', textDecoration: 'none' }}>
                  📥 Export Scored CSV
                </a>
                <a href={`${API_BASE}/data-lab/${assessmentId}/export/json`} target="_blank" rel="noreferrer" style={{ background: 'rgba(255,255,255,0.08)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)', padding: '6px 12px', borderRadius: '4px', fontSize: '11px', textDecoration: 'none' }}>
                  📄 Export JSON Report
                </a>
              </div>
            </div>
          )}
        </div>
      )}

      {/* History */}
      <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '16px', marginTop: '20px' }}>
        <h3 style={{ fontSize: '13px', fontWeight: '800', marginTop: 0 }}>Assessment History</h3>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px' }}>
            <thead>
              <tr style={{ background: 'rgba(255,255,255,0.05)', textAlign: 'left' }}>
                <th style={{ padding: '6px 8px' }}>ID</th>
                <th style={{ padding: '6px 8px' }}>Dataset</th>
                <th style={{ padding: '6px 8px' }}>Rows</th>
                <th style={{ padding: '6px 8px' }}>Uploaded Time</th>
                <th style={{ padding: '6px 8px' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h, idx) => (
                <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  <td style={{ padding: '6px 8px', color: '#60a5fa', fontWeight: '700' }}>{h.assessment_id}</td>
                  <td style={{ padding: '6px 8px' }}>{h.dataset_name}</td>
                  <td style={{ padding: '6px 8px' }}>{h.total_rows}</td>
                  <td style={{ padding: '6px 8px', color: '#e0f2fe' }}>{formatToLocalTime(h.uploaded_at)}</td>
                  <td style={{ padding: '6px 8px' }}>{h.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
