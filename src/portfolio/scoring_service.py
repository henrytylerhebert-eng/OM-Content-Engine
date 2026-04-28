"""Conservative score-draft assembly for the portfolio workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Optional, Sequence

from src.models.domain_score import DomainScore
from src.models.evidence_item import EvidenceItem
from src.models.review_queue_item import ReviewQueueItem
from src.portfolio.constants import (
    DomainKey,
    ReviewStatus,
    ScoreConfidence,
    ScoreStatus,
    TruthStage,
)


def _slug(value: object) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower())
    return text.strip("_") or "record"


def _unique_ids(values: Sequence[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)
    return cleaned


def _matches_domain(evidence_item: EvidenceItem, domain_key: DomainKey) -> bool:
    if evidence_item.primary_domain == domain_key:
        return True
    return any(domain == domain_key for domain in evidence_item.secondary_domains)


def _is_reviewed_evidence(evidence_item: EvidenceItem) -> bool:
    return (
        evidence_item.truth_stage
        in {
            TruthStage.REVIEWED_EVIDENCE,
            TruthStage.INTERNALLY_APPROVED_OUTPUT,
            TruthStage.EXTERNALLY_APPROVED_OUTPUT,
        }
        and evidence_item.review_status
        in {
            ReviewStatus.REVIEWED,
            ReviewStatus.INTERNALLY_APPROVED,
            ReviewStatus.EXTERNALLY_APPROVED,
        }
    )


@dataclass(frozen=True)
class DomainScoreInput:
    """Explicit inputs used to create or update a domain score draft."""

    organization_id: str
    domain_key: DomainKey
    raw_score: Optional[int] = None
    confidence: Optional[ScoreConfidence] = None
    evidence_level: Optional[int] = None
    rationale: Optional[str] = None
    key_gap: Optional[str] = None
    next_action: Optional[str] = None
    linked_assumption_ids: list[str] = field(default_factory=list)
    generated_by: Optional[str] = None
    score_id: Optional[str] = None


def _review_queue_links(
    *,
    organization_id: str,
    evidence_ids: Sequence[str],
    review_queue_items: Sequence[ReviewQueueItem],
) -> list[str]:
    evidence_id_set = set(evidence_ids)
    linked: list[str] = []
    for item in review_queue_items:
        if item.organization_id not in (None, organization_id):
            continue
        if item.linked_evidence_item_id and item.linked_evidence_item_id in evidence_id_set:
            linked.append(item.id)
            continue
        if item.entity_type == "domain_score" and item.entity_id:
            linked.append(item.id)
    return _unique_ids(linked)


def build_domain_score_draft(
    score_input: DomainScoreInput,
    *,
    evidence_items: Sequence[EvidenceItem] = (),
    review_queue_items: Sequence[ReviewQueueItem] = (),
) -> DomainScore:
    """Create a score draft grounded only in reviewed evidence."""

    matched_evidence = [
        item
        for item in evidence_items
        if item.organization_id == score_input.organization_id and _matches_domain(item, score_input.domain_key)
    ]
    reviewed_evidence = [item for item in matched_evidence if _is_reviewed_evidence(item)]
    pending_evidence = [item for item in matched_evidence if not _is_reviewed_evidence(item)]

    if score_input.raw_score is not None and not reviewed_evidence:
        raise ValueError("Domain score drafts with a raw score must be grounded in reviewed evidence.")
    if score_input.confidence is not None and score_input.raw_score is None:
        raise ValueError("Confidence may only be set when a raw score draft is present.")

    basis_evidence_ids = _unique_ids([item.id for item in reviewed_evidence])
    pending_evidence_ids = _unique_ids([item.id for item in pending_evidence])
    evidence_level = (
        score_input.evidence_level
        if score_input.evidence_level is not None
        else max((item.evidence_level for item in reviewed_evidence), default=0)
    )
    score_status = ScoreStatus.DRAFT
    if reviewed_evidence and not pending_evidence:
        score_status = ScoreStatus.REVIEW_READY

    return DomainScore(
        id=score_input.score_id
        or "domain_score:%s:%s" % (_slug(score_input.organization_id), score_input.domain_key.value),
        organization_id=score_input.organization_id,
        domain_key=score_input.domain_key,
        score_status=score_status,
        raw_score=score_input.raw_score,
        confidence=score_input.confidence,
        evidence_level=evidence_level,
        rationale=score_input.rationale,
        key_gap=score_input.key_gap,
        next_action=score_input.next_action,
        score_basis_evidence_ids=basis_evidence_ids,
        pending_evidence_ids=pending_evidence_ids,
        linked_review_queue_ids=_review_queue_links(
            organization_id=score_input.organization_id,
            evidence_ids=basis_evidence_ids + pending_evidence_ids,
            review_queue_items=review_queue_items,
        ),
        linked_assumption_ids=_unique_ids(score_input.linked_assumption_ids),
        generated_by=score_input.generated_by,
        provenance_note="Score draft assembled from linked evidence and review-state inputs.",
    )


def update_domain_score_draft(
    existing_score: DomainScore,
    *,
    raw_score: Optional[int] = None,
    confidence: Optional[ScoreConfidence] = None,
    evidence_level: Optional[int] = None,
    rationale: Optional[str] = None,
    key_gap: Optional[str] = None,
    next_action: Optional[str] = None,
    linked_assumption_ids: Optional[Sequence[str]] = None,
    generated_by: Optional[str] = None,
    evidence_items: Sequence[EvidenceItem] = (),
    review_queue_items: Sequence[ReviewQueueItem] = (),
) -> DomainScore:
    """Refresh a score draft while preserving score-basis linkage rules."""

    score_input = DomainScoreInput(
        organization_id=existing_score.organization_id,
        domain_key=existing_score.domain_key,
        raw_score=existing_score.raw_score if raw_score is None else raw_score,
        confidence=existing_score.confidence if confidence is None else confidence,
        evidence_level=existing_score.evidence_level if evidence_level is None else evidence_level,
        rationale=existing_score.rationale if rationale is None else rationale,
        key_gap=existing_score.key_gap if key_gap is None else key_gap,
        next_action=existing_score.next_action if next_action is None else next_action,
        linked_assumption_ids=list(existing_score.linked_assumption_ids if linked_assumption_ids is None else linked_assumption_ids),
        generated_by=existing_score.generated_by if generated_by is None else generated_by,
        score_id=existing_score.id,
    )
    updated_score = build_domain_score_draft(
        score_input,
        evidence_items=evidence_items,
        review_queue_items=review_queue_items,
    )
    updated_score.review_status = existing_score.review_status
    updated_score.truth_stage = existing_score.truth_stage
    updated_score.review_notes = existing_score.review_notes
    updated_score.reviewed_by = existing_score.reviewed_by
    updated_score.reviewed_at = existing_score.reviewed_at
    updated_score.internal_approved_by = existing_score.internal_approved_by
    updated_score.internal_approved_at = existing_score.internal_approved_at
    updated_score.external_approved_by = existing_score.external_approved_by
    updated_score.external_approved_at = existing_score.external_approved_at
    updated_score.suppressed_flag = existing_score.suppressed_flag
    return updated_score
