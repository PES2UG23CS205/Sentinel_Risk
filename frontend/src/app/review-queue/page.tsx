"use client";

import { useState, useEffect } from "react";

interface Finding {
  finding_id: string;
  statement: string;
  evidence_ids: string[];
  confidence: string;
  classification: string;
}

interface Hypothesis {
  hypothesis_id: string;
  hypothesis: string;
  supporting_evidence_ids: string[];
  confidence: string;
}

interface EvidenceItem {
  evidence_id: string;
  evidence_type: string;
  source: string;
  description: string;
}

interface InvestigationReport {
  case_id: string;
  policy_decision: string;
  policy_version: string;
  risk_summary: string;
  analyst_summary: string;
  uncertainty: string;
  evidence: EvidenceItem[];
  findings: Finding[];
  hypotheses: Hypothesis[];
  suspicious_signals: string[];
  benign_signals: string[];
  recommended_next_steps: string[];
}

interface AnalystNote {
  note_id: string;
  timestamp: string;
  analyst: string;
  text: string;
}

interface CaseItem {
  case_id: string;
  transaction_id: string | number;
  timestamp: string;
  amount: number;
  policy_decision: string;
  priority: string;
  status: string;
  report?: InvestigationReport;
  notes: AnalystNote[];
}

export default function ReviewQueue() {
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [selectedCase, setSelectedCase] = useState<CaseItem | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>("ALL");
  const [loading, setLoading] = useState(false);
  const [investigating, setInvestigating] = useState(false);
  const [newNote, setNewNote] = useState("");

  const sampleCases: CaseItem[] = [
    {
      case_id: "CASE-00001",
      transaction_id: 2557,
      timestamp: "2025-01-30 21:41:22",
      amount: 96.32,
      policy_decision: "HOLD",
      priority: "CRITICAL",
      status: "OPEN",
      notes: [],
    },
    {
      case_id: "CASE-00002",
      transaction_id: 806,
      timestamp: "2025-01-18 05:32:57",
      amount: 896.74,
      policy_decision: "REVIEW",
      priority: "MEDIUM",
      status: "OPEN",
      notes: [],
    },
    {
      case_id: "CASE-00003",
      transaction_id: 4661,
      timestamp: "2025-02-10 09:00:47",
      amount: 3400.0,
      policy_decision: "HOLD",
      priority: "CRITICAL",
      status: "OPEN",
      notes: [],
    },
  ];

  useEffect(() => {
    fetchCases();
  }, []);

  async function fetchCases() {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/cases/");
      if (res.ok) {
        const data = await res.json();
        if (data.cases && data.cases.length > 0) {
          setCases(data.cases);
          setSelectedCase(data.cases[0]);
          return;
        }
      }
    } catch (err) {
      console.log("Backend offline; using local queue state.", err);
    }
    setCases(sampleCases);
    setSelectedCase(sampleCases[0]);
    setLoading(false);
  }

  async function handleInvestigate(caseId: string) {
    setInvestigating(true);
    try {
      const res = await fetch(`http://localhost:8000/cases/${caseId}/investigate`, {
        method: "POST",
      });
      if (res.ok) {
        const report = await res.json();
        setCases((prev) =>
          prev.map((c) => (c.case_id === caseId ? { ...c, report, status: "INVESTIGATING" } : c))
        );
        if (selectedCase?.case_id === caseId) {
          setSelectedCase((prev) => prev ? { ...prev, report, status: "INVESTIGATING" } : null);
        }
        setInvestigating(false);
        return;
      }
    } catch (err) {
      console.log("Local mock investigation", err);
    }

    // Mock local investigation synthesis for interactive demo
    const mockReport: InvestigationReport = {
      case_id: caseId,
      policy_decision: selectedCase?.policy_decision || "HOLD",
      policy_version: "sentinelrisk-policy-v1",
      risk_summary: `Transaction #${selectedCase?.transaction_id} was intercepted under policy sentinelrisk-policy-v1.`,
      analyst_summary: `Evidence indicates multi-signal anomaly. Key risk factors include unrecognized device token and high behavioral deviation.`,
      uncertainty: "Device sharing can occur legitimately in family households. Manual verification recommended.",
      evidence: [
        { evidence_id: "EVID-001", evidence_type: "transaction", source: "transaction_features", description: `Transaction amount is INR ${selectedCase?.amount.toFixed(2)}.` },
        { evidence_id: "EVID-002", evidence_type: "ml_score", source: "lightgbm_model", description: "Supervised LightGBM calibrated fraud probability is 0.9995." },
        { evidence_id: "EVID-003", evidence_type: "device_novelty", source: "transaction_features", description: "Novel device hardware fingerprint never seen for customer." },
      ],
      findings: [
        { finding_id: "FIND-001", statement: "Supervised LightGBM model detected severe behavioral risk (probability > 0.99).", evidence_ids: ["EVID-002"], confidence: "HIGH", classification: "SUPPORTED" },
        { finding_id: "FIND-002", statement: "Transaction initiated on an unrecognized device token.", evidence_ids: ["EVID-003"], confidence: "HIGH", classification: "SUPPORTED" },
      ],
      hypotheses: [
        { hypothesis_id: "HYP-001", hypothesis: "Account Takeover (ATO): Unauthorized party accessing customer profile.", supporting_evidence_ids: ["EVID-002", "EVID-003"], confidence: "HIGH" },
      ],
      suspicious_signals: ["High-confidence ML risk score", "Unrecognized device hardware"],
      benign_signals: ["Consistent merchant category"],
      recommended_next_steps: ["Verify customer identity via registered phone number.", "Review transaction history on device."],
    };

    setCases((prev) =>
      prev.map((c) => (c.case_id === caseId ? { ...c, report: mockReport, status: "INVESTIGATING" } : c))
    );
    if (selectedCase?.case_id === caseId) {
      setSelectedCase((prev) => prev ? { ...prev, report: mockReport, status: "INVESTIGATING" } : null);
    }
    setInvestigating(false);
  }

  async function handleAddNote() {
    if (!selectedCase || !newNote.trim()) return;
    const noteObj: AnalystNote = {
      note_id: `NOTE-${Date.now()}`,
      timestamp: new Date().toISOString().replace("T", " ").substring(0, 19),
      analyst: "Analyst_Priya",
      text: newNote.trim(),
    };
    try {
      await fetch(`http://localhost:8000/cases/${selectedCase.case_id}/notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ analyst: "Analyst_Priya", text: newNote.trim() }),
      });
    } catch {}

    const updated = { ...selectedCase, notes: [...selectedCase.notes, noteObj] };
    setSelectedCase(updated);
    setCases((prev) => prev.map((c) => (c.case_id === selectedCase.case_id ? updated : c)));
    setNewNote("");
  }

  async function handleStatusChange(newStatus: string) {
    if (!selectedCase) return;
    try {
      await fetch(`http://localhost:8000/cases/${selectedCase.case_id}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus, details: "Status updated by analyst." }),
      });
    } catch {}

    const updated = { ...selectedCase, status: newStatus };
    setSelectedCase(updated);
    setCases((prev) => prev.map((c) => (c.case_id === selectedCase.case_id ? updated : c)));
  }

  const filteredCases = filterStatus === "ALL" ? cases : cases.filter((c) => c.status === filterStatus);

  return (
    <>
      <div className="sr-page-header">
        <h1 className="sr-page-title">Analyst Review Queue & Investigation Cases</h1>
        <p className="sr-page-description">
          Triage intercepted REVIEW and HOLD transactions with AI-assisted, evidence-grounded reports.
        </p>
      </div>

      {/* Filter Toolbar */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "20px" }}>
        {["ALL", "OPEN", "INVESTIGATING", "RESOLVED"].map((st) => (
          <button
            key={st}
            onClick={() => setFilterStatus(st)}
            style={{
              padding: "6px 14px",
              borderRadius: "6px",
              border: "1px solid var(--border-color, #333)",
              background: filterStatus === st ? "#2563eb" : "rgba(255,255,255,0.05)",
              color: "#fff",
              cursor: "pointer",
              fontSize: "13px",
              fontWeight: 500,
            }}
          >
            {st}
          </button>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1.6fr", gap: "20px" }}>
        {/* Case Queue Table */}
        <div className="sr-card" style={{ padding: "0" }}>
          <div style={{ padding: "16px", borderBottom: "1px solid rgba(255,255,255,0.1)", fontWeight: 600 }}>
            Active Cases ({filteredCases.length})
          </div>
          <div style={{ maxHeight: "650px", overflowY: "auto" }}>
            {filteredCases.map((c) => {
              const isSelected = selectedCase?.case_id === c.case_id;
              const isHold = c.policy_decision === "HOLD";
              return (
                <div
                  key={c.case_id}
                  onClick={() => setSelectedCase(c)}
                  style={{
                    padding: "14px 16px",
                    borderBottom: "1px solid rgba(255,255,255,0.05)",
                    background: isSelected ? "rgba(37, 99, 235, 0.15)" : "transparent",
                    cursor: "pointer",
                    transition: "background 0.2s",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                    <span style={{ fontWeight: 600, color: "#fff" }}>{c.case_id}</span>
                    <span
                      style={{
                        padding: "2px 8px",
                        borderRadius: "4px",
                        fontSize: "11px",
                        fontWeight: 700,
                        background: isHold ? "rgba(239, 68, 68, 0.2)" : "rgba(234, 179, 8, 0.2)",
                        color: isHold ? "#ef4444" : "#eab308",
                        border: `1px solid ${isHold ? "#ef4444" : "#eab308"}`,
                      }}
                    >
                      {c.policy_decision}
                    </span>
                  </div>
                  <div style={{ fontSize: "12px", color: "rgba(255,255,255,0.7)", display: "flex", justifyContent: "space-between" }}>
                    <span>Txn #{c.transaction_id}</span>
                    <span style={{ fontWeight: 600, color: "#fff" }}>INR {c.amount.toFixed(2)}</span>
                  </div>
                  <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.5)", marginTop: "4px", display: "flex", justifyContent: "space-between" }}>
                    <span>{c.timestamp}</span>
                    <span style={{ color: c.priority === "CRITICAL" ? "#ef4444" : "#3b82f6" }}>{c.priority}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Case Details & Investigation Panel */}
        <div className="sr-card">
          {selectedCase ? (
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid rgba(255,255,255,0.1)", paddingBottom: "12px", marginBottom: "16px" }}>
                <div>
                  <h2 style={{ margin: 0, fontSize: "20px", color: "#fff" }}>{selectedCase.case_id}</h2>
                  <div style={{ fontSize: "12px", color: "rgba(255,255,255,0.6)", marginTop: "2px" }}>
                    Transaction #{selectedCase.transaction_id} • Amount: INR {selectedCase.amount.toFixed(2)} • {selectedCase.timestamp}
                  </div>
                </div>
                <div style={{ display: "flex", gap: "8px" }}>
                  <button
                    onClick={() => handleInvestigate(selectedCase.case_id)}
                    disabled={investigating}
                    style={{
                      padding: "8px 14px",
                      background: "#2563eb",
                      color: "#fff",
                      border: "none",
                      borderRadius: "6px",
                      cursor: "pointer",
                      fontSize: "12px",
                      fontWeight: 600,
                    }}
                  >
                    {investigating ? "Investigating..." : selectedCase.report ? "Re-Investigate" : "Run AI Investigation"}
                  </button>
                  <button
                    onClick={() => handleStatusChange("RESOLVED")}
                    style={{
                      padding: "8px 12px",
                      background: "rgba(34, 197, 94, 0.2)",
                      color: "#22c55e",
                      border: "1px solid #22c55e",
                      borderRadius: "6px",
                      cursor: "pointer",
                      fontSize: "12px",
                      fontWeight: 600,
                    }}
                  >
                    Resolve
                  </button>
                </div>
              </div>

              {/* Investigation Report Display */}
              {selectedCase.report ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  <div style={{ background: "rgba(255,255,255,0.03)", padding: "12px", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.08)" }}>
                    <div style={{ fontSize: "11px", fontWeight: 700, color: "#3b82f6", textTransform: "uppercase", letterSpacing: "0.5px" }}>Analyst Summary</div>
                    <div style={{ fontSize: "13px", color: "#fff", marginTop: "4px", lineHeight: "1.5" }}>{selectedCase.report.analyst_summary}</div>
                  </div>

                  {/* Factual Findings with Evidence Citations */}
                  <div>
                    <div style={{ fontSize: "12px", fontWeight: 700, color: "rgba(255,255,255,0.8)", marginBottom: "8px" }}>
                      Factual Findings ({selectedCase.report.findings.length})
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                      {selectedCase.report.findings.map((f) => (
                        <div key={f.finding_id} style={{ background: "rgba(255,255,255,0.02)", padding: "8px 12px", borderRadius: "6px", border: "1px solid rgba(255,255,255,0.05)", fontSize: "12px" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", color: "#fff" }}>
                            <span>{f.statement}</span>
                            <span style={{ fontSize: "10px", color: "#22c55e", fontWeight: 600 }}>{f.classification}</span>
                          </div>
                          <div style={{ marginTop: "4px", display: "flex", gap: "4px" }}>
                            {f.evidence_ids.map((eid) => (
                              <span key={eid} style={{ background: "rgba(59, 130, 246, 0.2)", color: "#60a5fa", padding: "1px 6px", borderRadius: "3px", fontSize: "10px", fontWeight: 600 }}>
                                {eid}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Hypotheses */}
                  <div>
                    <div style={{ fontSize: "12px", fontWeight: 700, color: "rgba(255,255,255,0.8)", marginBottom: "8px" }}>
                      Synthesized Hypotheses
                    </div>
                    {selectedCase.report.hypotheses.map((h) => (
                      <div key={h.hypothesis_id} style={{ background: "rgba(168, 85, 247, 0.08)", border: "1px solid rgba(168, 85, 247, 0.3)", padding: "10px", borderRadius: "6px", fontSize: "12px", color: "#fff" }}>
                        <div style={{ fontWeight: 600 }}>{h.hypothesis}</div>
                        <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.6)", marginTop: "4px" }}>
                          Confidence: <span style={{ color: "#c084fc", fontWeight: 600 }}>{h.confidence}</span>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Recommended Steps */}
                  <div>
                    <div style={{ fontSize: "12px", fontWeight: 700, color: "rgba(255,255,255,0.8)", marginBottom: "6px" }}>
                      Recommended Next Actions
                    </div>
                    <ul style={{ margin: 0, paddingLeft: "20px", fontSize: "12px", color: "rgba(255,255,255,0.8)", lineHeight: "1.6" }}>
                      {selectedCase.report.recommended_next_steps.map((step, idx) => (
                        <li key={idx}>{step}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              ) : (
                <div style={{ padding: "40px", textAlign: "center", color: "rgba(255,255,255,0.5)" }}>
                  <div style={{ fontSize: "28px", marginBottom: "8px" }}>🔍</div>
                  <div>No investigation generated yet.</div>
                  <div style={{ fontSize: "12px", marginTop: "4px" }}>Click &quot;Run AI Investigation&quot; to synthesize evidence.</div>
                </div>
              )}

              {/* Analyst Notes Section */}
              <div style={{ marginTop: "24px", paddingTop: "16px", borderTop: "1px solid rgba(255,255,255,0.1)" }}>
                <div style={{ fontSize: "12px", fontWeight: 700, color: "rgba(255,255,255,0.8)", marginBottom: "8px" }}>
                  Analyst Audit Notes ({selectedCase.notes.length})
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginBottom: "10px" }}>
                  {selectedCase.notes.map((n) => (
                    <div key={n.note_id} style={{ background: "rgba(255,255,255,0.03)", padding: "8px 10px", borderRadius: "4px", fontSize: "12px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", color: "rgba(255,255,255,0.5)", fontSize: "10px" }}>
                        <span style={{ fontWeight: 600, color: "#60a5fa" }}>{n.analyst}</span>
                        <span>{n.timestamp}</span>
                      </div>
                      <div style={{ color: "#fff", marginTop: "2px" }}>{n.text}</div>
                    </div>
                  ))}
                </div>
                <div style={{ display: "flex", gap: "8px" }}>
                  <input
                    type="text"
                    placeholder="Add an analyst note..."
                    value={newNote}
                    onChange={(e) => setNewNote(e.target.value)}
                    style={{
                      flex: 1,
                      padding: "8px 12px",
                      borderRadius: "6px",
                      border: "1px solid rgba(255,255,255,0.15)",
                      background: "rgba(0,0,0,0.3)",
                      color: "#fff",
                      fontSize: "12px",
                    }}
                  />
                  <button
                    onClick={handleAddNote}
                    style={{
                      padding: "8px 14px",
                      background: "rgba(255,255,255,0.1)",
                      color: "#fff",
                      border: "1px solid rgba(255,255,255,0.2)",
                      borderRadius: "6px",
                      cursor: "pointer",
                      fontSize: "12px",
                      fontWeight: 600,
                    }}
                  >
                    Post Note
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div style={{ padding: "40px", textAlign: "center", color: "rgba(255,255,255,0.5)" }}>
              Select a case from the queue to view details.
            </div>
          )}
        </div>
      </div>
    </>
  );
}
