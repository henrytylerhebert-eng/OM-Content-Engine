"""Evidence normalization shells for the portfolio workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import Optional, Sequence

from src.models.assumption import Assumption
from src.models.discovery_source import DiscoverySource
from src.models.evidence_item import EvidenceItem
from src.models.review_queue_item import ReviewQueueItem
from src.portfolio.constants import DomainKey, EvidenceType, ReviewSeverity, TruthStage
from src.portfolio.review_queue import (
    build_missing_organization_link_item,
    build_review_queue_item,
    build_stage_promotion_item,
)


def _slug(value: object) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower())
    return text.strip("_") or "record"


def _dedupe_domains(
    primary_domain: DomainKey,
    secondary_domains: Sequence[DomainKey],
) -> list[DomainKey]:
    deduped: list[DomainKey] = []
    seen = {primary_domain.value}
    for domain in secondary_domains:
        if domain.value in seen:
            continue
        seen.add(domain.value)
        deduped.append(domain)
    return deduped


@dataclass(frozen=True)
class EvidenceExtractionTarget:
    """Explicit extraction target passed into the evidence normalization shell."""

    organization_id: Optional[str] = None
    evidence_type: EvidenceType = EvidenceType.OBSERVATION
    primary_domain: Optional[DomainKey] = None
    secondary_domains: list[DomainKey] = field(default_factory=list)
    evidence_statement: Optional[str] = None
    excerpt: Optional[str] = None
    observed_at: Optional[datetime] = None
    evidence_level: int = 0
    confidence_note: Optional[str] = None
    interpretation_note: Optional[str] = None
    assumption_title: Optional[str] = None
    assumption_statement: Optional[str] = None
    enqueue_for_review: bool = True
    target_id: Optional[str] = None


@dataclass
class EvidenceNormalizationResult:
    """Evidence normalization outputs for a single discovery source."""

    evidence_items: list[EvidenceItem] = field(default_factory=list)
    assumptions: list[Assumption] = field(default_factory=list)
    review_queue_items: list[ReviewQueueItem] = field(default_factory=list)


def normalize_evidence_targets(
    discovery_source: DiscoverySource,
    targets: Sequence[EvidenceExtractionTarget],
) -> EvidenceNormalizationResult:
    """Create evidence and assumption shells from explicit extraction targets."""

    result = EvidenceNormalizationResult()

    for index, target in enumerate(targets, start=1):
        organization_id = target.organization_id or discovery_source.organization_id
        target_id = target.target_id or "%s:%s" % (discovery_source.id, index)

        if not organization_id:
            result.review_queue_items.append(
                build_missing_organization_link_item(
                    entity_type="evidence_target",
                    entity_id=target_id,
                    record_label=discovery_source.title,
                    source_system=discovery_source.source_system,
                    source_table=discovery_source.source_table,
                    source_record_id=discovery_source.source_record_id,
                    source_url=discovery_source.source_url,
                    source_path=discovery_source.source_path,
                    linked_discovery_source_id=discovery_source.id,
                    note="Cannot create evidence until the discovery source is linked to a company.",
                )
            )
            continue

        if not (target.evidence_statement or target.excerpt):
            result.review_queue_items.append(
                build_review_queue_item(
                    organization_id=organization_id,
                    entity_type="evidence_target",
                    entity_id=target_id,
                    queue_reason_code="missing_evidence_statement",
                    severity=ReviewSeverity.HIGH,
                    recommended_action="Add a concrete evidence statement or source excerpt before normalizing this target.",
                    current_stage=TruthStage.RAW_INPUT,
                    target_stage=TruthStage.EXTRACTED_SIGNAL,
                    record_label=discovery_source.title,
                    source_system=discovery_source.source_system,
                    source_table=discovery_source.source_table,
                    source_record_id=discovery_source.source_record_id,
                    source_url=discovery_source.source_url,
                    source_path=discovery_source.source_path,
                    linked_discovery_source_id=discovery_source.id,
                    note="Evidence extraction target was empty.",
                )
            )
            continue

        if target.primary_domain is None:
            result.review_queue_items.append(
                build_review_queue_item(
                    organization_id=organization_id,
                    entity_type="evidence_target",
                    entity_id=target_id,
                    queue_reason_code="missing_primary_domain",
                    severity=ReviewSeverity.HIGH,
                    recommended_action="Assign one primary OM domain before using this evidence downstream.",
                    current_stage=TruthStage.RAW_INPUT,
                    target_stage=TruthStage.EXTRACTED_SIGNAL,
                    record_label=discovery_source.title,
                    source_system=discovery_source.source_system,
                    source_table=discovery_source.source_table,
                    source_record_id=discovery_source.source_record_id,
                    source_url=discovery_source.source_url,
                    source_path=discovery_source.source_path,
                    linked_discovery_source_id=discovery_source.id,
                    note="Evidence extraction target had no primary domain.",
                )
            )
            continue

        evidence_item = EvidenceItem(
            id="evidence:%s" % _slug(target_id),
            organization_id=organization_id,
            discovery_source_id=discovery_source.id,
            evidence_type=target.evidence_type,
            primary_domain=target.primary_domain,
            secondary_domains=_dedupe_domains(target.primary_domain, target.secondary_domains),
            evidence_statement=target.evidence_statement or str(target.excerpt or "").strip(),
            evidence_level=target.evidence_level,
            observed_at=target.observed_at or discovery_source.captured_at,
            excerpt=target.excerpt,
            confidence_note=target.confidence_note,
            interpretation_note=target.interpretation_note,
            source_system=discovery_source.source_system,
            source_table=discovery_source.source_table,
            source_record_id=discovery_source.source_record_id,
            source_document_id=discovery_source.source_document_id,
            source_url=discovery_source.source_url,
            source_path=discovery_source.source_path,
            row_hash=discovery_source.row_hash,
            captured_at=discovery_source.captured_at,
            ingested_at=discovery_source.ingested_at,
            provenance_note="Extracted from discovery source %s." % discovery_source.id,
            simulation_flag=discovery_source.simulation_flag,
        )
        result.evidence_items.append(evidence_item)

        if target.assumption_statement:
            assumption = Assumption(
                id="assumption:%s" % _slug(target_id),
                organization_id=organization_id,
                domain_key=target.primary_domain,
                title=target.assumption_title or "Working assumption for %s" % target.primary_domain.value,
                statement=target.assumption_statement,
                linked_evidence_ids=[evidence_item.id],
                source_system=discovery_source.source_system,
                source_table=discovery_source.source_table,
                source_record_id=discovery_source.source_record_id,
                source_document_id=discovery_source.source_document_id,
                source_url=discovery_source.source_url,
                source_path=discovery_source.source_path,
                row_hash=discovery_source.row_hash,
                captured_at=discovery_source.captured_at,
                ingested_at=discovery_source.ingested_at,
                provenance_note="Interpreted from discovery source %s." % discovery_source.id,
                simulation_flag=discovery_source.simulation_flag,
            )
            result.assumptions.append(assumption)
            evidence_item.linked_assumption_ids.append(assumption.id)

        if target.enqueue_for_review:
            result.review_queue_items.append(
                build_stage_promotion_item(
                    organization_id=organization_id,
                    entity_type="evidence_item",
                    entity_id=evidence_item.id,
                    current_stage=evidence_item.truth_stage,
                    target_stage=TruthStage.REVIEWED_EVIDENCE,
                    linked_discovery_source_id=discovery_source.id,
                    linked_evidence_item_id=evidence_item.id,
                    record_label=discovery_source.title,
                    note="Extracted evidence must be reviewed before it can be treated as reviewed evidence.",
                )
            )

    return result
