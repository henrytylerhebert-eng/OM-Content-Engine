"""Report draft assembly inputs for portfolio founder and internal summaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence
import re

from src.models.founder_report_draft import FounderReportDraft
from src.models.internal_report_draft import InternalReportDraft
from src.portfolio.constants import DomainKey, DraftStatus


def _slug(value: object) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower())
    return text.strip("_") or "record"


def _unique_strings(values: Sequence[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        cleaned.append(normalized)
    return cleaned


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


@dataclass(frozen=True)
class FounderSummaryInput:
    """Explicit sections supplied to the founder draft assembler."""

    organization_id: str
    report_period: str
    strengths: list[str] = field(default_factory=list)
    top_gaps: list[str] = field(default_factory=list)
    evidence_improving: list[str] = field(default_factory=list)
    milestones: list[str] = field(default_factory=list)
    recommended_next_actions: list[str] = field(default_factory=list)
    capital_readiness_summary: Optional[str] = None
    linked_domain_score_ids: list[str] = field(default_factory=list)
    linked_capital_readiness_draft_ids: list[str] = field(default_factory=list)
    linked_discovery_source_ids: list[str] = field(default_factory=list)
    linked_evidence_ids: list[str] = field(default_factory=list)
    linked_review_queue_ids: list[str] = field(default_factory=list)
    linked_assumption_ids: list[str] = field(default_factory=list)
    draft_status: DraftStatus = DraftStatus.DRAFT
    generated_by: Optional[str] = None


@dataclass(frozen=True)
class InternalSummaryInput:
    """Explicit sections supplied to the internal draft assembler."""

    organization_id: str
    report_period: str
    current_strengths: list[str] = field(default_factory=list)
    stuck_reasons: list[str] = field(default_factory=list)
    watchlist_status: Optional[str] = None
    recommended_support_route: Optional[str] = None
    milestone_status: Optional[str] = None
    capital_paths_considered: list[str] = field(default_factory=list)
    priority_domains: list[DomainKey] = field(default_factory=list)
    linked_domain_score_ids: list[str] = field(default_factory=list)
    linked_capital_readiness_draft_ids: list[str] = field(default_factory=list)
    linked_discovery_source_ids: list[str] = field(default_factory=list)
    linked_evidence_ids: list[str] = field(default_factory=list)
    linked_review_queue_ids: list[str] = field(default_factory=list)
    linked_assumption_ids: list[str] = field(default_factory=list)
    internal_notes: list[str] = field(default_factory=list)
    draft_status: DraftStatus = DraftStatus.DRAFT
    generated_by: Optional[str] = None


def _validate_review_ready_links(
    label: str,
    linked_domain_score_ids: Sequence[str],
    linked_discovery_source_ids: Sequence[str],
    linked_evidence_ids: Sequence[str],
    draft_status: DraftStatus,
) -> None:
    if draft_status != DraftStatus.REVIEW_READY:
        return

    if not _unique_ids(linked_domain_score_ids):
        raise ValueError("%s cannot be marked review_ready without linked domain score draft ids." % label)

    if not _unique_ids(linked_discovery_source_ids) and not _unique_ids(linked_evidence_ids):
        raise ValueError(
            "%s cannot be marked review_ready without linked discovery source ids or linked evidence ids."
            % label
        )


def build_founder_report_draft(summary_input: FounderSummaryInput) -> FounderReportDraft:
    """Assemble a founder-facing report draft from explicit input sections."""

    _validate_review_ready_links(
        "FounderReportDraft",
        summary_input.linked_domain_score_ids,
        summary_input.linked_discovery_source_ids,
        summary_input.linked_evidence_ids,
        summary_input.draft_status,
    )

    return FounderReportDraft(
        id="founder_report:%s:%s" % (
            _slug(summary_input.organization_id),
            _slug(summary_input.report_period),
        ),
        organization_id=summary_input.organization_id,
        report_period=summary_input.report_period,
        draft_status=summary_input.draft_status,
        strengths=_unique_strings(summary_input.strengths),
        top_gaps=_unique_strings(summary_input.top_gaps),
        evidence_improving=_unique_strings(summary_input.evidence_improving),
        milestones=_unique_strings(summary_input.milestones),
        recommended_next_actions=_unique_strings(summary_input.recommended_next_actions),
        capital_readiness_summary=summary_input.capital_readiness_summary,
        linked_domain_score_ids=_unique_ids(summary_input.linked_domain_score_ids),
        linked_capital_readiness_draft_ids=_unique_ids(summary_input.linked_capital_readiness_draft_ids),
        linked_discovery_source_ids=_unique_ids(summary_input.linked_discovery_source_ids),
        linked_evidence_ids=_unique_ids(summary_input.linked_evidence_ids),
        linked_review_queue_ids=_unique_ids(summary_input.linked_review_queue_ids),
        linked_assumption_ids=_unique_ids(summary_input.linked_assumption_ids),
        generated_by=summary_input.generated_by,
    )


def build_internal_report_draft(summary_input: InternalSummaryInput) -> InternalReportDraft:
    """Assemble an internal report draft from explicit input sections."""

    _validate_review_ready_links(
        "InternalReportDraft",
        summary_input.linked_domain_score_ids,
        summary_input.linked_discovery_source_ids,
        summary_input.linked_evidence_ids,
        summary_input.draft_status,
    )

    return InternalReportDraft(
        id="internal_report:%s:%s" % (
            _slug(summary_input.organization_id),
            _slug(summary_input.report_period),
        ),
        organization_id=summary_input.organization_id,
        report_period=summary_input.report_period,
        draft_status=summary_input.draft_status,
        current_strengths=_unique_strings(summary_input.current_strengths),
        stuck_reasons=_unique_strings(summary_input.stuck_reasons),
        watchlist_status=summary_input.watchlist_status,
        recommended_support_route=summary_input.recommended_support_route,
        milestone_status=summary_input.milestone_status,
        capital_paths_considered=_unique_strings(summary_input.capital_paths_considered),
        priority_domains=summary_input.priority_domains,
        linked_domain_score_ids=_unique_ids(summary_input.linked_domain_score_ids),
        linked_capital_readiness_draft_ids=_unique_ids(summary_input.linked_capital_readiness_draft_ids),
        linked_discovery_source_ids=_unique_ids(summary_input.linked_discovery_source_ids),
        linked_evidence_ids=_unique_ids(summary_input.linked_evidence_ids),
        linked_review_queue_ids=_unique_ids(summary_input.linked_review_queue_ids),
        linked_assumption_ids=_unique_ids(summary_input.linked_assumption_ids),
        internal_notes=_unique_strings(summary_input.internal_notes),
        generated_by=summary_input.generated_by,
    )
