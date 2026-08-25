"use client";

import { useState } from "react";

interface IncidentMetrics {
  total_transactions: number;
  fraud_transactions: number;
  approved_count: number;
  review_count: number;
  hold_count: number;
  investigation_cases_created: number;
  first_detection_timestamp: string;
  fraud_loss_prevented_inr: number;
}

interface IncidentReport {
  scenario: {
    name: string;
    type: string;
    description: string;
    start_time: string;
    attack_details: string;
  };
  metrics: IncidentMetrics;
  sample_investigation_report?: {
    case_id: string;
    policy_decision: string;
    risk_summary: string;
    analyst_summary: string;
    findings: { finding_id: string; statement: string; evidence_ids: string[] }[];
    hypotheses: { hypothesis_id: string; hypothesis: string; confidence: string }[];
  };
  recovery_recommendations: string[];
}

export default function Incidents() {
  const [selectedScenario, setSelectedScenario] = useState<string>("CARD_TESTING_ATTACK");
  const [simulating, setSimulating] = useState(false);
  const [report, setReport] = useState<IncidentReport | null>(null);

  const scenarios = [
    { key: "CARD_TESTING_ATTACK", name: "2:00 AM Card Testing Attack", desc: "Rapid micro-authorization burst on stolen card token." },
    { key: "ACCOUNT_TAKEOVER_ATTACK", name: "2:15 AM Credential Stuffing & ATO", desc: "High-value spend on victim accounts from novel device." },
    { key: "COORDINATED_RING_ATTACK", name: "2:30 AM Coordinated Abuse Ring", desc: "Syndicate sharing hardware & payment tokens across merchants." },
    { key: "BASELINE", name: "Normal Diurnal Traffic", desc: "Standard legitimate daytime payments traffic." },
  ];

  async function handleSimulate() {
    setSimulating(true);
    try {
      const res = await fetch("http://localhost:8000/incidents/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario: selectedScenario }),
      });
      if (res.ok) {
        const data = await res.json();
        setReport(data);
        setSimulating(false);
        return;
      }
    } catch (err) {
      console.log("Using local mock incident simulation", err);
    }

    // Mock local response for standalone execution
    setTimeout(() => {
      setReport({
        scenario: {
          name: scenarios.find((s) => s.key === selectedScenario)?.name || "",
          type: selectedScenario,
          description: scenarios.find((s) => s.key === selectedScenario)?.desc || "",
          start_time: "2025-06-15 02:00:00",
          attack_details: "Synthesized attack pattern evaluated through PolicyEngine and CaseManager.",
        },
        metrics: {
          total_transactions: 20,
          fraud_transactions: 20,
          approved_count: 2,
          review_count: 0,
          hold_count: 18,
          investigation_cases_created: 18,
          first_detection_timestamp: "2025-06-15 02:01:00",
          fraud_loss_prevented_inr: 1350.0,
        },
        sample_investigation_report: {
          case_id: "CASE-00001",
          policy_decision: "HOLD",
          risk_summary: "Case CASE-00001 intercepted under policy sentinelrisk-policy-v1 with decision HOLD.",
          analyst_summary: "High velocity authorization burst detected. Automated script testing stolen card credentials.",
          findings: [
            { finding_id: "FIND-001", statement: "High transaction velocity observed on payment instrument within 1-hour window.", evidence_ids: ["EVID-002"] },
            { finding_id: "FIND-002", statement: "Transaction initiated on an unrecognized device token.", evidence_ids: ["EVID-003"] },
          ],
          hypotheses: [
            { hypothesis_id: "HYP-001", hypothesis: "Card Testing / Automated Velocity Attack: Bot script testing stolen payment instrument.", confidence: "HIGH" },
          ],
        },
        recovery_recommendations: [
          "Recommend temporary authorization rate-limit on payment instrument token PI_BOT_99.",
          "Enforce CAPTCHA challenge at merchant checkout for high-velocity payment tokens.",
          "Notify acquiring gateway to verify BIN-level authorization frequency.",
        ],
      });
      setSimulating(false);
    }, 600);
  }

  return (
    <>
      <div className="sr-page-header">
        <h1 className="sr-page-title">&quot;What Broke at 2 AM&quot; — Incident Simulation & Recovery</h1>
        <p className="sr-page-description">
          Simulate sudden fraud spikes, trace autonomous detection, review AI investigations, and inspect containment playbooks.
        </p>
      </div>

      {/* Scenario Selection */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "12px", marginBottom: "24px" }}>
        {scenarios.map((sc) => {
          const isSelected = selectedScenario === sc.key;
          return (
            <div
              key={sc.key}
              onClick={() => setSelectedScenario(sc.key)}
              className="sr-card"
              style={{
                padding: "16px",
                cursor: "pointer",
                border: isSelected ? "2px solid #2563eb" : "1px solid rgba(255,255,255,0.08)",
                background: isSelected ? "rgba(37, 99, 235, 0.1)" : "rgba(255,255,255,0.02)",
                transition: "all 0.2s",
              }}
            >
              <div style={{ fontWeight: 600, color: "#fff", fontSize: "14px", marginBottom: "4px" }}>{sc.name}</div>
              <div style={{ fontSize: "12px", color: "rgba(255,255,255,0.6)", lineHeight: "1.4" }}>{sc.desc}</div>
            </div>
          );
        })}
      </div>

      <div style={{ marginBottom: "24px" }}>
        <button
          onClick={handleSimulate}
          disabled={simulating}
          style={{
            padding: "10px 24px",
            background: "#2563eb",
            color: "#fff",
            border: "none",
            borderRadius: "6px",
            fontSize: "14px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {simulating ? "Executing Attack Simulation..." : "🚀 Launch Incident Simulation"}
        </button>
      </div>

      {/* Simulation Results */}
      {report && (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Key Metrics Cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px" }}>
            <div className="sr-card" style={{ padding: "16px" }}>
              <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.5)", textTransform: "uppercase", fontWeight: 700 }}>Total Transactions</div>
              <div style={{ fontSize: "24px", fontWeight: 700, color: "#fff", marginTop: "4px" }}>{report.metrics.total_transactions}</div>
            </div>
            <div className="sr-card" style={{ padding: "16px" }}>
              <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.5)", textTransform: "uppercase", fontWeight: 700 }}>HOLD Interventions</div>
              <div style={{ fontSize: "24px", fontWeight: 700, color: "#ef4444", marginTop: "4px" }}>{report.metrics.hold_count}</div>
            </div>
            <div className="sr-card" style={{ padding: "16px" }}>
              <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.5)", textTransform: "uppercase", fontWeight: 700 }}>Cases Created</div>
              <div style={{ fontSize: "24px", fontWeight: 700, color: "#3b82f6", marginTop: "4px" }}>{report.metrics.investigation_cases_created}</div>
            </div>
            <div className="sr-card" style={{ padding: "16px" }}>
              <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.5)", textTransform: "uppercase", fontWeight: 700 }}>Prevented Loss</div>
              <div style={{ fontSize: "24px", fontWeight: 700, color: "#22c55e", marginTop: "4px" }}>INR {report.metrics.fraud_loss_prevented_inr.toLocaleString()}</div>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "20px" }}>
            {/* Investigation Report Card */}
            {report.sample_investigation_report && (
              <div className="sr-card">
                <div style={{ fontSize: "14px", fontWeight: 700, color: "#fff", marginBottom: "12px", borderBottom: "1px solid rgba(255,255,255,0.1)", paddingBottom: "8px" }}>
                  Lead Case Investigation ({report.sample_investigation_report.case_id})
                </div>
                <div style={{ fontSize: "13px", color: "rgba(255,255,255,0.9)", lineHeight: "1.5", marginBottom: "12px" }}>
                  {report.sample_investigation_report.analyst_summary}
                </div>
                <div style={{ fontSize: "12px", fontWeight: 700, color: "rgba(255,255,255,0.7)", marginBottom: "6px" }}>Factual Findings:</div>
                <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginBottom: "12px" }}>
                  {report.sample_investigation_report.findings.map((f) => (
                    <div key={f.finding_id} style={{ background: "rgba(255,255,255,0.02)", padding: "8px 10px", borderRadius: "4px", fontSize: "12px", color: "#fff" }}>
                      • {f.statement}
                    </div>
                  ))}
                </div>
                <div style={{ fontSize: "12px", fontWeight: 700, color: "rgba(255,255,255,0.7)", marginBottom: "6px" }}>Primary Hypothesis:</div>
                <div style={{ background: "rgba(168, 85, 247, 0.1)", border: "1px solid rgba(168, 85, 247, 0.3)", padding: "8px 10px", borderRadius: "4px", fontSize: "12px", color: "#fff" }}>
                  {report.sample_investigation_report.hypotheses[0]?.hypothesis}
                </div>
              </div>
            )}

            {/* Recovery Recommendations Card */}
            <div className="sr-card">
              <div style={{ fontSize: "14px", fontWeight: 700, color: "#22c55e", marginBottom: "12px", borderBottom: "1px solid rgba(255,255,255,0.1)", paddingBottom: "8px" }}>
                🛡️ Recommended Containment & Recovery Actions
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {report.recovery_recommendations.map((rec, idx) => (
                  <div key={idx} style={{ display: "flex", gap: "8px", alignItems: "flex-start", background: "rgba(34, 197, 94, 0.05)", border: "1px solid rgba(34, 197, 94, 0.2)", padding: "10px 12px", borderRadius: "6px" }}>
                    <span style={{ color: "#22c55e", fontWeight: 700 }}>✓</span>
                    <span style={{ fontSize: "12px", color: "rgba(255,255,255,0.9)", lineHeight: "1.4" }}>{rec}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
