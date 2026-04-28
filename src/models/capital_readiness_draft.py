"""Capital readiness draft schema for portfolio workflow."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from src.models.portfolio_common import ReviewStateFields
from src.portfolio.constants import CapitalReadinessStatus, DraftStatus, ReportAudience, TruthStage


class CapitalReadinessDraft(ReviewStateFields, SQLModel):
    """Audience-specific capital-readiness draft built from linked workflow inputs."""

    id: str
    organization_id: str
    report_period: str
    audience: ReportAudience = Field(default=ReportAudience.INTERNAL)
    draft_status: DraftStatus = Field(default=DraftStatus.DRAFT)
    readiness_status: CapitalReadinessStatus = Field(default=CapitalReadinessStatus.NOT_YET_ASSESSED)
    primary_capital_path: Optional[str] = None
    secondary_capital_paths: list[str] = Field(default_factory=list)
    readiness_rationale: Optional[str] = None
    blocking_gaps: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)
    support_routing_recommendation: Optional[str] = None
    next_milestone: Optional[str] = None
    linked_domain_score_ids: list[str] = Field(default_factory=list)
    linked_discovery_source_ids: list[str] = Field(default_factory=list)
    linked_evidence_ids: list[str] = Field(default_factory=list)
    linked_review_queue_ids: list[str] = Field(default_factory=list)
    linked_assumption_ids: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    generated_by: Optional[str] = None
    truth_stage: TruthStage = Field(default=TruthStage.INTERPRETED_EVIDENCE)
