"""Founder-facing report draft schema for portfolio workflow."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from src.models.portfolio_common import ReviewStateFields
from src.portfolio.constants import DraftStatus, ReportAudience, TruthStage


class FounderReportDraft(ReviewStateFields, SQLModel):
    """Founder-facing summary shell built from linked portfolio inputs."""

    id: str
    organization_id: str
    report_period: str
    audience: ReportAudience = Field(default=ReportAudience.FOUNDER)
    draft_status: DraftStatus = Field(default=DraftStatus.DRAFT)
    strengths: list[str] = Field(default_factory=list)
    top_gaps: list[str] = Field(default_factory=list)
    evidence_improving: list[str] = Field(default_factory=list)
    milestones: list[str] = Field(default_factory=list)
    recommended_next_actions: list[str] = Field(default_factory=list)
    capital_readiness_summary: Optional[str] = None
    linked_domain_score_ids: list[str] = Field(default_factory=list)
    linked_capital_readiness_draft_ids: list[str] = Field(default_factory=list)
    linked_discovery_source_ids: list[str] = Field(default_factory=list)
    linked_evidence_ids: list[str] = Field(default_factory=list)
    linked_review_queue_ids: list[str] = Field(default_factory=list)
    linked_assumption_ids: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    generated_by: Optional[str] = None
    truth_stage: TruthStage = Field(default=TruthStage.INTERPRETED_EVIDENCE)
