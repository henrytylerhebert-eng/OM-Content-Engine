"""Capital-readiness draft assembly for the portfolio workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence
import re

from src.models.capital_readiness_draft import CapitalReadinessDraft
from src.portfolio.constants import CapitalReadinessStatus, DraftStatus, ReportAudience


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
class CapitalReadinessInput:
    """Explicit inputs for building an audience-specific capital-readiness draft."""

    organization_id: str
    report_period: str
    audience: ReportAudience = ReportAudience.INTERNAL
    readiness_status: CapitalReadinessStatus = CapitalReadinessStatus.NOT_YET_ASSESSED
    primary_capital_path: Optional[str] = None
    secondary_capital_paths: list[str] = field(default_factory=list)
    readiness_rationale: Optional[str] = None
    blocking_gaps: list[str] = field(default_factory=list)
    required_evidence: list[str] = field(default_factory=list)
    support_routing_recommendation: Optional[str] = None
    next_milestone: Optional[str] = None
    linked_domain_score_ids: list[str] = field(default_factory=list)
    linked_discovery_source_ids: list[str] = field(default_factory=list)
    linked_evidence_ids: list[str] = field(default_factory=list)
    linked_review_queue_ids: list[str] = field(default_factory=list)
    linked_assumption_ids: list[str] = field(default_factory=list)
    draft_status: DraftStatus = DraftStatus.DRAFT
    generated_by: Optional[str] = None
    draft_id: Optional[str] = None


def _validate_capital_readiness_status(readiness_input: CapitalReadinessInput) -> None:
    """Prevent capital-readiness drafts from overstating their support."""

    if readiness_input.draft_status != DraftStatus.REVIEW_READY:
        return

    if readiness_input.readiness_status == CapitalReadinessStatus.NOT_YET_ASSESSED:
        raise ValueError(
            "CapitalReadinessDraft cannot be marked review_ready while readiness_status is not_yet_assessed."
        )

    if not _unique_ids(readiness_input.linked_domain_score_ids):
        raise ValueError("CapitalReadinessDraft cannot be marked review_ready without linked domain score draft ids.")

    if not _unique_ids(readiness_input.linked_discovery_source_ids) and not _unique_ids(readiness_input.linked_evidence_ids):
        raise ValueError(
            "CapitalReadinessDraft cannot be marked review_ready without linked discovery source ids or linked evidence ids."
        )

    if not str(readiness_input.readiness_rationale or "").strip():
        raise ValueError("CapitalReadinessDraft cannot be marked review_ready without a readiness rationale.")


def build_capital_readiness_draft(readiness_input: CapitalReadinessInput) -> CapitalReadinessDraft:
    """Assemble a capital-readiness draft from explicit linked inputs."""

    _validate_capital_readiness_status(readiness_input)

    return CapitalReadinessDraft(
        id=readiness_input.draft_id
        or "capital_readiness:%s:%s:%s" % (
            _slug(readiness_input.organization_id),
            readiness_input.audience.value,
            _slug(readiness_input.report_period),
        ),
        organization_id=readiness_input.organization_id,
        report_period=readiness_input.report_period,
        audience=readiness_input.audience,
        draft_status=readiness_input.draft_status,
        readiness_status=readiness_input.readiness_status,
        primary_capital_path=readiness_input.primary_capital_path,
        secondary_capital_paths=_unique_strings(readiness_input.secondary_capital_paths),
        readiness_rationale=readiness_input.readiness_rationale,
        blocking_gaps=_unique_strings(readiness_input.blocking_gaps),
        required_evidence=_unique_strings(readiness_input.required_evidence),
        support_routing_recommendation=readiness_input.support_routing_recommendation,
        next_milestone=readiness_input.next_milestone,
        linked_domain_score_ids=_unique_ids(readiness_input.linked_domain_score_ids),
        linked_discovery_source_ids=_unique_ids(readiness_input.linked_discovery_source_ids),
        linked_evidence_ids=_unique_ids(readiness_input.linked_evidence_ids),
        linked_review_queue_ids=_unique_ids(readiness_input.linked_review_queue_ids),
        linked_assumption_ids=_unique_ids(readiness_input.linked_assumption_ids),
        generated_by=readiness_input.generated_by,
    )
