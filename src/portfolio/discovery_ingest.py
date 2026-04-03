"""Discovery source ingestion interfaces for the portfolio workflow scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import Iterable, Mapping, Optional

from src.ingest.airtable_import import RawImportRecord
from src.models.discovery_source import DiscoverySource
from src.models.review_queue_item import ReviewQueueItem
from src.portfolio.constants import DiscoverySourceKind
from src.portfolio.review_queue import (
    build_missing_organization_link_item,
    build_missing_source_locator_item,
)


def _slug(value: object) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower())
    return text.strip("_") or "record"


def _record_title(raw_record: RawImportRecord) -> Optional[str]:
    return (
        raw_record.raw.get("Company Name")
        or raw_record.raw.get("Organization Name")
        or raw_record.raw.get("Full Name")
        or raw_record.raw.get("Title")
        or raw_record.raw.get("Name")
        or raw_record.source_record_id
    )


@dataclass(frozen=True)
class DiscoverySourceInput:
    """Manual or connector-provided intake input before discovery-source creation."""

    source_kind: DiscoverySourceKind
    title: Optional[str] = None
    organization_id: Optional[str] = None
    description: Optional[str] = None
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
    raw_payload_excerpt: Optional[dict[str, object]] = None
    submitted_by: Optional[str] = None
    simulation_flag: bool = False
    external_source_id: Optional[str] = None
    ingestion_run_id: Optional[str] = None
    item_id: Optional[str] = None


@dataclass
class DiscoveryIngestionResult:
    """Discovery-source records plus review queue items produced during intake."""

    discovery_sources: list[DiscoverySource] = field(default_factory=list)
    review_queue_items: list[ReviewQueueItem] = field(default_factory=list)


def build_discovery_source_from_raw_record(
    raw_record: RawImportRecord,
    *,
    organization_id: Optional[str] = None,
    source_kind: DiscoverySourceKind = DiscoverySourceKind.AIRTABLE_RECORD,
    title: Optional[str] = None,
    description: Optional[str] = None,
    submitted_by: Optional[str] = None,
    simulation_flag: bool = False,
    item_id: Optional[str] = None,
) -> DiscoverySource:
    """Build a discovery-source schema from an existing landed raw record."""

    identifier = raw_record.source_record_id or raw_record.row_hash
    return DiscoverySource(
        id=item_id or "discovery_source:%s" % _slug(identifier),
        organization_id=organization_id,
        source_kind=source_kind,
        title=title or _record_title(raw_record),
        description=description,
        source_system=raw_record.source_system,
        source_table=raw_record.source_table,
        source_record_id=raw_record.source_record_id,
        source_path=raw_record.file_path,
        row_hash=raw_record.row_hash,
        ingested_at=datetime.fromisoformat(raw_record.imported_at),
        provenance_note="Created from landed raw source input.",
        raw_payload_excerpt=dict(raw_record.raw),
        submitted_by=submitted_by,
        simulation_flag=simulation_flag,
    )


def build_discovery_source_from_input(entry: DiscoverySourceInput) -> DiscoverySource:
    """Build a discovery-source schema from a manual or connector input."""

    identifier = entry.item_id or entry.source_record_id or entry.source_document_id or entry.source_url or entry.title
    return DiscoverySource(
        id=entry.item_id or "discovery_source:%s" % _slug(identifier),
        organization_id=entry.organization_id,
        source_kind=entry.source_kind,
        title=entry.title,
        description=entry.description,
        source_system=entry.source_system,
        source_table=entry.source_table,
        source_record_id=entry.source_record_id,
        source_document_id=entry.source_document_id,
        source_url=entry.source_url,
        source_path=entry.source_path,
        row_hash=entry.row_hash,
        captured_at=entry.captured_at,
        ingested_at=entry.ingested_at,
        provenance_note=entry.provenance_note,
        raw_payload_excerpt=entry.raw_payload_excerpt,
        submitted_by=entry.submitted_by,
        simulation_flag=entry.simulation_flag,
        external_source_id=entry.external_source_id,
        ingestion_run_id=entry.ingestion_run_id,
    )


def ingest_discovery_sources(
    *,
    raw_records: Iterable[RawImportRecord] = (),
    inputs: Iterable[DiscoverySourceInput] = (),
) -> DiscoveryIngestionResult:
    """Create discovery-source shells from landed records or explicit inputs."""

    result = DiscoveryIngestionResult()

    for raw_record in raw_records:
        discovery_source = build_discovery_source_from_raw_record(raw_record)
        result.discovery_sources.append(discovery_source)
        result.review_queue_items.extend(_intake_review_items(discovery_source))

    for entry in inputs:
        discovery_source = build_discovery_source_from_input(entry)
        result.discovery_sources.append(discovery_source)
        result.review_queue_items.extend(_intake_review_items(discovery_source))

    return result


def _has_source_locator(discovery_source: DiscoverySource) -> bool:
    return any(
        (
            discovery_source.source_record_id,
            discovery_source.source_document_id,
            discovery_source.source_url,
            discovery_source.source_path,
            discovery_source.row_hash,
        )
    )


def _intake_review_items(discovery_source: DiscoverySource) -> list[ReviewQueueItem]:
    items: list[ReviewQueueItem] = []

    if not discovery_source.organization_id:
        items.append(
            build_missing_organization_link_item(
                entity_type="discovery_source",
                entity_id=discovery_source.id,
                record_label=discovery_source.title,
                source_system=discovery_source.source_system,
                source_table=discovery_source.source_table,
                source_record_id=discovery_source.source_record_id,
                source_url=discovery_source.source_url,
                source_path=discovery_source.source_path,
                linked_discovery_source_id=discovery_source.id,
                note="Discovery source landed without a resolved company link.",
            )
        )

    if not _has_source_locator(discovery_source):
        items.append(
            build_missing_source_locator_item(
                entity_type="discovery_source",
                entity_id=discovery_source.id,
                record_label=discovery_source.title,
                source_system=discovery_source.source_system,
                note="Discovery source has no stable source locator yet.",
            )
        )

    return items
