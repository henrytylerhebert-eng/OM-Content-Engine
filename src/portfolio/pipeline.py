"""Minimal local pipeline helpers for phase-one portfolio snapshots."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
import json
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, TypeVar

from src.models.evidence_item import EvidenceItem
from src.models.review_queue_item import ReviewQueueItem
from src.portfolio.capital_readiness import CapitalReadinessInput, build_capital_readiness_draft
from src.portfolio.constants import (
    CapitalReadinessStatus,
    DiscoverySourceKind,
    DomainKey,
    DraftStatus,
    EvidenceType,
    QueueStatus,
    ReportAudience,
    ReviewStatus,
    ScoreConfidence,
    TruthStage,
)
from src.portfolio.discovery_ingest import DiscoverySourceInput, ingest_discovery_sources
from src.portfolio.evidence_normalize import EvidenceExtractionTarget, normalize_evidence_targets
from src.portfolio.milestones import MilestoneInput, build_milestone_draft
from src.portfolio.report_drafts import (
    FounderSummaryInput,
    InternalSummaryInput,
    build_founder_report_draft,
    build_internal_report_draft,
)
from src.portfolio.recommendations import attach_portfolio_recommendation_draft
from src.portfolio.reviewed_truth import (
    apply_portfolio_overrides,
    build_portfolio_reviewed_truth_artifact,
    load_portfolio_override_document,
)
from src.portfolio.scoring_service import DomainScoreInput, build_domain_score_draft
from src.portfolio.snapshot import build_portfolio_snapshot_bundle
from src.portfolio.support_routing import SupportRoutingInput, build_support_routing_draft


TEnum = TypeVar("TEnum", bound=Enum)


PORTFOLIO_SNAPSHOT_ARTIFACTS = {
    "portfolio_snapshot.json": "Snapshot metadata and phase-one boundary statements for one company.",
    "discovery_sources.json": "Discovery inputs bundled into the portfolio snapshot.",
    "evidence_items.json": "Evidence items linked into the portfolio snapshot.",
    "assumptions.json": "Assumptions linked into the portfolio snapshot.",
    "domain_scores.json": "Domain score drafts bundled into the portfolio snapshot.",
    "capital_readiness_drafts.json": "Audience-limited capital-readiness drafts for founder/internal use only.",
    "support_routing_drafts.json": "Internal-only support-routing drafts linked to the portfolio snapshot.",
    "milestone_drafts.json": "Internal-only milestone drafts linked to the portfolio snapshot.",
    "review_queue_items.json": "Review queue items linked to the portfolio snapshot records.",
    "portfolio_recommendation_draft.json": "Rules-based internal recommendation draft. This remains draft guidance, not final truth.",
    "founder_report_draft.json": "Founder-facing draft summary. This remains a draft artifact, not approved output.",
    "internal_report_draft.json": "Internal operating draft summary. This remains a draft artifact, not approved output.",
    "portfolio_reviewed_truth.json": "Patch-only portfolio override log showing durable reviewed-truth decisions.",
    "snapshot_manifest.json": "Manifest describing the portfolio snapshot artifact set.",
}


def _json_default(value: object) -> object:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    raise TypeError("Object of type %s is not JSON serializable" % type(value).__name__)


def _optional_string(value: object) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _string_list(values: object) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise TypeError("Expected a list of strings but received %s." % type(values).__name__)

    cleaned: list[str] = []
    for value in values:
        text = _optional_string(value)
        if text is None:
            continue
        cleaned.append(text)
    return cleaned


def _mapping_list(payload: Mapping[str, object], key: str) -> list[Mapping[str, object]]:
    raw_value = payload.get(key, [])
    if raw_value is None:
        return []
    if not isinstance(raw_value, list):
        raise TypeError("%s must be a list of objects." % key)

    items: list[Mapping[str, object]] = []
    for index, item in enumerate(raw_value, start=1):
        if not isinstance(item, Mapping):
            raise TypeError("%s[%s] must be an object." % (key, index - 1))
        items.append(item)
    return items


def _required_string(value: object, label: str) -> str:
    text = _optional_string(value)
    if text is None:
        raise ValueError("%s is required." % label)
    return text


def _parse_datetime(value: object) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _parse_enum(enum_type: type[TEnum], value: object, label: str) -> TEnum:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(str(value))
    except ValueError as exc:
        raise ValueError("%s must be one of %s." % (label, ", ".join(member.value for member in enum_type))) from exc


def _parse_enum_list(enum_type: type[TEnum], values: object, label: str) -> list[TEnum]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise TypeError("%s must be a list." % label)
    return [_parse_enum(enum_type, value, label) for value in values]


def _build_discovery_source_input(entry: Mapping[str, object], organization_id: str) -> DiscoverySourceInput:
    raw_payload_excerpt = entry.get("raw_payload_excerpt")
    if raw_payload_excerpt is not None and not isinstance(raw_payload_excerpt, Mapping):
        raise TypeError("discovery_sources[].raw_payload_excerpt must be an object when provided.")

    return DiscoverySourceInput(
        item_id=_optional_string(entry.get("item_id")),
        source_kind=_parse_enum(
            DiscoverySourceKind,
            entry.get("source_kind", DiscoverySourceKind.MANUAL_ENTRY.value),
            "discovery_sources[].source_kind",
        ),
        title=_optional_string(entry.get("title")),
        organization_id=_optional_string(entry.get("organization_id")) or organization_id,
        description=_optional_string(entry.get("description")),
        source_system=_optional_string(entry.get("source_system")),
        source_table=_optional_string(entry.get("source_table")),
        source_record_id=_optional_string(entry.get("source_record_id")),
        source_document_id=_optional_string(entry.get("source_document_id")),
        source_url=_optional_string(entry.get("source_url")),
        source_path=_optional_string(entry.get("source_path")),
        row_hash=_optional_string(entry.get("row_hash")),
        captured_at=_parse_datetime(entry.get("captured_at")),
        ingested_at=_parse_datetime(entry.get("ingested_at")),
        provenance_note=_optional_string(entry.get("provenance_note")),
        raw_payload_excerpt=None if raw_payload_excerpt is None else dict(raw_payload_excerpt),
        submitted_by=_optional_string(entry.get("submitted_by")),
        simulation_flag=bool(entry.get("simulation_flag", False)),
        external_source_id=_optional_string(entry.get("external_source_id")),
        ingestion_run_id=_optional_string(entry.get("ingestion_run_id")),
    )


def _build_evidence_target(entry: Mapping[str, object], organization_id: str) -> tuple[str, EvidenceExtractionTarget]:
    return (
        _required_string(entry.get("discovery_source_id"), "evidence_targets[].discovery_source_id"),
        EvidenceExtractionTarget(
            organization_id=_optional_string(entry.get("organization_id")) or organization_id,
            evidence_type=_parse_enum(
                EvidenceType,
                entry.get("evidence_type", EvidenceType.OBSERVATION.value),
                "evidence_targets[].evidence_type",
            ),
            primary_domain=None
            if entry.get("primary_domain") is None
            else _parse_enum(DomainKey, entry.get("primary_domain"), "evidence_targets[].primary_domain"),
            secondary_domains=_parse_enum_list(
                DomainKey,
                entry.get("secondary_domains"),
                "evidence_targets[].secondary_domains",
            ),
            evidence_statement=_optional_string(entry.get("evidence_statement")),
            excerpt=_optional_string(entry.get("excerpt")),
            observed_at=_parse_datetime(entry.get("observed_at")),
            evidence_level=int(entry.get("evidence_level", 0)),
            confidence_note=_optional_string(entry.get("confidence_note")),
            interpretation_note=_optional_string(entry.get("interpretation_note")),
            assumption_title=_optional_string(entry.get("assumption_title")),
            assumption_statement=_optional_string(entry.get("assumption_statement")),
            enqueue_for_review=bool(entry.get("enqueue_for_review", True)),
            target_id=_optional_string(entry.get("target_id")),
        ),
    )


def _build_domain_score_input(entry: Mapping[str, object], organization_id: str) -> DomainScoreInput:
    confidence = entry.get("confidence")
    evidence_level = entry.get("evidence_level")
    raw_score = entry.get("raw_score")
    return DomainScoreInput(
        organization_id=_optional_string(entry.get("organization_id")) or organization_id,
        domain_key=_parse_enum(DomainKey, entry.get("domain_key"), "domain_scores[].domain_key"),
        raw_score=None if raw_score is None else int(raw_score),
        confidence=None if confidence is None else _parse_enum(ScoreConfidence, confidence, "domain_scores[].confidence"),
        evidence_level=None if evidence_level is None else int(evidence_level),
        rationale=_optional_string(entry.get("rationale")),
        key_gap=_optional_string(entry.get("key_gap")),
        next_action=_optional_string(entry.get("next_action")),
        linked_assumption_ids=_string_list(entry.get("linked_assumption_ids")),
        generated_by=_optional_string(entry.get("generated_by")),
        score_id=_optional_string(entry.get("score_id")),
    )


def _build_capital_readiness_input(
    entry: Mapping[str, object],
    organization_id: str,
    report_period: str,
) -> CapitalReadinessInput:
    return CapitalReadinessInput(
        organization_id=_optional_string(entry.get("organization_id")) or organization_id,
        report_period=_optional_string(entry.get("report_period")) or report_period,
        audience=_parse_enum(
            ReportAudience,
            entry.get("audience", ReportAudience.INTERNAL.value),
            "capital_readiness_drafts[].audience",
        ),
        draft_status=_parse_enum(
            DraftStatus,
            entry.get("draft_status", DraftStatus.DRAFT.value),
            "capital_readiness_drafts[].draft_status",
        ),
        readiness_status=_parse_enum(
            CapitalReadinessStatus,
            entry.get("readiness_status", CapitalReadinessStatus.NOT_YET_ASSESSED.value),
            "capital_readiness_drafts[].readiness_status",
        ),
        primary_capital_path=_optional_string(entry.get("primary_capital_path")),
        secondary_capital_paths=_string_list(entry.get("secondary_capital_paths")),
        readiness_rationale=_optional_string(entry.get("readiness_rationale")),
        blocking_gaps=_string_list(entry.get("blocking_gaps")),
        required_evidence=_string_list(entry.get("required_evidence")),
        support_routing_recommendation=_optional_string(entry.get("support_routing_recommendation")),
        next_milestone=_optional_string(entry.get("next_milestone")),
        linked_domain_score_ids=_string_list(entry.get("linked_domain_score_ids")),
        linked_discovery_source_ids=_string_list(entry.get("linked_discovery_source_ids")),
        linked_evidence_ids=_string_list(entry.get("linked_evidence_ids")),
        linked_review_queue_ids=_string_list(entry.get("linked_review_queue_ids")),
        linked_assumption_ids=_string_list(entry.get("linked_assumption_ids")),
        generated_by=_optional_string(entry.get("generated_by")),
        draft_id=_optional_string(entry.get("draft_id")),
    )


def _build_founder_summary_input(
    payload: Mapping[str, object],
    organization_id: str,
    report_period: str,
) -> FounderSummaryInput:
    return FounderSummaryInput(
        organization_id=organization_id,
        report_period=report_period,
        strengths=_string_list(payload.get("strengths")),
        top_gaps=_string_list(payload.get("top_gaps")),
        evidence_improving=_string_list(payload.get("evidence_improving")),
        milestones=_string_list(payload.get("milestones")),
        recommended_next_actions=_string_list(payload.get("recommended_next_actions")),
        capital_readiness_summary=_optional_string(payload.get("capital_readiness_summary")),
        linked_domain_score_ids=_string_list(payload.get("linked_domain_score_ids")),
        linked_capital_readiness_draft_ids=_string_list(payload.get("linked_capital_readiness_draft_ids")),
        linked_discovery_source_ids=_string_list(payload.get("linked_discovery_source_ids")),
        linked_evidence_ids=_string_list(payload.get("linked_evidence_ids")),
        linked_review_queue_ids=_string_list(payload.get("linked_review_queue_ids")),
        linked_assumption_ids=_string_list(payload.get("linked_assumption_ids")),
        draft_status=_parse_enum(
            DraftStatus,
            payload.get("draft_status", DraftStatus.DRAFT.value),
            "founder_report.draft_status",
        ),
        generated_by=_optional_string(payload.get("generated_by")),
    )


def _build_support_routing_input(
    entry: Mapping[str, object],
    organization_id: str,
    report_period: str,
) -> SupportRoutingInput:
    priority_domain = entry.get("priority_domain")
    return SupportRoutingInput(
        organization_id=_optional_string(entry.get("organization_id")) or organization_id,
        report_period=_optional_string(entry.get("report_period")) or report_period,
        route_recommendation=_required_string(
            entry.get("route_recommendation"),
            "support_routing_drafts[].route_recommendation",
        ),
        audience=_parse_enum(
            ReportAudience,
            entry.get("audience", ReportAudience.INTERNAL.value),
            "support_routing_drafts[].audience",
        ),
        draft_status=_parse_enum(
            DraftStatus,
            entry.get("draft_status", DraftStatus.DRAFT.value),
            "support_routing_drafts[].draft_status",
        ),
        route_category=_optional_string(entry.get("route_category")),
        route_rationale=_optional_string(entry.get("route_rationale")),
        priority_domain=None
        if priority_domain is None
        else _parse_enum(DomainKey, priority_domain, "support_routing_drafts[].priority_domain"),
        linked_domain_score_ids=_string_list(entry.get("linked_domain_score_ids")),
        linked_capital_readiness_draft_ids=_string_list(entry.get("linked_capital_readiness_draft_ids")),
        linked_discovery_source_ids=_string_list(entry.get("linked_discovery_source_ids")),
        linked_evidence_ids=_string_list(entry.get("linked_evidence_ids")),
        linked_review_queue_ids=_string_list(entry.get("linked_review_queue_ids")),
        linked_assumption_ids=_string_list(entry.get("linked_assumption_ids")),
        generated_by=_optional_string(entry.get("generated_by")),
        draft_id=_optional_string(entry.get("draft_id")),
    )


def _build_milestone_input(
    entry: Mapping[str, object],
    organization_id: str,
    report_period: str,
) -> MilestoneInput:
    priority_domain = entry.get("priority_domain")
    return MilestoneInput(
        organization_id=_optional_string(entry.get("organization_id")) or organization_id,
        report_period=_optional_string(entry.get("report_period")) or report_period,
        milestone_statement=_required_string(
            entry.get("milestone_statement"),
            "milestone_drafts[].milestone_statement",
        ),
        audience=_parse_enum(
            ReportAudience,
            entry.get("audience", ReportAudience.INTERNAL.value),
            "milestone_drafts[].audience",
        ),
        draft_status=_parse_enum(
            DraftStatus,
            entry.get("draft_status", DraftStatus.DRAFT.value),
            "milestone_drafts[].draft_status",
        ),
        milestone_category=_optional_string(entry.get("milestone_category")),
        milestone_rationale=_optional_string(entry.get("milestone_rationale")),
        target_window=_optional_string(entry.get("target_window")),
        priority_domain=None
        if priority_domain is None
        else _parse_enum(DomainKey, priority_domain, "milestone_drafts[].priority_domain"),
        linked_domain_score_ids=_string_list(entry.get("linked_domain_score_ids")),
        linked_capital_readiness_draft_ids=_string_list(entry.get("linked_capital_readiness_draft_ids")),
        linked_discovery_source_ids=_string_list(entry.get("linked_discovery_source_ids")),
        linked_evidence_ids=_string_list(entry.get("linked_evidence_ids")),
        linked_review_queue_ids=_string_list(entry.get("linked_review_queue_ids")),
        linked_assumption_ids=_string_list(entry.get("linked_assumption_ids")),
        generated_by=_optional_string(entry.get("generated_by")),
        draft_id=_optional_string(entry.get("draft_id")),
    )


def _build_internal_summary_input(
    payload: Mapping[str, object],
    organization_id: str,
    report_period: str,
) -> InternalSummaryInput:
    return InternalSummaryInput(
        organization_id=organization_id,
        report_period=report_period,
        current_strengths=_string_list(payload.get("current_strengths")),
        stuck_reasons=_string_list(payload.get("stuck_reasons")),
        watchlist_status=_optional_string(payload.get("watchlist_status")),
        recommended_support_route=_optional_string(payload.get("recommended_support_route")),
        milestone_status=_optional_string(payload.get("milestone_status")),
        capital_paths_considered=_string_list(payload.get("capital_paths_considered")),
        priority_domains=_parse_enum_list(DomainKey, payload.get("priority_domains"), "internal_report.priority_domains"),
        linked_domain_score_ids=_string_list(payload.get("linked_domain_score_ids")),
        linked_capital_readiness_draft_ids=_string_list(payload.get("linked_capital_readiness_draft_ids")),
        linked_discovery_source_ids=_string_list(payload.get("linked_discovery_source_ids")),
        linked_evidence_ids=_string_list(payload.get("linked_evidence_ids")),
        linked_review_queue_ids=_string_list(payload.get("linked_review_queue_ids")),
        linked_assumption_ids=_string_list(payload.get("linked_assumption_ids")),
        internal_notes=_string_list(payload.get("internal_notes")),
        draft_status=_parse_enum(
            DraftStatus,
            payload.get("draft_status", DraftStatus.DRAFT.value),
            "internal_report.draft_status",
        ),
        generated_by=_optional_string(payload.get("generated_by")),
    )


def _apply_explicit_review_state(
    evidence_items: Sequence[EvidenceItem],
    review_queue_items: Sequence[ReviewQueueItem],
    reviewed_evidence_ids: Sequence[str],
    *,
    reviewed_by: Optional[str],
    review_note: Optional[str],
) -> None:
    """Apply explicit local review decisions without inferring review automatically."""

    if not reviewed_evidence_ids:
        return

    evidence_by_id = {item.id: item for item in evidence_items}
    missing_ids = sorted(set(reviewed_evidence_ids) - set(evidence_by_id))
    if missing_ids:
        raise ValueError(
            "reviewed_evidence_ids references evidence ids that were not produced by the local input: %s."
            % ", ".join(missing_ids)
        )

    reviewed_at = datetime.utcnow()
    for evidence_id in reviewed_evidence_ids:
        evidence_item = evidence_by_id[evidence_id]
        evidence_item.truth_stage = TruthStage.REVIEWED_EVIDENCE
        evidence_item.review_status = ReviewStatus.REVIEWED
        evidence_item.reviewed_by = reviewed_by
        evidence_item.reviewed_at = reviewed_at
        evidence_item.review_notes = review_note or "Explicit local review input promoted this evidence to reviewed_evidence."

    for queue_item in review_queue_items:
        if queue_item.queue_reason_code != "review_stage_promotion":
            continue
        if queue_item.linked_evidence_item_id not in reviewed_evidence_ids:
            continue
        queue_item.queue_status = QueueStatus.RESOLVED
        queue_item.resolved_at = reviewed_at
        queue_item.resolution_note = (
            review_note or "Explicit local review input completed the pending evidence promotion step."
        )


def load_portfolio_input(input_path: Path) -> dict[str, object]:
    """Load a local portfolio input file from disk."""

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Portfolio input file must contain a top-level object.")
    return payload


def build_portfolio_snapshot_bundle_from_payload(payload: Mapping[str, object]) -> dict[str, object]:
    """Build a single-company portfolio snapshot bundle from explicit local input."""

    organization_id = _required_string(payload.get("organization_id"), "organization_id")
    company_name = _optional_string(payload.get("company_name"))
    report_period = _required_string(payload.get("report_period"), "report_period")
    assembled_by = _optional_string(payload.get("assembled_by"))

    discovery_inputs = [
        _build_discovery_source_input(entry, organization_id)
        for entry in _mapping_list(payload, "discovery_sources")
    ]
    ingestion_result = ingest_discovery_sources(inputs=discovery_inputs)
    discovery_sources = ingestion_result.discovery_sources
    review_queue_items = list(ingestion_result.review_queue_items)
    discovery_source_by_id = {source.id: source for source in discovery_sources}

    evidence_items: list[EvidenceItem] = []
    assumptions = []
    for entry in _mapping_list(payload, "evidence_targets"):
        discovery_source_id, target = _build_evidence_target(entry, organization_id)
        discovery_source = discovery_source_by_id.get(discovery_source_id)
        if discovery_source is None:
            raise ValueError(
                "evidence_targets references discovery source %s, but no matching discovery source was loaded."
                % discovery_source_id
            )

        result = normalize_evidence_targets(discovery_source, [target])
        evidence_items.extend(result.evidence_items)
        assumptions.extend(result.assumptions)
        review_queue_items.extend(result.review_queue_items)

    _apply_explicit_review_state(
        evidence_items,
        review_queue_items,
        _string_list(payload.get("reviewed_evidence_ids")),
        reviewed_by=_optional_string(payload.get("reviewed_by")),
        review_note=_optional_string(payload.get("review_note")),
    )

    domain_scores = [
        build_domain_score_draft(
            _build_domain_score_input(entry, organization_id),
            evidence_items=evidence_items,
            review_queue_items=review_queue_items,
        )
        for entry in _mapping_list(payload, "domain_scores")
    ]

    capital_readiness_drafts = [
        build_capital_readiness_draft(
            _build_capital_readiness_input(entry, organization_id, report_period)
        )
        for entry in _mapping_list(payload, "capital_readiness_drafts")
    ]
    support_routing_drafts = [
        build_support_routing_draft(
            _build_support_routing_input(entry, organization_id, report_period)
        )
        for entry in _mapping_list(payload, "support_routing_drafts")
    ]
    milestone_drafts = [
        build_milestone_draft(
            _build_milestone_input(entry, organization_id, report_period)
        )
        for entry in _mapping_list(payload, "milestone_drafts")
    ]

    founder_report_payload = payload.get("founder_report")
    founder_report_draft = None
    if founder_report_payload is not None:
        if not isinstance(founder_report_payload, Mapping):
            raise TypeError("founder_report must be an object.")
        founder_report_draft = build_founder_report_draft(
            _build_founder_summary_input(founder_report_payload, organization_id, report_period)
        )

    internal_report_payload = payload.get("internal_report")
    internal_report_draft = None
    if internal_report_payload is not None:
        if not isinstance(internal_report_payload, Mapping):
            raise TypeError("internal_report must be an object.")
        internal_report_draft = build_internal_report_draft(
            _build_internal_summary_input(internal_report_payload, organization_id, report_period)
        )

    bundle = build_portfolio_snapshot_bundle(
        organization_id=organization_id,
        report_period=report_period,
        discovery_sources=discovery_sources,
        evidence_items=evidence_items,
        assumptions=assumptions,
        domain_scores=domain_scores,
        capital_readiness_drafts=capital_readiness_drafts,
        support_routing_drafts=support_routing_drafts,
        milestone_drafts=milestone_drafts,
        review_queue_items=review_queue_items,
        founder_report_draft=founder_report_draft,
        internal_report_draft=internal_report_draft,
        assembled_by=assembled_by,
    )
    if company_name is not None:
        bundle["company_name"] = company_name
    return attach_portfolio_recommendation_draft(
        bundle,
        generated_by=assembled_by or "portfolio_recommendation_rules",
    )


def build_portfolio_snapshot_bundle_from_file(input_path: Path) -> dict[str, object]:
    """Load a local input file and build a one-company portfolio snapshot bundle."""

    return build_portfolio_snapshot_bundle_from_payload(load_portfolio_input(input_path))


def build_portfolio_snapshot_bundle_with_overrides(
    input_path: Path,
    *,
    overrides_path: Optional[Path],
) -> dict[str, object]:
    """Build a one-company portfolio snapshot bundle and apply optional reviewed-truth overrides."""

    bundle = build_portfolio_snapshot_bundle_from_file(input_path)
    override_document = load_portfolio_override_document(overrides_path)
    if not override_document.rules:
        return bundle

    reviewed_bundle, applications = apply_portfolio_overrides(bundle, override_document)
    reviewed_bundle = attach_portfolio_recommendation_draft(
        reviewed_bundle,
        generated_by="portfolio_recommendation_rules",
    )
    reviewed_bundle["portfolio_reviewed_truth"] = build_portfolio_reviewed_truth_artifact(
        override_document=override_document,
        applications=applications,
        snapshot_summary=reviewed_bundle.get("portfolio_snapshot", {}),
    )
    return reviewed_bundle


def write_portfolio_snapshot_outputs(bundle: dict[str, object], output_dir: Path) -> list[Path]:
    """Write a one-company portfolio snapshot bundle as inspectable JSON artifacts."""

    output_dir.mkdir(parents=True, exist_ok=True)

    payloads = {
        "portfolio_snapshot.json": bundle.get("portfolio_snapshot", {}),
        "discovery_sources.json": bundle.get("discovery_sources", []),
        "evidence_items.json": bundle.get("evidence_items", []),
        "assumptions.json": bundle.get("assumptions", []),
        "domain_scores.json": bundle.get("domain_scores", []),
        "capital_readiness_drafts.json": bundle.get("capital_readiness_drafts", []),
        "support_routing_drafts.json": bundle.get("support_routing_drafts", []),
        "milestone_drafts.json": bundle.get("milestone_drafts", []),
        "review_queue_items.json": bundle.get("review_queue_items", []),
        "portfolio_recommendation_draft.json": bundle.get("portfolio_recommendation_draft"),
        "founder_report_draft.json": bundle.get("founder_report_draft"),
        "internal_report_draft.json": bundle.get("internal_report_draft"),
    }
    if "portfolio_reviewed_truth" in bundle:
        payloads["portfolio_reviewed_truth.json"] = bundle.get("portfolio_reviewed_truth", {})

    written_paths: list[Path] = []
    for filename, payload in payloads.items():
        path = output_dir / filename
        path.write_text(json.dumps(payload, indent=2, default=_json_default) + "\n", encoding="utf-8")
        written_paths.append(path)

    snapshot = dict(bundle.get("portfolio_snapshot", {}))
    manifest = {
        "artifact_type": "portfolio_snapshot",
        "organization_id": snapshot.get("organization_id"),
        "report_period": snapshot.get("report_period"),
        "artifacts": [
            {
                "filename": path.name,
                "description": PORTFOLIO_SNAPSHOT_ARTIFACTS.get(path.name),
            }
            for path in written_paths
        ],
        "summary": snapshot,
    }

    manifest_path = output_dir / "snapshot_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, default=_json_default) + "\n", encoding="utf-8")
    written_paths.append(manifest_path)
    return written_paths
