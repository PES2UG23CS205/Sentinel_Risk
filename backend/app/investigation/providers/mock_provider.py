"""
SentinelRisk — Deterministic Mock Investigation LLM Provider

Produces evidence-grounded, structured investigation reports strictly citing
supplied EvidenceItems (EVID-xxx) without external network dependencies or API keys.
Guarantees 100% reproducibility, zero hallucination, and strict policy preservation.
"""

from backend.app.investigation.models import (
    InvestigationContext,
    InvestigationReport,
    Finding,
    Hypothesis,
    ConfidenceLevel,
    FindingClassification,
)
from backend.app.investigation.providers.base import BaseInvestigationLLM


class MockInvestigationLLM(BaseInvestigationLLM):
    """Deterministic, mock investigation provider for tests, CI, and offline demos."""

    def generate_report(self, context: InvestigationContext) -> InvestigationReport:
        """
        Synthesize an evidence-grounded report from context evidence items.
        """
        c = context
        evid_map = {e.evidence_id: e for e in c.evidence_items}

        findings: list[Finding] = []
        hypotheses: list[Hypothesis] = []
        suspicious_signals: list[str] = []
        benign_signals: list[str] = []
        recommendations: list[str] = []

        finding_idx = 1
        def add_finding(stmt: str, eids: list[str], conf: ConfidenceLevel, cls: FindingClassification):
            nonlocal finding_idx
            # Only cite evidence IDs that actually exist in the context
            valid_eids = [eid for eid in eids if eid in evid_map]
            findings.append(Finding(
                finding_id=f"FIND-{finding_idx:03d}",
                statement=stmt,
                evidence_ids=valid_eids,
                confidence=conf,
                classification=cls,
            ))
            finding_idx += 1

        # 1. Map ML Score Evidence
        ml_evids = [e.evidence_id for e in c.evidence_items if e.evidence_type == "ml_score"]
        if c.ml_probability >= 0.50:
            add_finding(
                f"Supervised LightGBM model detected severe behavioral risk with calibrated fraud probability of {c.ml_probability:.3f}.",
                ml_evids, ConfidenceLevel.HIGH, FindingClassification.SUPPORTED,
            )
            suspicious_signals.append(f"High-confidence ML risk score ({c.ml_probability:.3f})")
        elif c.ml_probability >= 0.05:
            add_finding(
                f"Supervised ML model identified elevated transaction risk (probability: {c.ml_probability:.3f}).",
                ml_evids, ConfidenceLevel.MEDIUM, FindingClassification.SUPPORTED,
            )
            suspicious_signals.append(f"Elevated ML risk score ({c.ml_probability:.3f})")

        # 2. Map Graph Topology Evidence
        graph_evids = [e.evidence_id for e in c.evidence_items if e.evidence_type == "graph_topology"]
        if c.graph_ring_score >= 0.50 or c.graph_ring_candidate == 1:
            add_finding(
                f"Entity graph analysis identified multi-account infrastructure sharing with ring score of {c.graph_ring_score:.2f}.",
                graph_evids, ConfidenceLevel.HIGH, FindingClassification.SUPPORTED,
            )
            suspicious_signals.append(f"Coordinated syndicate infrastructure sharing (Ring score: {c.graph_ring_score:.2f})")
            recommendations.append("Inspect connected customer accounts and shared hardware tokens in entity graph.")

        # 3. Map Velocity Evidence (Strictly grounded in threshold rules)
        vel_evids = [e.evidence_id for e in c.evidence_items if e.evidence_type == "velocity"]
        if vel_evids:
            # Check actual velocity value from evidence item
            v_item = next((e for e in c.evidence_items if e.evidence_type == "velocity"), None)
            v_val = int(v_item.value) if v_item and isinstance(v_item.value, (int, float)) else 0
            if v_val >= 5:
                add_finding(
                    f"Severe authorization velocity burst observed on payment instrument ({v_val} transactions within 1 hour).",
                    vel_evids, ConfidenceLevel.HIGH, FindingClassification.SUPPORTED,
                )
                suspicious_signals.append(f"Severe authorization velocity burst ({v_val} txns/hr)")
                recommendations.append("Apply temporary token rate limit on payment instrument.")
            elif v_val >= 3:
                add_finding(
                    f"Elevated authorization frequency on payment instrument ({v_val} transactions within 1 hour).",
                    vel_evids, ConfidenceLevel.MEDIUM, FindingClassification.SUPPORTED,
                )
                suspicious_signals.append(f"Elevated payment instrument velocity ({v_val} txns/hr)")
                recommendations.append("Verify payment instrument authorization frequency across merchants.")

        # 4. Map Customer Baseline & Device Novelty Evidence
        dev_evids = [e.evidence_id for e in c.evidence_items if e.evidence_type == "device_novelty"]
        base_evids = [e.evidence_id for e in c.evidence_items if e.evidence_type == "customer_baseline"]

        if dev_evids and base_evids:
            add_finding(
                "Transaction was executed on an unrecognized device accompanied by spending significantly above customer historical baseline.",
                dev_evids + base_evids, ConfidenceLevel.HIGH, FindingClassification.SUPPORTED,
            )
            suspicious_signals.append("Unrecognized device paired with spending surge")
            recommendations.append("Contact customer via registered out-of-band channel to confirm transaction intent.")
        elif dev_evids:
            add_finding(
                "Transaction initiated from an unrecognized device token.",
                dev_evids, ConfidenceLevel.MEDIUM, FindingClassification.SUPPORTED,
            )
            suspicious_signals.append("New unrecognized device")

        # 5. Map Benign Signals
        benign_evids = [e.evidence_id for e in c.evidence_items if e.evidence_type == "benign_indicator"]
        for eid in benign_evids:
            item = evid_map[eid]
            benign_signals.append(item.description)

        if benign_evids and not suspicious_signals:
            add_finding(
                "Entity connectivity and spending patterns are consistent with normal legitimate behavior.",
                benign_evids, ConfidenceLevel.HIGH, FindingClassification.SUPPORTED,
            )

        # 6. Synthesize Hypotheses — Strictly Aligned with Policy Trigger & Confirmed Evidence
        hyp_candidates: list[tuple[int, Hypothesis]] = []

        # Check A: Coordinated Syndicate
        if c.primary_trigger in ("SEVERE_GRAPH_RING_SYNDICATE", "ELEVATED_GRAPH_RING_SCORE", "COMPOUND_ML_GRAPH_SYNDICATE") or c.graph_ring_score >= 0.30:
            priority_score = 10 if c.primary_trigger in ("SEVERE_GRAPH_RING_SYNDICATE", "ELEVATED_GRAPH_RING_SCORE") else 5
            hyp_candidates.append((
                priority_score,
                Hypothesis(
                    hypothesis_id="HYP-001",
                    hypothesis="Coordinated Multi-Accounting Syndicate: Collusive ring sharing devices and payment credentials.",
                    supporting_evidence_ids=graph_evids,
                    contradicting_evidence_ids=benign_evids,
                    confidence=ConfidenceLevel.HIGH if c.graph_ring_score >= 0.50 else ConfidenceLevel.MEDIUM,
                )
            ))

        # Check B: Card Testing / Velocity Burst
        if c.primary_trigger in ("SEVERE_PI_VELOCITY", "MODERATE_PI_VELOCITY") or any("authorization burst" in s for s in suspicious_signals):
            priority_score = 10 if c.primary_trigger in ("SEVERE_PI_VELOCITY", "MODERATE_PI_VELOCITY") else 6
            hyp_candidates.append((
                priority_score,
                Hypothesis(
                    hypothesis_id="HYP-002",
                    hypothesis="Card Testing / Automated Velocity Attack: Bot script testing stolen payment instrument.",
                    supporting_evidence_ids=vel_evids + ml_evids,
                    contradicting_evidence_ids=benign_evids,
                    confidence=ConfidenceLevel.HIGH if any("Severe" in e.description for e in c.evidence_items if e.evidence_type == "velocity") else ConfidenceLevel.MEDIUM,
                )
            ))

        # Check C: Account Takeover (ATO)
        if c.primary_trigger in ("HIGH_CONFIDENCE_ML_RISK", "SEVERE_AMOUNT_ANOMALY") or "Unrecognized device paired with spending surge" in suspicious_signals or (dev_evids and c.ml_probability >= 0.40):
            priority_score = 10 if c.primary_trigger in ("HIGH_CONFIDENCE_ML_RISK", "SEVERE_AMOUNT_ANOMALY") else 7
            hyp_candidates.append((
                priority_score,
                Hypothesis(
                    hypothesis_id="HYP-003",
                    hypothesis="Account Takeover (ATO): Unauthorized party accessing customer profile via new device.",
                    supporting_evidence_ids=dev_evids + base_evids + ml_evids,
                    contradicting_evidence_ids=benign_evids,
                    confidence=ConfidenceLevel.HIGH if c.ml_probability >= 0.70 else ConfidenceLevel.MEDIUM,
                )
            ))

        # Check D: General Fallback
        if not hyp_candidates:
            if c.policy_decision == "HOLD":
                hyp_candidates.append((
                    1,
                    Hypothesis(
                        hypothesis_id="HYP-004",
                        hypothesis="High-Risk Behavioral Anomaly: Unprecedented combination of risk factors.",
                        supporting_evidence_ids=[e.evidence_id for e in c.evidence_items if e.evidence_type in ("ml_score", "graph_topology", "velocity", "customer_baseline")],
                        contradicting_evidence_ids=benign_evids,
                        confidence=ConfidenceLevel.MEDIUM,
                    )
                ))
            elif c.policy_decision == "REVIEW":
                hyp_candidates.append((
                    1,
                    Hypothesis(
                        hypothesis_id="HYP-004",
                        hypothesis="Borderline Transaction Anomaly: Elevated risk indicators requiring analyst review.",
                        supporting_evidence_ids=[e.evidence_id for e in c.evidence_items if e.evidence_type in ("ml_score", "graph_topology", "velocity", "customer_baseline")],
                        contradicting_evidence_ids=benign_evids,
                        confidence=ConfidenceLevel.MEDIUM,
                    )
                ))
            else:
                hyp_candidates.append((
                    1,
                    Hypothesis(
                        hypothesis_id="HYP-005",
                        hypothesis="Legitimate Activity: Shared household device or benign baseline variation.",
                        supporting_evidence_ids=benign_evids,
                        contradicting_evidence_ids=[],
                        confidence=ConfidenceLevel.HIGH if benign_evids else ConfidenceLevel.LOW,
                    )
                ))

        # Sort candidates so highest priority (matching primary policy trigger) is first
        hyp_candidates.sort(key=lambda x: x[0], reverse=True)
        hypotheses = [h for (_, h) in hyp_candidates]
        for idx, h in enumerate(hypotheses, 1):
            h.hypothesis_id = f"HYP-{idx:03d}"

        if not recommendations:
            recommendations = [
                "Review recent authorization history for customer account.",
                "Monitor device token for further multi-customer associations.",
            ]

        # Uncertainty Analysis
        uncertainty = (
            "Device sharing can occur legitimately in family households or shared workspaces. "
            "Velocity spikes may occasionally reflect rapid user re-attempts following temporary network drops."
        )

        risk_summary = (
            f"Case {c.case_id} intercepted under policy {c.policy_version} with decision {c.policy_decision}. "
            f"Primary trigger: {c.primary_trigger}. ML fraud probability: {c.ml_probability:.3f}, Graph ring score: {c.graph_ring_score:.2f}."
        )

        analyst_summary = (
            f"Transaction #{c.transaction_id} (INR {c.amount:.2f}) was flagged for {c.policy_decision} (Trigger: {c.primary_trigger}). "
            f"Key findings indicate {len(suspicious_signals)} suspicious risk signals and {len(benign_signals)} benign indicators. "
            f"Primary hypothesis: {hypotheses[0].hypothesis}."
        )

        return InvestigationReport(
            case_id=c.case_id,
            policy_decision=c.policy_decision,
            policy_version=c.policy_version,
            risk_summary=risk_summary,
            evidence=c.evidence_items,
            findings=findings,
            suspicious_signals=suspicious_signals,
            benign_signals=benign_signals,
            related_entities=c.related_entities,
            timeline=c.timeline,
            hypotheses=hypotheses,
            uncertainty=uncertainty,
            recommended_next_steps=recommendations,
            analyst_summary=analyst_summary,
            model_metadata={
                "provider": "MockInvestigationLLM",
                "model_version": "deterministic-v1",
                "evidence_items_count": len(c.evidence_items),
                "citations_valid": True,
            },
            investigation_status="COMPLETED",
        )
