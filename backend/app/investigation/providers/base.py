"""
SentinelRisk — Investigation LLM Provider Abstraction

Defines the abstract base class for LLM investigation providers.
"""

from abc import ABC, abstractmethod
from backend.app.investigation.models import InvestigationContext, InvestigationReport


class BaseInvestigationLLM(ABC):
    """Abstract interface for LLM investigation report generators."""

    @abstractmethod
    def generate_report(self, context: InvestigationContext) -> InvestigationReport:
        """
        Generate an evidence-grounded, structured investigation report.

        Args:
            context: Controlled InvestigationContext containing facts and evidence items.
        Returns:
            Validated InvestigationReport.
        """
        pass
