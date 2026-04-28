"""Assumption schema for portfolio workflow."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from src.models.portfolio_common import ProvenanceFields, ReviewStateFields
from src.portfolio.constants import DomainKey, TruthStage


class Assumption(ProvenanceFields, ReviewStateFields, SQLModel):
    """Tracked founder or OM assumption linked to evidence."""

    id: str
    organization_id: str
    domain_key: DomainKey
    title: str
    statement: str
    assumption_type: str = "working_assumption"
    status: str = "open"
    owner: Optional[str] = None
    opened_at: Optional[datetime] = None
    last_reviewed_at: Optional[datetime] = None
    validation_plan: Optional[str] = None
    next_check_date: Optional[datetime] = None
    linked_evidence_ids: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    truth_stage: TruthStage = Field(default=TruthStage.INTERPRETED_EVIDENCE)
