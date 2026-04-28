"""Discovery source schema for portfolio workflow intake."""

from __future__ import annotations

from typing import Any, Optional

from sqlmodel import Field, SQLModel

from src.models.portfolio_common import ProvenanceFields, ReviewStateFields
from src.portfolio.constants import DiscoverySourceKind, TruthStage


class DiscoverySource(ProvenanceFields, ReviewStateFields, SQLModel):
    """One intake artifact or raw record available for evidence extraction."""

    id: str
    organization_id: Optional[str] = None
    source_kind: DiscoverySourceKind = Field(default=DiscoverySourceKind.AIRTABLE_RECORD)
    title: Optional[str] = None
    description: Optional[str] = None
    external_source_id: Optional[str] = None
    ingestion_run_id: Optional[str] = None
    raw_payload_excerpt: Optional[dict[str, Any]] = None
    submitted_by: Optional[str] = None
    truth_stage: TruthStage = Field(default=TruthStage.RAW_INPUT)
