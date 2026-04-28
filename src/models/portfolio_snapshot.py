"""Portfolio snapshot summary schema for bundled portfolio outputs."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from src.portfolio.constants import DraftStatus


class PortfolioSnapshot(SQLModel):
    """Inspectable metadata summary for a single-company portfolio snapshot bundle."""

    id: str
    organization_id: str
    report_period: str
    source_truth_statement: str = Field(
        default="Real discovery inputs remain the source of truth for phase one."
    )
    draft_boundary_statement: str = Field(
        default="Bundled score, readiness, and report outputs remain drafts until separately reviewed or approved."
    )
    assembled_at: datetime = Field(default_factory=datetime.utcnow)
    assembled_by: Optional[str] = None
    discovery_source_count: int = 0
    evidence_item_count: int = 0
    reviewed_evidence_count: int = 0
    pending_evidence_count: int = 0
    assumption_count: int = 0
    domain_score_count: int = 0
    review_ready_domain_score_count: int = 0
    capital_readiness_draft_count: int = 0
    review_ready_capital_readiness_draft_count: int = 0
    support_routing_draft_count: int = 0
    review_ready_support_routing_draft_count: int = 0
    milestone_draft_count: int = 0
    review_ready_milestone_draft_count: int = 0
    review_queue_item_count: int = 0
    portfolio_recommendation_draft_id: Optional[str] = None
    portfolio_recommendation_draft_status: Optional[DraftStatus] = None
    founder_report_draft_id: Optional[str] = None
    founder_report_draft_status: Optional[DraftStatus] = None
    internal_report_draft_id: Optional[str] = None
    internal_report_draft_status: Optional[DraftStatus] = None
