"""
SentinelRisk — Investigation Agent & Safeguards

Executes evidence-grounded investigations, enforces strict schema validation,
rejects hallucinated evidence citations, and guarantees policy decision preservation.
"""

import os
import logging
from backend.app.investigation.models import (
    InvestigationContext,
    InvestigationReport,
)
from backend.app.investigation.providers.base import BaseInvestigationLLM
from backend.app.investigation.providers.mock_provider import MockInvestigationLLM
from backend.app.investigation.providers.gemini_provider import GeminiInvestigationLLM

logger = logging.getLogger("sentinelrisk.investigation")


class InvestigationAgent:
    """Orchestrates LLM investigation with hallucination checks and policy preservation."""

    def __init__(self, provider: BaseInvestigationLLM | None = None):
        if provider is not None:
            self.provider = provider
        else:
            provider_type = os.getenv("INVESTIGATION_LLM_PROVIDER", "mock").lower()
            if provider_type == "gemini":
                self.provider = GeminiInvestigationLLM()
            else:
                self.provider = MockInvestigationLLM()

    def investigate(self, context: InvestigationContext) -> InvestigationReport:
        """
        Execute an evidence-grounded investigation on the provided context.
        Enforces strict safety and validation rules.
        """
        valid_evidence_ids = {e.evidence_id for e in context.evidence_items}

        try:
            report = self.provider.generate_report(context)

            # Safeguard 1: Strict Policy Decision Preservation
            # The LLM must NEVER modify or override the Stage 7 policy decision
            if report.policy_decision != context.policy_decision:
                logger.warning(
                    f"Policy override attempt detected from LLM ({report.policy_decision} != {context.policy_decision}). "
                    f"Preserving Stage 7 decision."
                )
                report.policy_decision = context.policy_decision

            # Safeguard 2: Hallucinated Evidence Citation Check
            # All cited evidence IDs must exist in the context
            for finding in report.findings:
                invalid_cites = [eid for eid in finding.evidence_ids if eid not in valid_evidence_ids]
                if invalid_cites:
                    logger.warning(f"Removing invalid/hallucinated evidence citations in {finding.finding_id}: {invalid_cites}")
                    finding.evidence_ids = [eid for eid in finding.evidence_ids if eid in valid_evidence_ids]

            for hyp in report.hypotheses:
                hyp.supporting_evidence_ids = [eid for eid in hyp.supporting_evidence_ids if eid in valid_evidence_ids]
                hyp.contradicting_evidence_ids = [eid for eid in hyp.contradicting_evidence_ids if eid in valid_evidence_ids]

            return report

        except Exception as e:
            logger.error(f"Investigation provider failed ({e}); producing safe degraded report.")
            # Safe degradation: Create minimal fallback report preserving policy decision
            return InvestigationReport(
                case_id=context.case_id,
                policy_decision=context.policy_decision,
                policy_version=context.policy_version,
                risk_summary=f"Investigation failed to complete ({str(e)}). Policy decision {context.policy_decision} preserved.",
                evidence=context.evidence_items,
                findings=[],
                suspicious_signals=["INVESTIGATION_SYSTEM_DEGRADED"],
                benign_signals=[],
                related_entities=context.related_entities,
                timeline=context.timeline,
                hypotheses=[],
                uncertainty="Automated synthesis unavailable; manual analyst review required.",
                recommended_next_steps=["Escalate to senior risk analyst for manual audit."],
                analyst_summary=f"Automated LLM investigation degraded. Retaining authoritative decision: {context.policy_decision}.",
                model_metadata={"error": str(e), "provider": type(self.provider).__name__},
                investigation_status="FAILED",
            )
