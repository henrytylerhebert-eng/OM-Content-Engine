"""Review queue helpers for portfolio workflow records."""

from __future__ import annotations

from datetime import datetime
import re
from typing import Optional

from src.models.review_queue_item import ReviewQueueItem
from src.portfolio.constants import ReviewSeverity, TruthStage
from src.transform.review_flags import ReviewFlag


def _slug(value: object) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower())
    return text.strip("_") or "record"


def build_review_queue_item(
    *,
    organization_id: Optional[str],
    entity_type: str,
    entity_id: Optional[str],
    queue_reason_code: str,
    severity: ReviewSeverity = ReviewSeverity.MEDIUM,
    recommended_action: Optional[str] = None,
    current_stage: TruthStage = TruthStage.RAW_INPUT,
    target_stage: TruthStage = TruthStage.REVIEWED_EVIDENCE,
    record_label: Optional[str] = None,
    source_system: Optional[str] = None,
    source_table: Optional[str] = None,
    source_record_id: Optional[str] = None,
    source_url: Optional[str] = None,
    source_path: Optional[str] = None,
    source_field: Optional[str] = None,
    raw_value: Optional[object] = None,
    linked_discovery_source_id: Optional[str] = None,
    linked_evidence_item_id: Optional[str] = None,
    note: Optional[str] = None,
    item_id: Optional[str] = None,
    opened_at: Optional[datetime] = None,
) -> ReviewQueueItem:
    """Build a portfolio review queue item with preserved source context."""

    queue_id = item_id or "review:%s:%s:%s" % (
        entity_type,
        _slug(entity_id or linked_discovery_source_id or source_record_id),
        _slug(queue_reason_code),
    )
    return ReviewQueueItem(
        id=queue_id,
        organization_id=organization_id,
        entity_type=entity_type,
        entity_id=entity_id,
        queue_reason_code=queue_reason_code,
        severity=severity,
        recommended_action=recommended_action,
        current_stage=current_stage,
        target_stage=target_stage,
        record_label=record_label,
        source_system=source_system,
        source_table=source_table,
        source_record_id=source_record_id,
        source_url=source_url,
        source_path=source_path,
        source_field=source_field,
        raw_value=None if raw_value is None else str(raw_value),
        linked_discovery_source_id=linked_discovery_source_id,
        linked_evidence_item_id=linked_evidence_item_id,
        note=note,
        opened_at=opened_at or datetime.utcnow(),
    )


def build_review_queue_item_from_flag(
    flag: ReviewFlag,
    *,
    organization_id: Optional[str],
    entity_type: str,
    entity_id: Optional[str] = None,
    current_stage: TruthStage = TruthStage.RAW_INPUT,
    target_stage: TruthStage = TruthStage.REVIEWED_EVIDENCE,
    linked_discovery_source_id: Optional[str] = None,
    linked_evidence_item_id: Optional[str] = None,
) -> ReviewQueueItem:
    """Convert an existing normalization flag into a portfolio review queue item."""

    return build_review_queue_item(
        organization_id=organization_id,
        entity_type=entity_type,
        entity_id=entity_id,
        queue_reason_code=flag.code,
        severity=ReviewSeverity(flag.severity),
        recommended_action=flag.recommended_action,
        current_stage=current_stage,
        target_stage=target_stage,
        record_label=flag.record_label,
        source_system=flag.source_system,
        source_table=flag.source_table,
        source_record_id=flag.source_record_id,
        source_field=flag.source_field,
        raw_value=flag.raw_value,
        linked_discovery_source_id=linked_discovery_source_id,
        linked_evidence_item_id=linked_evidence_item_id,
        note=flag.note or flag.description,
    )


def build_stage_promotion_item(
    *,
    organization_id: Optional[str],
    entity_type: str,
    entity_id: str,
    current_stage: TruthStage,
    target_stage: TruthStage,
    linked_discovery_source_id: Optional[str] = None,
    linked_evidence_item_id: Optional[str] = None,
    record_label: Optional[str] = None,
    note: Optional[str] = None,
) -> ReviewQueueItem:
    """Queue a deliberate review step before a record can be promoted."""

    return build_review_queue_item(
        organization_id=organization_id,
        entity_type=entity_type,
        entity_id=entity_id,
        queue_reason_code="review_stage_promotion",
        severity=ReviewSeverity.MEDIUM,
        recommended_action="Review the record and explicitly approve promotion to the next truth stage.",
        current_stage=current_stage,
        target_stage=target_stage,
        record_label=record_label,
        linked_discovery_source_id=linked_discovery_source_id,
        linked_evidence_item_id=linked_evidence_item_id,
        note=note,
    )


def build_missing_organization_link_item(
    *,
    entity_type: str,
    entity_id: str,
    record_label: Optional[str],
    source_system: Optional[str] = None,
    source_table: Optional[str] = None,
    source_record_id: Optional[str] = None,
    source_url: Optional[str] = None,
    source_path: Optional[str] = None,
    linked_discovery_source_id: Optional[str] = None,
    note: Optional[str] = None,
) -> ReviewQueueItem:
    """Queue a review item when discovery or evidence cannot be linked to a company."""

    return build_review_queue_item(
        organization_id=None,
        entity_type=entity_type,
        entity_id=entity_id,
        queue_reason_code="missing_organization_link",
        severity=ReviewSeverity.HIGH,
        recommended_action="Link this record to an Opportunity Machine company before using it downstream.",
        current_stage=TruthStage.RAW_INPUT,
        target_stage=TruthStage.EXTRACTED_SIGNAL,
        record_label=record_label,
        source_system=source_system,
        source_table=source_table,
        source_record_id=source_record_id,
        source_url=source_url,
        source_path=source_path,
        linked_discovery_source_id=linked_discovery_source_id,
        note=note,
    )


def build_missing_source_locator_item(
    *,
    entity_type: str,
    entity_id: str,
    record_label: Optional[str],
    source_system: Optional[str] = None,
    note: Optional[str] = None,
) -> ReviewQueueItem:
    """Queue a review item when the source cannot be traced back safely."""

    return build_review_queue_item(
        organization_id=None,
        entity_type=entity_type,
        entity_id=entity_id,
        queue_reason_code="missing_source_locator",
        severity=ReviewSeverity.HIGH,
        recommended_action="Add a usable source locator before treating this record as evidence-ready input.",
        current_stage=TruthStage.RAW_INPUT,
        target_stage=TruthStage.RAW_INPUT,
        record_label=record_label,
        source_system=source_system,
        note=note,
    )
