"""Shared schema pieces for portfolio workflow records."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from src.portfolio.constants import ReviewStatus, TruthStage


class ProvenanceFields(SQLModel):
    """Reusable provenance fields for portfolio records."""

    source_system: Optional[str] = None
    source_table: Optional[str] = None
    source_record_id: Optional[str] = None
    source_document_id: Optional[str] = None
    source_url: Optional[str] = None
    source_path: Optional[str] = None
    row_hash: Optional[str] = None
    captured_at: Optional[datetime] = None
    ingested_at: Optional[datetime] = None
    provenance_note: Optional[str] = None
    simulation_flag: bool = False


class ReviewStateFields(SQLModel):
    """Reusable review-state fields for portfolio records."""

    truth_stage: TruthStage = Field(default=TruthStage.RAW_INPUT)
    review_status: ReviewStatus = Field(default=ReviewStatus.PENDING_REVIEW)
    review_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    internal_approved_by: Optional[str] = None
    internal_approved_at: Optional[datetime] = None
    external_approved_by: Optional[str] = None
    external_approved_at: Optional[datetime] = None
    suppressed_flag: bool = False
