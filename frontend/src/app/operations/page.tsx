"use client";

import { useState, useEffect } from "react";

interface OperationalMetrics {
  traffic: {
    total_requests: number;
    successful_requests: number;
    failed_requests: number;
    cached_idempotent_requests: number;
    throughput_rps: number;
  };
  decisions: {
    approve_count: number;
    review_count: number;
    hold_count: number;
    approve_rate_pct: number;
    review_rate_pct: number;
    hold_rate_pct: number;
  };
  latencies: {
    p50_ms: number;
    p95_ms: number;
    p99_ms: number;
    mean_ms: number;
    min_ms: number;
    max_ms: number;
  };
  dependency_failures: Record<string, number>;
  active_alerts: { alert: string; severity: string; message: string }[];
}

interface DependencyHealth {
  service: string;
  overall_health: string;
  dependencies: Record<string, { status: string; version?: string; fallback_available?: boolean }>;
}

export default function Operations() {
  const [metrics, setMetrics] = useState<OperationalMetrics | null>(null);
  const [health, setHealth] = useState<DependencyHealth | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchOperationsData();
    const interval = setInterval(fetchOperationsData, 5000);
    return () => clearInterval(interval);
  }, []);

  async function fetchOperationsData() {
    try {
      const [resMet, resHealth] = await Promise.all([
        fetch("http://localhost:8000/metrics/operations"),
        fetch("http://localhost:8000/health/dependencies"),
      ]);
      if (resMet.ok) setMetrics(await resMet.json());
      if (resHealth.ok) setHealth(await resHealth.json());
    } catch {
      // Fallback local mock data for standalone frontend viewing
      setMetrics({
        traffic: {
          total_requests: 1000,
          successful_requests: 1000,
          failed_requests: 0,
          cached_idempotent_requests: 48,
          throughput_rps: 17929.05,
        },
        decisions: {
          approve_count: 983,
          review_count: 7,
          hold_count: 10,
          approve_rate_pct: 98.3,
          review_rate_pct: 0.7,
          hold_rate_pct: 1.0,
        },
        latencies: {
          p50_ms: 0.046,
          p95_ms: 0.081,
          p99_ms: 0.136,
          mean_ms: 0.052,
          min_ms: 0.021,
          max_ms: 0.450,
        },
        dependency_failures: { ml: 0, graph: 0, rules: 0, policy: 0, investigation: 0 },
        active_alerts: [],
      });

      setHealth({
        service: "sentinelrisk",
        overall_health: "HEALTHY",
        dependencies: {
          ml_model_service: { status: "HEALTHY", version: "lightgbm-v1", fallback_available: true },
          entity_graph_service: { status: "HEALTHY", version: "graph-v1", fallback_available: true },
          policy_engine: { status: "HEALTHY", version: "sentinelrisk-policy-v1" },
          investigation_llm: { status: "HEALTHY", version: "MockInvestigationLLM" },
        },
      });
    }
  }

  return (
    <>
      <div className="sr-page-header">
        <h1 className="sr-page-title">Production Operations & Observability</h1>
        <p className="sr-page-description">
          Real-time service health, latency percentiles, throughput instrumentation, and active operational alert thresholds.
        </p>
      </div>

      {/* System Health Badges */}
      <div className="sr-card" style={{ marginBottom: "20px" }}>
        <div style={{ fontSize: "14px", fontWeight: 700, color: "#fff", marginBottom: "12px" }}>
          Dependency Health & Service Probes
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "12px" }}>
          {health?.dependencies ? (
            Object.entries(health.dependencies).map(([dep, info]) => (
              <div
                key={dep}
                style={{
                  background: "rgba(255,255,255,0.03)",
                  padding: "12px",
                  borderRadius: "6px",
                  border: "1px solid rgba(255,255,255,0.08)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "12px", fontWeight: 600, color: "rgba(255,255,255,0.8)" }}>{dep.replace(/_/g, " ").toUpperCase()}</span>
                  <span
                    style={{
                      padding: "2px 6px",
                      borderRadius: "4px",
                      fontSize: "10px",
                      fontWeight: 700,
                      background: info.status === "HEALTHY" ? "rgba(34, 197, 94, 0.2)" : "rgba(239, 68, 68, 0.2)",
                      color: info.status === "HEALTHY" ? "#22c55e" : "#ef4444",
                    }}
                  >
                    {info.status}
                  </span>
                </div>
                {info.version && (
                  <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.5)", marginTop: "4px" }}>
                    Version: {info.version}
                  </div>
                )}
              </div>
            ))
          ) : (
            <div>Loading dependency health...</div>
          )}
        </div>
      </div>

      {/* Key Metric Gauges */}
      {metrics && (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px" }}>
            <div className="sr-card" style={{ padding: "16px" }}>
              <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.5)", textTransform: "uppercase", fontWeight: 700 }}>Throughput</div>
              <div style={{ fontSize: "24px", fontWeight: 700, color: "#fff", marginTop: "4px" }}>{metrics.traffic.throughput_rps.toLocaleString()} <span style={{ fontSize: "12px", color: "rgba(255,255,255,0.5)" }}>RPS</span></div>
            </div>
            <div className="sr-card" style={{ padding: "16px" }}>
              <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.5)", textTransform: "uppercase", fontWeight: 700 }}>p50 Latency</div>
              <div style={{ fontSize: "24px", fontWeight: 700, color: "#22c55e", marginTop: "4px" }}>{metrics.latencies.p50_ms} <span style={{ fontSize: "12px", color: "rgba(255,255,255,0.5)" }}>ms</span></div>
            </div>
            <div className="sr-card" style={{ padding: "16px" }}>
              <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.5)", textTransform: "uppercase", fontWeight: 700 }}>p95 Latency</div>
              <div style={{ fontSize: "24px", fontWeight: 700, color: "#3b82f6", marginTop: "4px" }}>{metrics.latencies.p95_ms} <span style={{ fontSize: "12px", color: "rgba(255,255,255,0.5)" }}>ms</span></div>
            </div>
            <div className="sr-card" style={{ padding: "16px" }}>
              <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.5)", textTransform: "uppercase", fontWeight: 700 }}>p99 Latency</div>
              <div style={{ fontSize: "24px", fontWeight: 700, color: "#a855f7", marginTop: "4px" }}>{metrics.latencies.p99_ms} <span style={{ fontSize: "12px", color: "rgba(255,255,255,0.5)" }}>ms</span></div>
            </div>
          </div>

          {/* Traffic Breakdown & Latency Distribution */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
            <div className="sr-card">
              <div style={{ fontSize: "14px", fontWeight: 700, color: "#fff", marginBottom: "12px" }}>
                Decision Distribution (Tri-State Traffic)
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "4px" }}>
                    <span>APPROVE (Frictionless)</span>
                    <span style={{ fontWeight: 600, color: "#22c55e" }}>{metrics.decisions.approve_count} ({metrics.decisions.approve_rate_pct}%)</span>
                  </div>
                  <div style={{ height: "6px", background: "rgba(255,255,255,0.1)", borderRadius: "3px", overflow: "hidden" }}>
                    <div style={{ width: `${metrics.decisions.approve_rate_pct}%`, height: "100%", background: "#22c55e" }} />
                  </div>
                </div>

                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "4px" }}>
                    <span>REVIEW (Analyst Triage)</span>
                    <span style={{ fontWeight: 600, color: "#eab308" }}>{metrics.decisions.review_count} ({metrics.decisions.review_rate_pct}%)</span>
                  </div>
                  <div style={{ height: "6px", background: "rgba(255,255,255,0.1)", borderRadius: "3px", overflow: "hidden" }}>
                    <div style={{ width: `${metrics.decisions.review_rate_pct}%`, height: "100%", background: "#eab308" }} />
                  </div>
                </div>

                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "4px" }}>
                    <span>HOLD (Automated Freeze)</span>
                    <span style={{ fontWeight: 600, color: "#ef4444" }}>{metrics.decisions.hold_count} ({metrics.decisions.hold_rate_pct}%)</span>
                  </div>
                  <div style={{ height: "6px", background: "rgba(255,255,255,0.1)", borderRadius: "3px", overflow: "hidden" }}>
                    <div style={{ width: `${metrics.decisions.hold_rate_pct}%`, height: "100%", background: "#ef4444" }} />
                  </div>
                </div>
              </div>
            </div>

            {/* Version Tracking & Auditing */}
            <div className="sr-card">
              <div style={{ fontSize: "14px", fontWeight: 700, color: "#fff", marginBottom: "12px" }}>
                Active Production Metadata & Versions
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "12px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 8px", background: "rgba(255,255,255,0.02)", borderRadius: "4px" }}>
                  <span style={{ color: "rgba(255,255,255,0.6)" }}>Model Version</span>
                  <span style={{ fontWeight: 600, color: "#fff" }}>lightgbm-v1</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 8px", background: "rgba(255,255,255,0.02)", borderRadius: "4px" }}>
                  <span style={{ color: "rgba(255,255,255,0.6)" }}>Feature Version</span>
                  <span style={{ fontWeight: 600, color: "#fff" }}>features-v1</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 8px", background: "rgba(255,255,255,0.02)", borderRadius: "4px" }}>
                  <span style={{ color: "rgba(255,255,255,0.6)" }}>Graph Version</span>
                  <span style={{ fontWeight: 600, color: "#fff" }}>graph-v1</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 8px", background: "rgba(255,255,255,0.02)", borderRadius: "4px" }}>
                  <span style={{ color: "rgba(255,255,255,0.6)" }}>Policy Version</span>
                  <span style={{ fontWeight: 600, color: "#3b82f6" }}>sentinelrisk-policy-v1</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 8px", background: "rgba(255,255,255,0.02)", borderRadius: "4px" }}>
                  <span style={{ color: "rgba(255,255,255,0.6)" }}>Investigation Prompt</span>
                  <span style={{ fontWeight: 600, color: "#c084fc" }}>investigation-prompt-v1</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
