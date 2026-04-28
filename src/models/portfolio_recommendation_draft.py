"""Rules-based internal recommendation draft for portfolio workflow."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from src.models.portfolio_common import ReviewStateFields
from src.portfolio.constants import DraftStatus, ReportAudience, TruthStage


class PortfolioRecommendationDraft(ReviewStateFields, SQLModel):
    """Internal, rules-based recommendation summary for one company and period."""

    id: str
    organization_id: str
    report_period: str
    audience: ReportAudience = Field(default=ReportAudience.INTERNAL)
    draft_status: DraftStatus = Field(default=DraftStatus.DRAFT)
    recommendation_method: str = Field(default="rules_based")
    boundary_note: str = Field(
        default="Rules-based recommendations remain draft operating guidance, not final truth."
    )
    top_risks: list[str] = Field(default_factory=list)
    strongest_signals: list[str] = Field(default_factory=list)
    next_validation_steps: list[str] = Field(default_factory=list)
    support_recommendations: list[str] = Field(default_factory=list)
    likely_near_term_capital_path_label: Optional[str] = None
    what_not_to_pursue_yet: list[str] = Field(default_factory=list)
    linked_domain_score_ids: list[str] = Field(default_factory=list)
    linked_capital_readiness_draft_ids: list[str] = Field(default_factory=list)
    linked_support_routing_draft_ids: list[str] = Field(default_factory=list)
    linked_milestone_draft_ids: list[str] = Field(default_factory=list)
    linked_discovery_source_ids: list[str] = Field(default_factory=list)
    linked_evidence_ids: list[str] = Field(default_factory=list)
    linked_review_queue_ids: list[str] = Field(default_factory=list)
    linked_assumption_ids: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    generated_by: Optional[str] = None
    truth_stage: TruthStage = Field(default=TruthStage.INTERPRETED_EVIDENCE)
