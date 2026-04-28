"""Evidence item schema for portfolio workflow."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from src.models.portfolio_common import ProvenanceFields, ReviewStateFields
from src.portfolio.constants import DomainKey, EvidenceType, TruthStage


class EvidenceItem(ProvenanceFields, ReviewStateFields, SQLModel):
    """Normalized evidence statement tied to one company and domain."""

    id: str
    organization_id: str
    discovery_source_id: str
    evidence_type: EvidenceType = Field(default=EvidenceType.OBSERVATION)
    primary_domain: DomainKey
    secondary_domains: list[DomainKey] = Field(default_factory=list)
    evidence_statement: str
    evidence_level: int = Field(default=0, ge=0, le=7)
    observed_at: Optional[datetime] = None
    excerpt: Optional[str] = None
    confidence_note: Optional[str] = None
    interpretation_note: Optional[str] = None
    linked_assumption_ids: list[str] = Field(default_factory=list)
    truth_stage: TruthStage = Field(default=TruthStage.EXTRACTED_SIGNAL)
