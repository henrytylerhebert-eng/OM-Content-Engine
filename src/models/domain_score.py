"""Domain score schema for portfolio workflow."""

from __future__ import annotations

from typing import Optional

from sqlmodel import Field, SQLModel

from src.models.portfolio_common import ProvenanceFields, ReviewStateFields
from src.portfolio.constants import DomainKey, ScoreConfidence, ScoreStatus, TruthStage


class DomainScore(ProvenanceFields, ReviewStateFields, SQLModel):
    """Score draft for one company-domain pair."""

    id: str
    organization_id: str
    domain_key: DomainKey
    score_status: ScoreStatus = Field(default=ScoreStatus.DRAFT)
    raw_score: Optional[int] = Field(default=None, ge=1, le=5)
    confidence: Optional[ScoreConfidence] = None
    evidence_level: int = Field(default=0, ge=0, le=7)
    rationale: Optional[str] = None
    key_gap: Optional[str] = None
    next_action: Optional[str] = None
    score_basis_evidence_ids: list[str] = Field(default_factory=list)
    pending_evidence_ids: list[str] = Field(default_factory=list)
    linked_review_queue_ids: list[str] = Field(default_factory=list)
    linked_assumption_ids: list[str] = Field(default_factory=list)
    generated_by: Optional[str] = None
    truth_stage: TruthStage = Field(default=TruthStage.INTERPRETED_EVIDENCE)
