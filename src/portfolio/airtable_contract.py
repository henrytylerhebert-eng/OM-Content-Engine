"""Airtable-aligned operational export structures for phase-one portfolio records."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, date
from enum import Enum
import json
from pathlib import Path
import re
from typing import Mapping, Optional


AIRTABLE_OPERATIONAL_TABLES = (
    "Companies",
    "Evidence Items",
    "Assumptions",
    "Domain Scores",
    "Capital Readiness",
    "Support Routing",
    "Action Items",
    "Milestones",
)

AIRTABLE_OPERATIONAL_FILENAMES = {
    "Companies": "airtable_companies.json",
    "Evidence Items": "airtable_evidence_items.json",
    "Assumptions": "airtable_assumptions.json",
    "Domain Scores": "airtable_domain_scores.json",
    "Capital Readiness": "airtable_capital_readiness.json",
    "Support Routing": "airtable_support_routing.json",
    "Action Items": "airtable_action_items.json",
    "Milestones": "airtable_milestones.json",
}


def _optional_text(value: object) -> Optional[str]:
    text = str(value or "").strip()
    return text or None


def _json_default(value: object) -> object:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    raise TypeError("Object of type %s is not JSON serializable" % type(value).__name__)


def _string_list(values: object) -> list[str]:
    if values is None:
        return []
    if isinstance(values, list):
        cleaned: list[str] = []
        for value in values:
            text = _optional_text(value)
            if text is None:
                continue
            cleaned.append(text)
        return cleaned
    return [_optional_text(values)] if _optional_text(values) is not None else []


def _slug(value: object) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower())
    return text.strip("_") or "record"


def _title_case_slug(value: str) -> str:
    parts = [part for part in re.split(r"[_:\-]+", value) if part]
    return " ".join(part.capitalize() for part in parts) or value


def _model_list(bundle: Mapping[str, object], key: str) -> list[Mapping[str, object]]:
    value = bundle.get(key, [])
    if not isinstance(value, list):
        return []
    rows: list[Mapping[str, object]] = []
    for item in value:
        if isinstance(item, Mapping):
            rows.append(item)
    return rows


def _single_model(bundle: Mapping[str, object], key: str) -> Optional[Mapping[str, object]]:
    value = bundle.get(key)
    return value if isinstance(value, Mapping) else None


def _infer_company_name(bundle: Mapping[str, object]) -> tuple[Optional[str], bool]:
    explicit_name = _optional_text(bundle.get("company_name"))
    if explicit_name is not None:
        return explicit_name, False

    for discovery_source in _model_list(bundle, "discovery_sources"):
        raw_excerpt = discovery_source.get("raw_payload_excerpt")
        if not isinstance(raw_excerpt, Mapping):
            continue
        for field_name in ("Company Name", "Organization Name", "company_name", "organization_name", "Name"):
            name = _optional_text(raw_excerpt.get(field_name))
            if name is not None:
                return name, False

    snapshot = _single_model(bundle, "portfolio_snapshot") or {}
    organization_id = _optional_text(snapshot.get("organization_id"))
    if organization_id is None:
        return None, False

    inferred_name = _title_case_slug(organization_id.replace("org:", ""))
    return inferred_name, True


@dataclass(frozen=True)
class CompanyOperationalRecord:
    id: str
    organization_id: str
    report_period: str
    company_name: Optional[str]
    company_name_inferred: bool
    portfolio_snapshot_id: str
    source_truth_statement: str
    draft_boundary_statement: str
    reviewed_evidence_count: int
    pending_evidence_count: int
    domain_score_count: int
    review_ready_domain_score_count: int
    capital_readiness_draft_count: int
    founder_report_draft_id: Optional[str]
    founder_report_draft_status: Optional[str]
    founder_report_review_status: Optional[str]
    internal_report_draft_id: Optional[str]
    internal_report_draft_status: Optional[str]
    internal_report_review_status: Optional[str]
    watchlist_status: Optional[str]
    recommended_support_route: Optional[str]
    milestone_status: Optional[str]


@dataclass(frozen=True)
class EvidenceItemOperationalRecord:
    id: str
    organization_id: str
    discovery_source_id: str
    evidence_type: Optional[str]
    primary_domain: str
    secondary_domains: list[str]
    evidence_statement: str
    evidence_level: int
    observed_at: Optional[str]
    excerpt: Optional[str]
    confidence_note: Optional[str]
    interpretation_note: Optional[str]
    truth_stage: Optional[str]
    review_status: Optional[str]
    review_notes: Optional[str]
    reviewed_by: Optional[str]
    reviewed_at: Optional[str]
    linked_assumption_ids: list[str]
    reviewed_truth_applied: bool
    reviewed_override_ids: list[str]
    source_system: Optional[str]
    source_table: Optional[str]
    source_record_id: Optional[str]
    source_document_id: Optional[str]
    source_url: Optional[str]
    source_path: Optional[str]
    row_hash: Optional[str]


@dataclass(frozen=True)
class AssumptionOperationalRecord:
    id: str
    organization_id: str
    domain_key: str
    title: str
    statement: str
    assumption_type: Optional[str]
    status: Optional[str]
    owner: Optional[str]
    validation_plan: Optional[str]
    next_check_date: Optional[str]
    truth_stage: Optional[str]
    review_status: Optional[str]
    review_notes: Optional[str]
    linked_evidence_ids: list[str]
    contradicting_evidence_ids: list[str]
    source_system: Optional[str]
    source_table: Optional[str]
    source_record_id: Optional[str]
    source_url: Optional[str]
    source_path: Optional[str]


@dataclass(frozen=True)
class DomainScoreOperationalRecord:
    id: str
    organization_id: str
    domain_key: str
    raw_score: Optional[int]
    confidence: Optional[str]
    evidence_level: int
    rationale: Optional[str]
    key_gap: Optional[str]
    next_action: Optional[str]
    score_status: Optional[str]
    truth_stage: Optional[str]
    review_status: Optional[str]
    review_notes: Optional[str]
    reviewed_by: Optional[str]
    reviewed_at: Optional[str]
    score_basis_evidence_ids: list[str]
    pending_evidence_ids: list[str]
    linked_review_queue_ids: list[str]
    linked_assumption_ids: list[str]
    generated_by: Optional[str]
    reviewed_truth_applied: bool
    reviewed_override_ids: list[str]


@dataclass(frozen=True)
class CapitalReadinessOperationalRecord:
    id: str
    organization_id: str
    report_period: str
    audience: Optional[str]
    draft_status: Optional[str]
    review_status: Optional[str]
    truth_stage: Optional[str]
    readiness_status: Optional[str]
    primary_capital_path: Optional[str]
    secondary_capital_paths: list[str]
    readiness_rationale: Optional[str]
    blocking_gaps: list[str]
    required_evidence: list[str]
    support_routing_recommendation: Optional[str]
    next_milestone: Optional[str]
    linked_domain_score_ids: list[str]
    linked_discovery_source_ids: list[str]
    linked_evidence_ids: list[str]
    linked_review_queue_ids: list[str]
    linked_assumption_ids: list[str]
    generated_by: Optional[str]
    reviewed_truth_applied: bool
    reviewed_override_ids: list[str]


@dataclass(frozen=True)
class SupportRoutingOperationalRecord:
    id: str
    organization_id: str
    report_period: str
    audience: str
    route_recommendation: str
    route_category: Optional[str]
    route_rationale: Optional[str]
    priority_domain: Optional[str]
    route_source_type: str
    route_source_id: str
    source_draft_status: Optional[str]
    source_truth_stage: Optional[str]
    source_review_status: Optional[str]
    linked_domain_score_ids: list[str]
    linked_capital_readiness_draft_ids: list[str]
    linked_evidence_ids: list[str]
    linked_assumption_ids: list[str]
    linked_review_queue_ids: list[str]
    operational_status: str = "draft_projection"


@dataclass(frozen=True)
class ActionItemOperationalRecord:
    id: str
    organization_id: str
    report_period: str
    audience: str
    action_text: str
    action_type: str
    source_record_type: str
    source_record_id: str
    source_domain_key: Optional[str]
    source_draft_status: Optional[str]
    source_truth_stage: Optional[str]
    source_review_status: Optional[str]
    linked_domain_score_ids: list[str]
    linked_evidence_ids: list[str]
    linked_assumption_ids: list[str]
    operational_status: str = "draft_projection"


@dataclass(frozen=True)
class MilestoneOperationalRecord:
    id: str
    organization_id: str
    report_period: str
    audience: str
    milestone_text: str
    milestone_type: str
    milestone_rationale: Optional[str]
    target_window: Optional[str]
    priority_domain: Optional[str]
    source_record_type: str
    source_record_id: str
    source_draft_status: Optional[str]
    source_truth_stage: Optional[str]
    source_review_status: Optional[str]
    linked_domain_score_ids: list[str]
    linked_capital_readiness_draft_ids: list[str]
    linked_evidence_ids: list[str]
    linked_review_queue_ids: list[str]
    linked_assumption_ids: list[str]
    operational_status: str = "draft_projection"


@dataclass(frozen=True)
class PortfolioAirtableOperationalExport:
    organization_id: str
    report_period: str
    portfolio_snapshot_id: str
    companies: list[CompanyOperationalRecord] = field(default_factory=list)
    evidence_items: list[EvidenceItemOperationalRecord] = field(default_factory=list)
    assumptions: list[AssumptionOperationalRecord] = field(default_factory=list)
    domain_scores: list[DomainScoreOperationalRecord] = field(default_factory=list)
    capital_readiness: list[CapitalReadinessOperationalRecord] = field(default_factory=list)
    support_routing: list[SupportRoutingOperationalRecord] = field(default_factory=list)
    action_items: list[ActionItemOperationalRecord] = field(default_factory=list)
    milestones: list[MilestoneOperationalRecord] = field(default_factory=list)


@dataclass(frozen=True)
class AirtableOperationalTableSummary:
    table_name: str
    row_count: int
    record_ids: list[str]


@dataclass(frozen=True)
class PortfolioAirtableExampleSummary:
    organization_id: str
    report_period: str
    portfolio_snapshot_id: str
    company_name: Optional[str]
    source_truth_statement: str
    draft_boundary_statement: str
    founder_report_draft_status: Optional[str]
    internal_report_draft_status: Optional[str]
    tables: list[AirtableOperationalTableSummary] = field(default_factory=list)


def _company_record(bundle: Mapping[str, object]) -> CompanyOperationalRecord:
    snapshot = _single_model(bundle, "portfolio_snapshot") or {}
    internal_report = _single_model(bundle, "internal_report_draft") or {}
    founder_report = _single_model(bundle, "founder_report_draft") or {}
    company_name, company_name_inferred = _infer_company_name(bundle)
    return CompanyOperationalRecord(
        id="company:%s:%s" % (
            _slug(snapshot.get("organization_id")),
            _slug(snapshot.get("report_period")),
        ),
        organization_id=str(snapshot.get("organization_id")),
        report_period=str(snapshot.get("report_period")),
        company_name=company_name,
        company_name_inferred=company_name_inferred,
        portfolio_snapshot_id=str(snapshot.get("id")),
        source_truth_statement=str(snapshot.get("source_truth_statement")),
        draft_boundary_statement=str(snapshot.get("draft_boundary_statement")),
        reviewed_evidence_count=int(snapshot.get("reviewed_evidence_count", 0)),
        pending_evidence_count=int(snapshot.get("pending_evidence_count", 0)),
        domain_score_count=int(snapshot.get("domain_score_count", 0)),
        review_ready_domain_score_count=int(snapshot.get("review_ready_domain_score_count", 0)),
        capital_readiness_draft_count=int(snapshot.get("capital_readiness_draft_count", 0)),
        founder_report_draft_id=_optional_text(founder_report.get("id")),
        founder_report_draft_status=_optional_text(founder_report.get("draft_status")),
        founder_report_review_status=_optional_text(founder_report.get("review_status")),
        internal_report_draft_id=_optional_text(internal_report.get("id")),
        internal_report_draft_status=_optional_text(internal_report.get("draft_status")),
        internal_report_review_status=_optional_text(internal_report.get("review_status")),
        watchlist_status=_optional_text(internal_report.get("watchlist_status")),
        recommended_support_route=_optional_text(internal_report.get("recommended_support_route")),
        milestone_status=_optional_text(internal_report.get("milestone_status")),
    )


def _evidence_item_records(bundle: Mapping[str, object]) -> list[EvidenceItemOperationalRecord]:
    records: list[EvidenceItemOperationalRecord] = []
    for item in _model_list(bundle, "evidence_items"):
        records.append(
            EvidenceItemOperationalRecord(
                id=str(item.get("id")),
                organization_id=str(item.get("organization_id")),
                discovery_source_id=str(item.get("discovery_source_id")),
                evidence_type=_optional_text(item.get("evidence_type")),
                primary_domain=str(item.get("primary_domain")),
                secondary_domains=_string_list(item.get("secondary_domains")),
                evidence_statement=str(item.get("evidence_statement")),
                evidence_level=int(item.get("evidence_level", 0)),
                observed_at=_optional_text(item.get("observed_at")),
                excerpt=_optional_text(item.get("excerpt")),
                confidence_note=_optional_text(item.get("confidence_note")),
                interpretation_note=_optional_text(item.get("interpretation_note")),
                truth_stage=_optional_text(item.get("truth_stage")),
                review_status=_optional_text(item.get("review_status")),
                review_notes=_optional_text(item.get("review_notes")),
                reviewed_by=_optional_text(item.get("reviewed_by")),
                reviewed_at=_optional_text(item.get("reviewed_at")),
                linked_assumption_ids=_string_list(item.get("linked_assumption_ids")),
                reviewed_truth_applied=bool(item.get("reviewed_truth_applied", False)),
                reviewed_override_ids=_string_list(item.get("reviewed_override_ids")),
                source_system=_optional_text(item.get("source_system")),
                source_table=_optional_text(item.get("source_table")),
                source_record_id=_optional_text(item.get("source_record_id")),
                source_document_id=_optional_text(item.get("source_document_id")),
                source_url=_optional_text(item.get("source_url")),
                source_path=_optional_text(item.get("source_path")),
                row_hash=_optional_text(item.get("row_hash")),
            )
        )
    return records


def _assumption_records(bundle: Mapping[str, object]) -> list[AssumptionOperationalRecord]:
    records: list[AssumptionOperationalRecord] = []
    for item in _model_list(bundle, "assumptions"):
        records.append(
            AssumptionOperationalRecord(
                id=str(item.get("id")),
                organization_id=str(item.get("organization_id")),
                domain_key=str(item.get("domain_key")),
                title=str(item.get("title")),
                statement=str(item.get("statement")),
                assumption_type=_optional_text(item.get("assumption_type")),
                status=_optional_text(item.get("status")),
                owner=_optional_text(item.get("owner")),
                validation_plan=_optional_text(item.get("validation_plan")),
                next_check_date=_optional_text(item.get("next_check_date")),
                truth_stage=_optional_text(item.get("truth_stage")),
                review_status=_optional_text(item.get("review_status")),
                review_notes=_optional_text(item.get("review_notes")),
                linked_evidence_ids=_string_list(item.get("linked_evidence_ids")),
                contradicting_evidence_ids=_string_list(item.get("contradicting_evidence_ids")),
                source_system=_optional_text(item.get("source_system")),
                source_table=_optional_text(item.get("source_table")),
                source_record_id=_optional_text(item.get("source_record_id")),
                source_url=_optional_text(item.get("source_url")),
                source_path=_optional_text(item.get("source_path")),
            )
        )
    return records


def _domain_score_records(bundle: Mapping[str, object]) -> list[DomainScoreOperationalRecord]:
    records: list[DomainScoreOperationalRecord] = []
    for item in _model_list(bundle, "domain_scores"):
        raw_score = item.get("raw_score")
        records.append(
            DomainScoreOperationalRecord(
                id=str(item.get("id")),
                organization_id=str(item.get("organization_id")),
                domain_key=str(item.get("domain_key")),
                raw_score=None if raw_score is None else int(raw_score),
                confidence=_optional_text(item.get("confidence")),
                evidence_level=int(item.get("evidence_level", 0)),
                rationale=_optional_text(item.get("rationale")),
                key_gap=_optional_text(item.get("key_gap")),
                next_action=_optional_text(item.get("next_action")),
                score_status=_optional_text(item.get("score_status")),
                truth_stage=_optional_text(item.get("truth_stage")),
                review_status=_optional_text(item.get("review_status")),
                review_notes=_optional_text(item.get("review_notes")),
                reviewed_by=_optional_text(item.get("reviewed_by")),
                reviewed_at=_optional_text(item.get("reviewed_at")),
                score_basis_evidence_ids=_string_list(item.get("score_basis_evidence_ids")),
                pending_evidence_ids=_string_list(item.get("pending_evidence_ids")),
                linked_review_queue_ids=_string_list(item.get("linked_review_queue_ids")),
                linked_assumption_ids=_string_list(item.get("linked_assumption_ids")),
                generated_by=_optional_text(item.get("generated_by")),
                reviewed_truth_applied=bool(item.get("reviewed_truth_applied", False)),
                reviewed_override_ids=_string_list(item.get("reviewed_override_ids")),
            )
        )
    return records


def _capital_readiness_records(bundle: Mapping[str, object]) -> list[CapitalReadinessOperationalRecord]:
    records: list[CapitalReadinessOperationalRecord] = []
    for item in _model_list(bundle, "capital_readiness_drafts"):
        records.append(
            CapitalReadinessOperationalRecord(
                id=str(item.get("id")),
                organization_id=str(item.get("organization_id")),
                report_period=str(item.get("report_period")),
                audience=_optional_text(item.get("audience")),
                draft_status=_optional_text(item.get("draft_status")),
                review_status=_optional_text(item.get("review_status")),
                truth_stage=_optional_text(item.get("truth_stage")),
                readiness_status=_optional_text(item.get("readiness_status")),
                primary_capital_path=_optional_text(item.get("primary_capital_path")),
                secondary_capital_paths=_string_list(item.get("secondary_capital_paths")),
                readiness_rationale=_optional_text(item.get("readiness_rationale")),
                blocking_gaps=_string_list(item.get("blocking_gaps")),
                required_evidence=_string_list(item.get("required_evidence")),
                support_routing_recommendation=_optional_text(item.get("support_routing_recommendation")),
                next_milestone=_optional_text(item.get("next_milestone")),
                linked_domain_score_ids=_string_list(item.get("linked_domain_score_ids")),
                linked_discovery_source_ids=_string_list(item.get("linked_discovery_source_ids")),
                linked_evidence_ids=_string_list(item.get("linked_evidence_ids")),
                linked_review_queue_ids=_string_list(item.get("linked_review_queue_ids")),
                linked_assumption_ids=_string_list(item.get("linked_assumption_ids")),
                generated_by=_optional_text(item.get("generated_by")),
                reviewed_truth_applied=bool(item.get("reviewed_truth_applied", False)),
                reviewed_override_ids=_string_list(item.get("reviewed_override_ids")),
            )
        )
    return records


def _support_routing_records(bundle: Mapping[str, object]) -> list[SupportRoutingOperationalRecord]:
    snapshot = _single_model(bundle, "portfolio_snapshot") or {}
    report_period = str(snapshot.get("report_period"))
    organization_id = str(snapshot.get("organization_id"))
    records: list[SupportRoutingOperationalRecord] = []

    explicit_drafts = _model_list(bundle, "support_routing_drafts")
    if explicit_drafts:
        for draft in explicit_drafts:
            records.append(
                SupportRoutingOperationalRecord(
                    id=str(draft.get("id")),
                    organization_id=organization_id,
                    report_period=report_period,
                    audience=_optional_text(draft.get("audience")) or "internal",
                    route_recommendation=str(draft.get("route_recommendation")),
                    route_category=_optional_text(draft.get("route_category")),
                    route_rationale=_optional_text(draft.get("route_rationale")),
                    priority_domain=_optional_text(draft.get("priority_domain")),
                    route_source_type="support_routing_draft",
                    route_source_id=str(draft.get("id")),
                    source_draft_status=_optional_text(draft.get("draft_status")),
                    source_truth_stage=_optional_text(draft.get("truth_stage")),
                    source_review_status=_optional_text(draft.get("review_status")),
                    linked_domain_score_ids=_string_list(draft.get("linked_domain_score_ids")),
                    linked_capital_readiness_draft_ids=_string_list(draft.get("linked_capital_readiness_draft_ids")),
                    linked_evidence_ids=_string_list(draft.get("linked_evidence_ids")),
                    linked_assumption_ids=_string_list(draft.get("linked_assumption_ids")),
                    linked_review_queue_ids=_string_list(draft.get("linked_review_queue_ids")),
                )
            )
    return records


def _action_item_records(bundle: Mapping[str, object]) -> list[ActionItemOperationalRecord]:
    snapshot = _single_model(bundle, "portfolio_snapshot") or {}
    report_period = str(snapshot.get("report_period"))
    organization_id = str(snapshot.get("organization_id"))
    records: list[ActionItemOperationalRecord] = []

    for score in _model_list(bundle, "domain_scores"):
        next_action = _optional_text(score.get("next_action"))
        if next_action is None:
            continue
        records.append(
            ActionItemOperationalRecord(
                id="action_item:%s:%s" % (organization_id.replace(":", "_"), _slug(score.get("id"))),
                organization_id=organization_id,
                report_period=report_period,
                audience="internal",
                action_text=next_action,
                action_type="domain_score_next_action",
                source_record_type="domain_score",
                source_record_id=str(score.get("id")),
                source_domain_key=_optional_text(score.get("domain_key")),
                source_draft_status=_optional_text(score.get("score_status")),
                source_truth_stage=_optional_text(score.get("truth_stage")),
                source_review_status=_optional_text(score.get("review_status")),
                linked_domain_score_ids=[str(score.get("id"))],
                linked_evidence_ids=_string_list(score.get("score_basis_evidence_ids")),
                linked_assumption_ids=_string_list(score.get("linked_assumption_ids")),
            )
        )

    founder_report = _single_model(bundle, "founder_report_draft") or {}
    for index, action_text in enumerate(_string_list(founder_report.get("recommended_next_actions")), start=1):
        records.append(
            ActionItemOperationalRecord(
                id="action_item:%s:%s_%s" % (
                    organization_id.replace(":", "_"),
                    _slug(founder_report.get("id")),
                    index,
                ),
                organization_id=organization_id,
                report_period=report_period,
                audience="founder",
                action_text=action_text,
                action_type="founder_report_next_action",
                source_record_type="founder_report_draft",
                source_record_id=str(founder_report.get("id")),
                source_domain_key=None,
                source_draft_status=_optional_text(founder_report.get("draft_status")),
                source_truth_stage=_optional_text(founder_report.get("truth_stage")),
                source_review_status=_optional_text(founder_report.get("review_status")),
                linked_domain_score_ids=_string_list(founder_report.get("linked_domain_score_ids")),
                linked_evidence_ids=_string_list(founder_report.get("linked_evidence_ids")),
                linked_assumption_ids=_string_list(founder_report.get("linked_assumption_ids")),
            )
        )
    return records


def _milestone_records(bundle: Mapping[str, object]) -> list[MilestoneOperationalRecord]:
    snapshot = _single_model(bundle, "portfolio_snapshot") or {}
    report_period = str(snapshot.get("report_period"))
    organization_id = str(snapshot.get("organization_id"))
    records: list[MilestoneOperationalRecord] = []

    explicit_drafts = _model_list(bundle, "milestone_drafts")
    if explicit_drafts:
        for draft in explicit_drafts:
            records.append(
                MilestoneOperationalRecord(
                    id=str(draft.get("id")),
                    organization_id=organization_id,
                    report_period=report_period,
                    audience=_optional_text(draft.get("audience")) or "internal",
                    milestone_text=str(draft.get("milestone_statement")),
                    milestone_type=_optional_text(draft.get("milestone_category")) or "milestone_draft",
                    milestone_rationale=_optional_text(draft.get("milestone_rationale")),
                    target_window=_optional_text(draft.get("target_window")),
                    priority_domain=_optional_text(draft.get("priority_domain")),
                    source_record_type="milestone_draft",
                    source_record_id=str(draft.get("id")),
                    source_draft_status=_optional_text(draft.get("draft_status")),
                    source_truth_stage=_optional_text(draft.get("truth_stage")),
                    source_review_status=_optional_text(draft.get("review_status")),
                    linked_domain_score_ids=_string_list(draft.get("linked_domain_score_ids")),
                    linked_capital_readiness_draft_ids=_string_list(draft.get("linked_capital_readiness_draft_ids")),
                    linked_evidence_ids=_string_list(draft.get("linked_evidence_ids")),
                    linked_review_queue_ids=_string_list(draft.get("linked_review_queue_ids")),
                    linked_assumption_ids=_string_list(draft.get("linked_assumption_ids")),
                )
            )
    return records


def build_portfolio_airtable_operational_export(
    bundle: Mapping[str, object],
) -> PortfolioAirtableOperationalExport:
    """Build an Airtable-aligned operational export bundle from a one-company snapshot."""

    snapshot = _single_model(bundle, "portfolio_snapshot")
    if snapshot is None:
        raise ValueError("Portfolio Airtable export requires a portfolio_snapshot bundle entry.")

    return PortfolioAirtableOperationalExport(
        organization_id=str(snapshot.get("organization_id")),
        report_period=str(snapshot.get("report_period")),
        portfolio_snapshot_id=str(snapshot.get("id")),
        companies=[_company_record(bundle)],
        evidence_items=_evidence_item_records(bundle),
        assumptions=_assumption_records(bundle),
        domain_scores=_domain_score_records(bundle),
        capital_readiness=_capital_readiness_records(bundle),
        support_routing=_support_routing_records(bundle),
        action_items=_action_item_records(bundle),
        milestones=_milestone_records(bundle),
    )


def portfolio_airtable_operational_export_to_payload(
    export_bundle: PortfolioAirtableOperationalExport,
) -> dict[str, object]:
    """Convert the typed Airtable operational export into a JSON-friendly payload."""

    return {
        "organization_id": export_bundle.organization_id,
        "report_period": export_bundle.report_period,
        "portfolio_snapshot_id": export_bundle.portfolio_snapshot_id,
        "tables": {
            "Companies": [asdict(record) for record in export_bundle.companies],
            "Evidence Items": [asdict(record) for record in export_bundle.evidence_items],
            "Assumptions": [asdict(record) for record in export_bundle.assumptions],
            "Domain Scores": [asdict(record) for record in export_bundle.domain_scores],
            "Capital Readiness": [asdict(record) for record in export_bundle.capital_readiness],
            "Support Routing": [asdict(record) for record in export_bundle.support_routing],
            "Action Items": [asdict(record) for record in export_bundle.action_items],
            "Milestones": [asdict(record) for record in export_bundle.milestones],
        },
    }


def build_portfolio_airtable_example_summary(
    export_bundle: PortfolioAirtableOperationalExport,
) -> PortfolioAirtableExampleSummary:
    """Build a compact grouped summary for the runnable Airtable-aligned example export."""

    company_record = export_bundle.companies[0] if export_bundle.companies else None
    table_rows = {
        "Companies": export_bundle.companies,
        "Evidence Items": export_bundle.evidence_items,
        "Assumptions": export_bundle.assumptions,
        "Domain Scores": export_bundle.domain_scores,
        "Capital Readiness": export_bundle.capital_readiness,
        "Support Routing": export_bundle.support_routing,
        "Action Items": export_bundle.action_items,
        "Milestones": export_bundle.milestones,
    }
    table_summaries = [
        AirtableOperationalTableSummary(
            table_name=table_name,
            row_count=len(rows),
            record_ids=[getattr(row, "id") for row in rows],
        )
        for table_name, rows in table_rows.items()
    ]

    return PortfolioAirtableExampleSummary(
        organization_id=export_bundle.organization_id,
        report_period=export_bundle.report_period,
        portfolio_snapshot_id=export_bundle.portfolio_snapshot_id,
        company_name=None if company_record is None else company_record.company_name,
        source_truth_statement="" if company_record is None else company_record.source_truth_statement,
        draft_boundary_statement="" if company_record is None else company_record.draft_boundary_statement,
        founder_report_draft_status=None if company_record is None else company_record.founder_report_draft_status,
        internal_report_draft_status=None if company_record is None else company_record.internal_report_draft_status,
        tables=table_summaries,
    )


def portfolio_airtable_operational_export_from_payload(
    payload: Mapping[str, object],
) -> PortfolioAirtableOperationalExport:
    """Load a typed Airtable operational export bundle from JSON-friendly payload."""

    tables = payload.get("tables", {})
    if not isinstance(tables, Mapping):
        raise ValueError("Portfolio Airtable export payload must define tables as an object.")

    def _rows(table_name: str) -> list[Mapping[str, object]]:
        raw_rows = tables.get(table_name, [])
        if not isinstance(raw_rows, list):
            raise ValueError("%s rows must be a list." % table_name)
        rows: list[Mapping[str, object]] = []
        for row in raw_rows:
            if not isinstance(row, Mapping):
                raise ValueError("%s rows must contain objects." % table_name)
            rows.append(row)
        return rows

    return PortfolioAirtableOperationalExport(
        organization_id=str(payload.get("organization_id")),
        report_period=str(payload.get("report_period")),
        portfolio_snapshot_id=str(payload.get("portfolio_snapshot_id")),
        companies=[CompanyOperationalRecord(**row) for row in _rows("Companies")],
        evidence_items=[EvidenceItemOperationalRecord(**row) for row in _rows("Evidence Items")],
        assumptions=[AssumptionOperationalRecord(**row) for row in _rows("Assumptions")],
        domain_scores=[DomainScoreOperationalRecord(**row) for row in _rows("Domain Scores")],
        capital_readiness=[CapitalReadinessOperationalRecord(**row) for row in _rows("Capital Readiness")],
        support_routing=[SupportRoutingOperationalRecord(**row) for row in _rows("Support Routing")],
        action_items=[ActionItemOperationalRecord(**row) for row in _rows("Action Items")],
        milestones=[MilestoneOperationalRecord(**row) for row in _rows("Milestones")],
    )


def write_portfolio_airtable_operational_exports(
    export_bundle: PortfolioAirtableOperationalExport,
    output_dir: Path,
) -> list[Path]:
    """Write Airtable-aligned operational export tables as inspectable JSON files."""

    output_dir.mkdir(parents=True, exist_ok=True)
    payload = portfolio_airtable_operational_export_to_payload(export_bundle)
    tables = payload["tables"]
    assert isinstance(tables, Mapping)

    written_paths: list[Path] = []
    for table_name in AIRTABLE_OPERATIONAL_TABLES:
        table_path = output_dir / AIRTABLE_OPERATIONAL_FILENAMES[table_name]
        table_path.write_text(json.dumps(tables[table_name], indent=2, default=_json_default) + "\n", encoding="utf-8")
        written_paths.append(table_path)

    example_summary = build_portfolio_airtable_example_summary(export_bundle)
    summary_path = output_dir / "airtable_operational_example_summary.json"
    summary_path.write_text(
        json.dumps(asdict(example_summary), indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    written_paths.append(summary_path)

    export_manifest = {
        "artifact_type": "portfolio_airtable_operational_export",
        "organization_id": export_bundle.organization_id,
        "report_period": export_bundle.report_period,
        "portfolio_snapshot_id": export_bundle.portfolio_snapshot_id,
        "tables": [
            {
                "table_name": table_name,
                "filename": AIRTABLE_OPERATIONAL_FILENAMES[table_name],
                "row_count": len(tables[table_name]),
            }
            for table_name in AIRTABLE_OPERATIONAL_TABLES
        ],
    }
    manifest_path = output_dir / "airtable_operational_export_manifest.json"
    manifest_path.write_text(json.dumps(export_manifest, indent=2, default=_json_default) + "\n", encoding="utf-8")
    written_paths.append(manifest_path)

    full_bundle_path = output_dir / "airtable_operational_export.json"
    full_bundle_path.write_text(json.dumps(payload, indent=2, default=_json_default) + "\n", encoding="utf-8")
    written_paths.append(full_bundle_path)
    return written_paths
