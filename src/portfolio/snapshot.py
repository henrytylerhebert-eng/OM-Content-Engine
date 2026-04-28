"""Minimal portfolio snapshot assembly for one-company phase-one outputs."""

from __future__ import annotations

from typing import Optional, Sequence, TypeVar
import re

from src.models.assumption import Assumption
from src.models.capital_readiness_draft import CapitalReadinessDraft
from src.models.discovery_source import DiscoverySource
from src.models.domain_score import DomainScore
from src.models.evidence_item import EvidenceItem
from src.models.founder_report_draft import FounderReportDraft
from src.models.internal_report_draft import InternalReportDraft
from src.models.milestone_draft import MilestoneDraft
from src.models.portfolio_snapshot import PortfolioSnapshot
from src.models.review_queue_item import ReviewQueueItem
from src.models.support_routing_draft import SupportRoutingDraft
from src.portfolio.constants import DraftStatus, ScoreStatus, TruthStage


T = TypeVar("T")


def _slug(value: object) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower())
    return text.strip("_") or "record"


def _model_dump(model: object) -> object:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    if hasattr(model, "dict"):
        return model.dict()
    return model


def _unique_records(records: Sequence[T]) -> list[T]:
    unique: list[T] = []
    seen: set[str] = set()
    for record in records:
        record_id = getattr(record, "id", None)
        if record_id is None:
            unique.append(record)
            continue
        if str(record_id) in seen:
            continue
        seen.add(str(record_id))
        unique.append(record)
    return unique


def _validate_record_organization(record: object, organization_id: str, label: str) -> None:
    record_id = getattr(record, "id", label)
    record_organization_id = getattr(record, "organization_id", None)
    if record_organization_id != organization_id:
        raise ValueError(
            "%s %s does not belong to organization %s."
            % (label, record_id, organization_id)
        )


def _validate_report_period(record: object, report_period: str, label: str) -> None:
    record_id = getattr(record, "id", label)
    record_period = getattr(record, "report_period", None)
    if record_period != report_period:
        raise ValueError(
            "%s %s does not match report period %s."
            % (label, record_id, report_period)
        )


def _validate_review_ready_bundle_links(
    label: str,
    draft: Optional[FounderReportDraft | InternalReportDraft],
    domain_scores: Sequence[DomainScore],
    discovery_sources: Sequence[DiscoverySource],
    evidence_items: Sequence[EvidenceItem],
) -> None:
    if draft is None or draft.draft_status != DraftStatus.REVIEW_READY:
        return

    available_score_ids = {score.id for score in domain_scores}
    available_discovery_ids = {source.id for source in discovery_sources}
    available_evidence_ids = {item.id for item in evidence_items}

    missing_score_ids = sorted(set(draft.linked_domain_score_ids) - available_score_ids)
    if missing_score_ids:
        raise ValueError(
            "%s %s references linked score ids that are missing from the snapshot bundle: %s."
            % (label, draft.id, ", ".join(missing_score_ids))
        )

    missing_discovery_ids = sorted(set(draft.linked_discovery_source_ids) - available_discovery_ids)
    if missing_discovery_ids:
        raise ValueError(
            "%s %s references linked discovery source ids that are missing from the snapshot bundle: %s."
            % (label, draft.id, ", ".join(missing_discovery_ids))
        )

    missing_evidence_ids = sorted(set(draft.linked_evidence_ids) - available_evidence_ids)
    if missing_evidence_ids:
        raise ValueError(
            "%s %s references linked evidence ids that are missing from the snapshot bundle: %s."
            % (label, draft.id, ", ".join(missing_evidence_ids))
        )


