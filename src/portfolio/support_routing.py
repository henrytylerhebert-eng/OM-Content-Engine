"""Support-routing draft assembly for the portfolio workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence
import re

from src.models.support_routing_draft import SupportRoutingDraft
from src.portfolio.constants import DomainKey, DraftStatus, ReportAudience


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
class SupportRoutingInput:
    """Explicit inputs for building an internal support-routing draft."""

    organization_id: str
    report_period: str
    route_recommendation: str
    audience: ReportAudience = ReportAudience.INTERNAL
    draft_status: DraftStatus = DraftStatus.DRAFT
    route_category: Optional[str] = None
    route_rationale: Optional[str] = None
    priority_domain: Optional[DomainKey] = None
    linked_domain_score_ids: list[str] = field(default_factory=list)
    linked_capital_readiness_draft_ids: list[str] = field(default_factory=list)
    linked_discovery_source_ids: list[str] = field(default_factory=list)
    linked_evidence_ids: list[str] = field(default_factory=list)
    linked_review_queue_ids: list[str] = field(default_factory=list)
    linked_assumption_ids: list[str] = field(default_factory=list)
    generated_by: Optional[str] = None
    draft_id: Optional[str] = None


def _validate_support_routing_input(support_input: SupportRoutingInput) -> None:
    if support_input.audience != ReportAudience.INTERNAL:
        raise ValueError("SupportRoutingDraft is limited to internal operational use in phase one.")

    if not str(support_input.route_recommendation or "").strip():
        raise ValueError("SupportRoutingDraft requires a route recommendation.")

    if support_input.draft_status != DraftStatus.REVIEW_READY:
        return

    if not _unique_ids(support_input.linked_domain_score_ids):
        raise ValueError("SupportRoutingDraft cannot be marked review_ready without linked domain score draft ids.")

    if not _unique_ids(support_input.linked_discovery_source_ids) and not _unique_ids(support_input.linked_evidence_ids):
        raise ValueError(
            "SupportRoutingDraft cannot be marked review_ready without linked discovery source ids or linked evidence ids."
        )

    if not str(support_input.route_rationale or "").strip():
        raise ValueError("SupportRoutingDraft cannot be marked review_ready without a route rationale.")


def build_support_routing_draft(support_input: SupportRoutingInput) -> SupportRoutingDraft:
    """Assemble an internal support-routing draft from explicit linked inputs."""

    _validate_support_routing_input(support_input)

    return SupportRoutingDraft(
        id=support_input.draft_id
        or "support_routing:%s:%s" % (_slug(support_input.organization_id), _slug(support_input.report_period)),
        organization_id=support_input.organization_id,
        report_period=support_input.report_period,
        audience=support_input.audience,
        draft_status=support_input.draft_status,
        route_recommendation=support_input.route_recommendation.strip(),
        route_category=support_input.route_category,
        route_rationale=support_input.route_rationale,
        priority_domain=support_input.priority_domain,
        linked_domain_score_ids=_unique_ids(support_input.linked_domain_score_ids),
        linked_capital_readiness_draft_ids=_unique_ids(support_input.linked_capital_readiness_draft_ids),
        linked_discovery_source_ids=_unique_ids(support_input.linked_discovery_source_ids),
        linked_evidence_ids=_unique_ids(support_input.linked_evidence_ids),
        linked_review_queue_ids=_unique_ids(support_input.linked_review_queue_ids),
        linked_assumption_ids=_unique_ids(support_input.linked_assumption_ids),
        generated_by=support_input.generated_by,
    )
