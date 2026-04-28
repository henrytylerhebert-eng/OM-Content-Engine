"""Review queue item schema for portfolio workflow."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from src.models.portfolio_common import ProvenanceFields
from src.portfolio.constants import QueueStatus, ReviewSeverity, TruthStage


class ReviewQueueItem(ProvenanceFields, SQLModel):
    """Review task created from portfolio workflow stages."""

    id: str
    organization_id: Optional[str] = None
    entity_type: str
    entity_id: Optional[str] = None
    queue_reason_code: str
    severity: ReviewSeverity = Field(default=ReviewSeverity.MEDIUM)
    recommended_action: Optional[str] = None
    current_stage: TruthStage = Field(default=TruthStage.RAW_INPUT)
    target_stage: TruthStage = Field(default=TruthStage.REVIEWED_EVIDENCE)
    record_label: Optional[str] = None
    source_field: Optional[str] = None
    raw_value: Optional[str] = None
    owner: Optional[str] = None
    queue_status: QueueStatus = Field(default=QueueStatus.OPEN)
    opened_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None
    linked_discovery_source_id: Optional[str] = None
    linked_evidence_item_id: Optional[str] = None
    note: Optional[str] = None
