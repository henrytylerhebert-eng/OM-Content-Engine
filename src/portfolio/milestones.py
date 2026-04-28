"""Milestone draft assembly for the portfolio workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence
import re

from src.models.milestone_draft import MilestoneDraft
from src.portfolio.constants import DomainKey, DraftStatus, ReportAudience


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


@dataclass(frozen=True)
class MilestoneInput:
    """Explicit inputs for building an internal milestone draft."""

    organization_id: str
    report_period: str
    milestone_statement: str
    audience: ReportAudience = ReportAudience.INTERNAL
    draft_status: DraftStatus = DraftStatus.DRAFT
    milestone_category: Optional[str] = None
    milestone_rationale: Optional[str] = None
    target_window: Optional[str] = None
    priority_domain: Optional[DomainKey] = None
    linked_domain_score_ids: list[str] = field(default_factory=list)
    linked_capital_readiness_draft_ids: list[str] = field(default_factory=list)
    linked_discovery_source_ids: list[str] = field(default_factory=list)
    linked_evidence_ids: list[str] = field(default_factory=list)
    linked_review_queue_ids: list[str] = field(default_factory=list)
    linked_assumption_ids: list[str] = field(default_factory=list)
    generated_by: Optional[str] = None
    draft_id: Optional[str] = None


def _validate_milestone_input(milestone_input: MilestoneInput) -> None:
    if milestone_input.audience != ReportAudience.INTERNAL:
        raise ValueError("MilestoneDraft is limited to internal operational use in phase one.")

    if not str(milestone_input.milestone_statement or "").strip():
        raise ValueError("MilestoneDraft requires a milestone statement.")

    if milestone_input.draft_status != DraftStatus.REVIEW_READY:
        return

    if not _unique_ids(milestone_input.linked_domain_score_ids):
        raise ValueError("MilestoneDraft cannot be marked review_ready without linked domain score draft ids.")

    if not _unique_ids(milestone_input.linked_discovery_source_ids) and not _unique_ids(milestone_input.linked_evidence_ids):
        raise ValueError(
            "MilestoneDraft cannot be marked review_ready without linked discovery source ids or linked evidence ids."
        )

    if not str(milestone_input.milestone_rationale or "").strip():
        raise ValueError("MilestoneDraft cannot be marked review_ready without a milestone rationale.")


def build_milestone_draft(milestone_input: MilestoneInput) -> MilestoneDraft:
    """Assemble an internal milestone draft from explicit linked inputs."""

    _validate_milestone_input(milestone_input)

    return MilestoneDraft(
        id=milestone_input.draft_id
        or "milestone:%s:%s" % (_slug(milestone_input.organization_id), _slug(milestone_input.report_period)),
        organization_id=milestone_input.organization_id,
        report_period=milestone_input.report_period,
        audience=milestone_input.audience,
        draft_status=milestone_input.draft_status,
        milestone_statement=milestone_input.milestone_statement.strip(),
        milestone_category=milestone_input.milestone_category,
        milestone_rationale=milestone_input.milestone_rationale,
        target_window=milestone_input.target_window,
        priority_domain=milestone_input.priority_domain,
        linked_domain_score_ids=_unique_ids(milestone_input.linked_domain_score_ids),
        linked_capital_readiness_draft_ids=_unique_ids(milestone_input.linked_capital_readiness_draft_ids),
        linked_discovery_source_ids=_unique_ids(milestone_input.linked_discovery_source_ids),
        linked_evidence_ids=_unique_ids(milestone_input.linked_evidence_ids),
        linked_review_queue_ids=_unique_ids(milestone_input.linked_review_queue_ids),
        linked_assumption_ids=_unique_ids(milestone_input.linked_assumption_ids),
        generated_by=milestone_input.generated_by,
    )