def _validate_review_ready_capital_readiness_links(
    draft: CapitalReadinessDraft,
    domain_scores: Sequence[DomainScore],
    discovery_sources: Sequence[DiscoverySource],
    evidence_items: Sequence[EvidenceItem],
) -> None:
    if draft.draft_status != DraftStatus.REVIEW_READY:
        return

    available_scores = {score.id: score for score in domain_scores}
    available_discovery_ids = {source.id for source in discovery_sources}
    available_evidence = {item.id: item for item in evidence_items}

    missing_score_ids = sorted(set(draft.linked_domain_score_ids) - set(available_scores))
    if missing_score_ids:
        raise ValueError(
            "CapitalReadinessDraft %s references linked score ids that are missing from the snapshot bundle: %s."
            % (draft.id, ", ".join(missing_score_ids))
        )

    unsupported_score_ids = sorted(
        score_id
        for score_id in draft.linked_domain_score_ids
        if available_scores[score_id].score_status not in (ScoreStatus.REVIEW_READY, ScoreStatus.REVIEWED)
    )
    if unsupported_score_ids:
        raise ValueError(
            "CapitalReadinessDraft %s cannot be review_ready while linked domain scores remain draft: %s."
            % (draft.id, ", ".join(unsupported_score_ids))
        )

    missing_discovery_ids = sorted(set(draft.linked_discovery_source_ids) - available_discovery_ids)
    if missing_discovery_ids:
        raise ValueError(
            "CapitalReadinessDraft %s references linked discovery source ids that are missing from the snapshot bundle: %s."
            % (draft.id, ", ".join(missing_discovery_ids))
        )

    missing_evidence_ids = sorted(set(draft.linked_evidence_ids) - set(available_evidence))
    if missing_evidence_ids:
        raise ValueError(
            "CapitalReadinessDraft %s references linked evidence ids that are missing from the snapshot bundle: %s."
            % (draft.id, ", ".join(missing_evidence_ids))
        )

    unreviewed_linked_evidence_ids = sorted(
        evidence_id
        for evidence_id in draft.linked_evidence_ids
        if available_evidence[evidence_id].truth_stage != TruthStage.REVIEWED_EVIDENCE
    )
    if unreviewed_linked_evidence_ids:
        raise ValueError(
            "CapitalReadinessDraft %s cannot be review_ready while linked evidence is not reviewed: %s."
            % (draft.id, ", ".join(unreviewed_linked_evidence_ids))
        )


def _validate_review_ready_internal_draft_links(
    label: str,
    draft: SupportRoutingDraft | MilestoneDraft,
    domain_scores: Sequence[DomainScore],
    discovery_sources: Sequence[DiscoverySource],
    evidence_items: Sequence[EvidenceItem],
) -> None:
    if draft.draft_status != DraftStatus.REVIEW_READY:
        return

    available_scores = {score.id: score for score in domain_scores}
    available_discovery_ids = {source.id for source in discovery_sources}
    available_evidence = {item.id: item for item in evidence_items}

    missing_score_ids = sorted(set(draft.linked_domain_score_ids) - set(available_scores))
    if missing_score_ids:
        raise ValueError(
            "%s %s references linked score ids that are missing from the snapshot bundle: %s."
            % (label, draft.id, ", ".join(missing_score_ids))
        )

    unsupported_score_ids = sorted(
        score_id
        for score_id in draft.linked_domain_score_ids
        if available_scores[score_id].score_status not in (ScoreStatus.REVIEW_READY, ScoreStatus.REVIEWED)
    )
    if unsupported_score_ids:
        raise ValueError(
            "%s %s cannot be review_ready while linked domain scores remain draft: %s."
            % (label, draft.id, ", ".join(unsupported_score_ids))
        )

    missing_discovery_ids = sorted(set(draft.linked_discovery_source_ids) - available_discovery_ids)
    if missing_discovery_ids:
        raise ValueError(
            "%s %s references linked discovery source ids that are missing from the snapshot bundle: %s."
            % (label, draft.id, ", ".join(missing_discovery_ids))
        )

    missing_evidence_ids = sorted(set(draft.linked_evidence_ids) - set(available_evidence))
    if missing_evidence_ids:
        raise ValueError(
            "%s %s references linked evidence ids that are missing from the snapshot bundle: %s."
            % (label, draft.id, ", ".join(missing_evidence_ids))
        )

    unreviewed_linked_evidence_ids = sorted(
        evidence_id
        for evidence_id in draft.linked_evidence_ids
        if available_evidence[evidence_id].truth_stage != TruthStage.REVIEWED_EVIDENCE
    )
    if unreviewed_linked_evidence_ids:
        raise ValueError(
            "%s %s cannot be review_ready while linked evidence is not reviewed: %s."
            % (label, draft.id, ", ".join(unreviewed_linked_evidence_ids))
        )


