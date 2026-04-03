"""Milestone draft schema for portfolio workflow."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from src.models.portfolio_common import ReviewStateFields
from src.portfolio.constants import DomainKey, DraftStatus, ReportAudience, TruthStage


class MilestoneDraft(ReviewStateFields, SQLModel):
    """Internal draft expressing the next milestone a company should hit."""

    id: str
    organization_id: str
    report_period: str
    audience: ReportAudience = Field(default=ReportAudience.INTERNAL)
    draft_status: DraftStatus = Field(default=DraftStatus.DRAFT)
    milestone_statement: str
    milestone_category: Optional[str] = None
    milestone_rationale: Optional[str] = None
    target_window: Optional[str] = None
    priority_domain: Optional[DomainKey] = None
    linked_domain_score_ids: list[str] = Field(default_factory=list)
    linked_capital_readiness_draft_ids: list[str] = Field(default_factory=list)
    linked_discovery_source_ids: list[str] = Field(default_factory=list)
    linked_evidence_ids: list[str] = Field(default_factory=list)
    linked_review_queue_ids: list[str] = Field(default_factory=list)
    linked_assumption_ids: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    generated_by: Optional[str] = None
    truth_stage: TruthStage = Field(default=TruthStage.INTERPRETED_EVIDENCE)