def build_portfolio_snapshot_bundle(
    organization_id: str,
    report_period: str,
    discovery_sources: Sequence[DiscoverySource] = (),
    evidence_items: Sequence[EvidenceItem] = (),
    assumptions: Sequence[Assumption] = (),
    domain_scores: Sequence[DomainScore] = (),
    capital_readiness_drafts: Sequence[CapitalReadinessDraft] = (),
    support_routing_drafts: Sequence[SupportRoutingDraft] = (),
    milestone_drafts: Sequence[MilestoneDraft] = (),
    review_queue_items: Sequence[ReviewQueueItem] = (),
    founder_report_draft: Optional[FounderReportDraft] = None,
    internal_report_draft: Optional[InternalReportDraft] = None,
    assembled_by: Optional[str] = None,
) -> dict[str, object]:
    """Build an inspectable single-company snapshot bundle for phase-one portfolio outputs."""

    unique_discovery_sources = _unique_records(discovery_sources)
    unique_evidence_items = _unique_records(evidence_items)
    unique_assumptions = _unique_records(assumptions)
    unique_domain_scores = _unique_records(domain_scores)
    unique_capital_readiness_drafts = _unique_records(capital_readiness_drafts)
    unique_support_routing_drafts = _unique_records(support_routing_drafts)
    unique_milestone_drafts = _unique_records(milestone_drafts)
    unique_review_queue_items = _unique_records(review_queue_items)

    for discovery_source in unique_discovery_sources:
        _validate_record_organization(discovery_source, organization_id, "DiscoverySource")
    for evidence_item in unique_evidence_items:
        _validate_record_organization(evidence_item, organization_id, "EvidenceItem")
    for assumption in unique_assumptions:
        _validate_record_organization(assumption, organization_id, "Assumption")
    for domain_score in unique_domain_scores:
        _validate_record_organization(domain_score, organization_id, "DomainScore")
    for capital_readiness_draft in unique_capital_readiness_drafts:
        _validate_record_organization(capital_readiness_draft, organization_id, "CapitalReadinessDraft")
        _validate_report_period(capital_readiness_draft, report_period, "CapitalReadinessDraft")
        _validate_review_ready_capital_readiness_links(
            capital_readiness_draft,
            unique_domain_scores,
            unique_discovery_sources,
            unique_evidence_items,
        )
    for support_routing_draft in unique_support_routing_drafts:
        _validate_record_organization(support_routing_draft, organization_id, "SupportRoutingDraft")
        _validate_report_period(support_routing_draft, report_period, "SupportRoutingDraft")
        _validate_review_ready_internal_draft_links(
            "SupportRoutingDraft",
            support_routing_draft,
            unique_domain_scores,
            unique_discovery_sources,
            unique_evidence_items,
        )
    for milestone_draft in unique_milestone_drafts:
        _validate_record_organization(milestone_draft, organization_id, "MilestoneDraft")
        _validate_report_period(milestone_draft, report_period, "MilestoneDraft")
        _validate_review_ready_internal_draft_links(
            "MilestoneDraft",
            milestone_draft,
            unique_domain_scores,
            unique_discovery_sources,
            unique_evidence_items,
        )
    for review_queue_item in unique_review_queue_items:
        if review_queue_item.organization_id is not None:
            _validate_record_organization(review_queue_item, organization_id, "ReviewQueueItem")

    if founder_report_draft is not None:
        _validate_record_organization(founder_report_draft, organization_id, "FounderReportDraft")
        _validate_report_period(founder_report_draft, report_period, "FounderReportDraft")
    if internal_report_draft is not None:
        _validate_record_organization(internal_report_draft, organization_id, "InternalReportDraft")
        _validate_report_period(internal_report_draft, report_period, "InternalReportDraft")

    _validate_review_ready_bundle_links(
        "FounderReportDraft",
        founder_report_draft,
        unique_domain_scores,
        unique_discovery_sources,
        unique_evidence_items,
    )
    _validate_review_ready_bundle_links(
        "InternalReportDraft",
        internal_report_draft,
        unique_domain_scores,
        unique_discovery_sources,
        unique_evidence_items,
    )

    snapshot = PortfolioSnapshot(
        id="portfolio_snapshot:%s:%s" % (_slug(organization_id), _slug(report_period)),
        organization_id=organization_id,
        report_period=report_period,
        assembled_by=assembled_by,
        discovery_source_count=len(unique_discovery_sources),
        evidence_item_count=len(unique_evidence_items),
        reviewed_evidence_count=sum(
            1 for item in unique_evidence_items if item.truth_stage == TruthStage.REVIEWED_EVIDENCE
        ),
        pending_evidence_count=sum(
            1 for item in unique_evidence_items if item.truth_stage != TruthStage.REVIEWED_EVIDENCE
        ),
        assumption_count=len(unique_assumptions),
        domain_score_count=len(unique_domain_scores),
        review_ready_domain_score_count=sum(
            1 for score in unique_domain_scores if score.score_status == ScoreStatus.REVIEW_READY
        ),
        capital_readiness_draft_count=len(unique_capital_readiness_drafts),
        review_ready_capital_readiness_draft_count=sum(
            1 for draft in unique_capital_readiness_drafts if draft.draft_status == DraftStatus.REVIEW_READY
        ),
        support_routing_draft_count=len(unique_support_routing_drafts),
        review_ready_support_routing_draft_count=sum(
            1 for draft in unique_support_routing_drafts if draft.draft_status == DraftStatus.REVIEW_READY
        ),
        milestone_draft_count=len(unique_milestone_drafts),
        review_ready_milestone_draft_count=sum(
            1 for draft in unique_milestone_drafts if draft.draft_status == DraftStatus.REVIEW_READY
        ),
        review_queue_item_count=len(unique_review_queue_items),
        founder_report_draft_id=None if founder_report_draft is None else founder_report_draft.id,
        founder_report_draft_status=None if founder_report_draft is None else founder_report_draft.draft_status,
        internal_report_draft_id=None if internal_report_draft is None else internal_report_draft.id,
        internal_report_draft_status=None if internal_report_draft is None else internal_report_draft.draft_status,
    )

    return {
        "portfolio_snapshot": _model_dump(snapshot),
        "discovery_sources": [_model_dump(record) for record in unique_discovery_sources],
        "evidence_items": [_model_dump(record) for record in unique_evidence_items],
        "assumptions": [_model_dump(record) for record in unique_assumptions],
        "domain_scores": [_model_dump(record) for record in unique_domain_scores],
        "capital_readiness_drafts": [_model_dump(record) for record in unique_capital_readiness_drafts],
        "support_routing_drafts": [_model_dump(record) for record in unique_support_routing_drafts],
        "milestone_drafts": [_model_dump(record) for record in unique_milestone_drafts],
        "review_queue_items": [_model_dump(record) for record in unique_review_queue_items],
        "founder_report_draft": _model_dump(founder_report_draft) if founder_report_draft is not None else None,
        "internal_report_draft": _model_dump(internal_report_draft) if internal_report_draft is not None else None,
    }
