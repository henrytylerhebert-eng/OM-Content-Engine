"""Patch-only reviewed-truth overrides for portfolio workflow records."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Mapping, Optional, Sequence

from src.portfolio.constants import (
    CapitalReadinessStatus,
    DraftStatus,
    QueueStatus,
    ReviewStatus,
    ScoreConfidence,
    ScoreStatus,
    TruthStage,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PORTFOLIO_OVERRIDES_PATH = REPO_ROOT / "data" / "reviewed_truth" / "portfolio_overrides.json"
EXAMPLE_PORTFOLIO_OVERRIDES_PATH = REPO_ROOT / "data" / "reviewed_truth" / "portfolio_example_overrides.json"

PORTFOLIO_OVERRIDE_TARGETS = {
    "evidence_items",
    "domain_scores",
    "capital_readiness_drafts",
    "founder_report_draft",
    "internal_report_draft",
    "review_queue_items",
}
SINGULAR_TARGETS = {"founder_report_draft", "internal_report_draft"}
LIST_TARGETS = PORTFOLIO_OVERRIDE_TARGETS - SINGULAR_TARGETS
PHASE_ONE_INTERNAL_TRUTH_STAGES = {
    TruthStage.INTERPRETED_EVIDENCE.value,
    TruthStage.REVIEWED_EVIDENCE.value,
    TruthStage.INTERNALLY_APPROVED_OUTPUT.value,
}
PHASE_ONE_INTERNAL_REVIEW_STATUSES = {
    ReviewStatus.PENDING_REVIEW.value,
    ReviewStatus.IN_REVIEW.value,
    ReviewStatus.REVIEWED.value,
    ReviewStatus.INTERNALLY_APPROVED.value,
}

ALLOWED_SET_FIELDS = {
    "evidence_items": {
        "truth_stage",
        "review_status",
        "review_notes",
        "reviewed_by",
        "reviewed_at",
    },
    "domain_scores": {
        "raw_score",
        "confidence",
        "evidence_level",
        "rationale",
        "key_gap",
        "next_action",
        "score_status",
        "review_status",
        "review_notes",
        "reviewed_by",
        "reviewed_at",
    },
    "capital_readiness_drafts": {
        "draft_status",
        "readiness_status",
        "readiness_rationale",
        "blocking_gaps",
        "required_evidence",
        "support_routing_recommendation",
        "next_milestone",
        "review_status",
        "truth_stage",
        "review_notes",
        "reviewed_by",
        "reviewed_at",
        "internal_approved_by",
        "internal_approved_at",
    },
    "founder_report_draft": {
        "draft_status",
        "review_status",
        "truth_stage",
        "review_notes",
        "reviewed_by",
        "reviewed_at",
        "internal_approved_by",
        "internal_approved_at",
    },
    "internal_report_draft": {
        "draft_status",
        "review_status",
        "truth_stage",
        "review_notes",
        "reviewed_by",
        "reviewed_at",
        "internal_approved_by",
        "internal_approved_at",
    },
    "review_queue_items": {
        "queue_status",
        "resolution_note",
        "resolved_at",
        "owner",
        "note",
    },
}


@dataclass(frozen=True)
class PortfolioOverrideRule:
    """Single portfolio reviewed-truth rule loaded from JSON."""

    rule_id: str
    target: str
    match: dict[str, object]
    set_values: dict[str, object] = field(default_factory=dict)
    reason: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    note: Optional[str] = None


@dataclass(frozen=True)
class PortfolioOverrideDocument:
    """Loaded portfolio override document plus normalized rule objects."""

    file_path: Optional[str]
    version: int
    description: Optional[str]
    rules: list[PortfolioOverrideRule]


@dataclass(frozen=True)
class PortfolioOverrideUpsertResult:
    """Result of creating or updating one portfolio override rule on disk."""

    file_path: str
    action: str
    document: PortfolioOverrideDocument
    rule: PortfolioOverrideRule


def _normalize_text(value: object) -> str:
    return " ".join(str(value).strip().split()).lower()


def _values_equal(actual: object, expected: object) -> bool:
    if expected is None:
        return actual in (None, "", [])
    if isinstance(expected, list):
        return actual == expected
    if isinstance(actual, list):
        return any(_values_equal(item, expected) for item in actual)
    return _normalize_text(actual) == _normalize_text(expected)


def _record_matches(record: Mapping[str, object], match_fields: Mapping[str, object]) -> bool:
    if not match_fields:
        return False
    return all(_values_equal(record.get(field_name), expected_value) for field_name, expected_value in match_fields.items())


def _append_override_metadata(record: dict[str, object], rule: PortfolioOverrideRule) -> None:
    override_ids = list(record.get("reviewed_override_ids", []))
    if rule.rule_id not in override_ids:
        override_ids.append(rule.rule_id)
    record["reviewed_override_ids"] = override_ids
    record["reviewed_truth_applied"] = True


def _application_row(rule: PortfolioOverrideRule, *, matched_count: int, updated_count: int) -> dict[str, object]:
    return {
        "rule_id": rule.rule_id,
        "target": rule.target,
        "matched_count": matched_count,
        "updated_count": updated_count,
        "status": "updated" if updated_count else "unmatched",
        "reason": rule.reason,
        "reviewed_by": rule.reviewed_by,
        "reviewed_at": rule.reviewed_at,
        "note": rule.note,
    }


def _validate_target_fields(rule_id: str, target: str, set_values: Mapping[str, object]) -> None:
    disallowed_fields = set(set_values) - ALLOWED_SET_FIELDS[target]
    if disallowed_fields:
        raise ValueError(
            "Portfolio override rule %s uses unsupported fields for %s: %s."
            % (rule_id, target, ", ".join(sorted(disallowed_fields)))
        )


def _validate_evidence_override(rule_id: str, set_values: Mapping[str, object]) -> None:
    truth_stage = set_values.get("truth_stage")
    review_status = set_values.get("review_status")
    if truth_stage is not None and truth_stage != TruthStage.REVIEWED_EVIDENCE.value:
        raise ValueError("Portfolio override rule %s may only promote evidence to reviewed_evidence." % rule_id)
    if review_status is not None and review_status != ReviewStatus.REVIEWED.value:
        raise ValueError("Portfolio override rule %s may only mark evidence as reviewed." % rule_id)


def _validate_domain_score_override(rule_id: str, set_values: Mapping[str, object]) -> None:
    raw_score = set_values.get("raw_score")
    if raw_score is not None and int(raw_score) not in (1, 2, 3, 4, 5):
        raise ValueError("Portfolio override rule %s must keep domain score raw_score within 1-5." % rule_id)

    evidence_level = set_values.get("evidence_level")
    if evidence_level is not None and int(evidence_level) not in range(0, 8):
        raise ValueError("Portfolio override rule %s must keep domain score evidence_level within 0-7." % rule_id)

    confidence = set_values.get("confidence")
    if confidence is not None:
        ScoreConfidence(str(confidence))

    score_status = set_values.get("score_status")
    if score_status is not None:
        ScoreStatus(str(score_status))

    review_status = set_values.get("review_status")
    if review_status is not None and str(review_status) not in {
        ReviewStatus.PENDING_REVIEW.value,
        ReviewStatus.IN_REVIEW.value,
        ReviewStatus.REVIEWED.value,
    }:
        raise ValueError("Portfolio override rule %s may only use pending_review, in_review, or reviewed on domain scores." % rule_id)


def _validate_internal_draft_override(rule_id: str, set_values: Mapping[str, object], *, label: str) -> None:
    draft_status = set_values.get("draft_status")
    if draft_status is not None:
        DraftStatus(str(draft_status))

    review_status = set_values.get("review_status")
    if review_status is not None and str(review_status) not in PHASE_ONE_INTERNAL_REVIEW_STATUSES:
        raise ValueError("%s override rule %s cannot use external review states in phase one." % (label, rule_id))

    truth_stage = set_values.get("truth_stage")
    if truth_stage is not None and str(truth_stage) not in PHASE_ONE_INTERNAL_TRUTH_STAGES:
        raise ValueError("%s override rule %s cannot use external truth stages in phase one." % (label, rule_id))

    if truth_stage == TruthStage.INTERNALLY_APPROVED_OUTPUT.value and review_status not in (
        ReviewStatus.INTERNALLY_APPROVED.value,
        None,
    ):
        raise ValueError("%s override rule %s must use internally_approved review_status with internally_approved_output." % (label, rule_id))


def _validate_capital_readiness_override(rule_id: str, set_values: Mapping[str, object]) -> None:
    _validate_internal_draft_override(rule_id, set_values, label="CapitalReadinessDraft")

    readiness_status = set_values.get("readiness_status")
    if readiness_status is not None:
        CapitalReadinessStatus(str(readiness_status))


def _validate_review_queue_override(rule_id: str, set_values: Mapping[str, object]) -> None:
    queue_status = set_values.get("queue_status")
    if queue_status is not None:
        QueueStatus(str(queue_status))

    if (set_values.get("resolved_at") is not None or set_values.get("resolution_note") is not None) and queue_status not in (
        QueueStatus.RESOLVED.value,
        None,
    ):
        raise ValueError("Portfolio override rule %s must set queue_status to resolved when adding resolution fields." % rule_id)


def _validate_rule_payload(rule_id: str, target: str, set_values: Mapping[str, object]) -> None:
    _validate_target_fields(rule_id, target, set_values)

    if target == "evidence_items":
        _validate_evidence_override(rule_id, set_values)
    elif target == "domain_scores":
        _validate_domain_score_override(rule_id, set_values)
    elif target == "capital_readiness_drafts":
        _validate_capital_readiness_override(rule_id, set_values)
    elif target in {"founder_report_draft", "internal_report_draft"}:
        _validate_internal_draft_override(rule_id, set_values, label=target)
    elif target == "review_queue_items":
        _validate_review_queue_override(rule_id, set_values)


def _rule_from_payload(index: int, payload: Mapping[str, object]) -> PortfolioOverrideRule:
    rule_id = str(payload.get("id") or "portfolio_override_%s" % index)
    target = str(payload.get("target") or "").strip()
    match = payload.get("match") or {}
    set_values = payload.get("set") or {}

    if target not in PORTFOLIO_OVERRIDE_TARGETS:
        raise ValueError("Unsupported portfolio reviewed-truth target: %s" % target)
    if bool(payload.get("suppress", False)):
        raise ValueError(
            "Portfolio override rule %s cannot use suppress. Phase-one portfolio overrides are patch-only." % rule_id
        )
    if not isinstance(match, dict):
        raise ValueError("Portfolio override rule %s must use an object for match." % rule_id)
    if not isinstance(set_values, dict):
        raise ValueError("Portfolio override rule %s must use an object for set." % rule_id)

    _validate_rule_payload(rule_id, target, set_values)

    return PortfolioOverrideRule(
        rule_id=rule_id,
        target=target,
        match=dict(match),
        set_values=dict(set_values),
        reason=None if payload.get("reason") is None else str(payload.get("reason")),
        reviewed_by=None if payload.get("reviewed_by") is None else str(payload.get("reviewed_by")),
        reviewed_at=None if payload.get("reviewed_at") is None else str(payload.get("reviewed_at")),
        note=None if payload.get("note") is None else str(payload.get("note")),
    )


def create_portfolio_override_rule(payload: Mapping[str, object]) -> PortfolioOverrideRule:
    """Create and validate one portfolio override rule from a JSON-friendly payload."""

    return _rule_from_payload(1, payload)


def portfolio_override_rule_to_payload(rule: PortfolioOverrideRule) -> dict[str, object]:
    """Convert a normalized portfolio override rule back into JSON-friendly form."""

    payload: dict[str, object] = {
        "id": rule.rule_id,
        "target": rule.target,
        "match": dict(rule.match),
        "set": dict(rule.set_values),
    }
    if rule.reason is not None:
        payload["reason"] = rule.reason
    if rule.reviewed_by is not None:
        payload["reviewed_by"] = rule.reviewed_by
    if rule.reviewed_at is not None:
        payload["reviewed_at"] = rule.reviewed_at
    if rule.note is not None:
        payload["note"] = rule.note
    return payload


def portfolio_override_document_to_payload(document: PortfolioOverrideDocument) -> dict[str, object]:
    """Convert a portfolio override document into a JSON-friendly payload."""

    payload: dict[str, object] = {
        "version": document.version,
        "rules": [portfolio_override_rule_to_payload(rule) for rule in document.rules],
    }
    if document.description is not None:
        payload["description"] = document.description
    return payload


def load_portfolio_override_document(
    file_path: Optional[Path] = DEFAULT_PORTFOLIO_OVERRIDES_PATH,
) -> PortfolioOverrideDocument:
    """Load a portfolio reviewed-truth override file or return an empty document."""

    if file_path is None or not file_path.exists():
        return PortfolioOverrideDocument(
            file_path=None if file_path is None else str(file_path),
            version=1,
            description=None,
            rules=[],
        )

    payload = json.loads(file_path.read_text(encoding="utf-8"))
    raw_rules = payload.get("rules", [])
    if not isinstance(raw_rules, list):
        raise ValueError("Portfolio reviewed-truth overrides must define rules as a list.")

    rules = [_rule_from_payload(index, item) for index, item in enumerate(raw_rules, start=1)]
    return PortfolioOverrideDocument(
        file_path=str(file_path),
        version=int(payload.get("version", 1)),
        description=None if payload.get("description") is None else str(payload.get("description")),
        rules=rules,
    )


def write_portfolio_override_document(document: PortfolioOverrideDocument, file_path: Path) -> None:
    """Write a validated portfolio override document back to disk."""

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(portfolio_override_document_to_payload(document), indent=2) + "\n",
        encoding="utf-8",
    )


def upsert_portfolio_override_rule(
    file_path: Path,
    rule: PortfolioOverrideRule,
    *,
    description: Optional[str] = None,
) -> PortfolioOverrideUpsertResult:
    """Create or update one portfolio override rule in a file-backed document."""

    current_document = load_portfolio_override_document(file_path)
    updated_rules = list(current_document.rules)
    action = "created"

    for index, existing_rule in enumerate(updated_rules):
        if existing_rule.rule_id != rule.rule_id:
            continue
        if existing_rule.target != rule.target:
            raise ValueError(
                "Portfolio override rule %s already exists for target %s and cannot be reassigned to %s."
                % (rule.rule_id, existing_rule.target, rule.target)
            )
        updated_rules[index] = rule
        action = "updated"
        break
    else:
        updated_rules.append(rule)

    updated_document = PortfolioOverrideDocument(
        file_path=str(file_path),
        version=current_document.version,
        description=current_document.description if description is None else description,
        rules=updated_rules,
    )
    write_portfolio_override_document(updated_document, file_path)
    return PortfolioOverrideUpsertResult(
        file_path=str(file_path),
        action=action,
        document=updated_document,
        rule=rule,
    )


def _apply_rules_to_records(
    records: Sequence[dict[str, object]],
    *,
    rules: Sequence[PortfolioOverrideRule],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    working = deepcopy(list(records))
    applications: list[dict[str, object]] = []

    for rule in rules:
        matched_indexes = [index for index, record in enumerate(working) if _record_matches(record, rule.match)]
        updated_count = 0

        for index in matched_indexes:
            record = dict(working[index])
            for field_name, value in rule.set_values.items():
                record[field_name] = value
            _append_override_metadata(record, rule)
            working[index] = record
            updated_count += 1

        applications.append(_application_row(rule, matched_count=len(matched_indexes), updated_count=updated_count))

    return working, applications


def _refresh_portfolio_snapshot(bundle: dict[str, object]) -> None:
    snapshot = dict(bundle.get("portfolio_snapshot", {}))
    evidence_items = list(bundle.get("evidence_items", []))
    domain_scores = list(bundle.get("domain_scores", []))
    capital_readiness_drafts = list(bundle.get("capital_readiness_drafts", []))
    support_routing_drafts = list(bundle.get("support_routing_drafts", []))
    milestone_drafts = list(bundle.get("milestone_drafts", []))
    founder_report_draft = bundle.get("founder_report_draft")
    internal_report_draft = bundle.get("internal_report_draft")

    snapshot["discovery_source_count"] = len(bundle.get("discovery_sources", []))
    snapshot["evidence_item_count"] = len(evidence_items)
    snapshot["reviewed_evidence_count"] = len(
        [item for item in evidence_items if item.get("truth_stage") == TruthStage.REVIEWED_EVIDENCE.value]
    )
    snapshot["pending_evidence_count"] = len(evidence_items) - int(snapshot["reviewed_evidence_count"])
    snapshot["assumption_count"] = len(bundle.get("assumptions", []))
    snapshot["domain_score_count"] = len(domain_scores)
    snapshot["review_ready_domain_score_count"] = len(
        [item for item in domain_scores if item.get("score_status") == ScoreStatus.REVIEW_READY.value]
    )
    snapshot["capital_readiness_draft_count"] = len(capital_readiness_drafts)
    snapshot["review_ready_capital_readiness_draft_count"] = len(
        [item for item in capital_readiness_drafts if item.get("draft_status") == DraftStatus.REVIEW_READY.value]
    )
    snapshot["support_routing_draft_count"] = len(support_routing_drafts)
    snapshot["review_ready_support_routing_draft_count"] = len(
        [item for item in support_routing_drafts if item.get("draft_status") == DraftStatus.REVIEW_READY.value]
    )
    snapshot["milestone_draft_count"] = len(milestone_drafts)
    snapshot["review_ready_milestone_draft_count"] = len(
        [item for item in milestone_drafts if item.get("draft_status") == DraftStatus.REVIEW_READY.value]
    )
    snapshot["review_queue_item_count"] = len(bundle.get("review_queue_items", []))
    snapshot["founder_report_draft_id"] = None if founder_report_draft is None else founder_report_draft.get("id")
    snapshot["founder_report_draft_status"] = (
        None if founder_report_draft is None else founder_report_draft.get("draft_status")
    )
    snapshot["internal_report_draft_id"] = None if internal_report_draft is None else internal_report_draft.get("id")
    snapshot["internal_report_draft_status"] = (
        None if internal_report_draft is None else internal_report_draft.get("draft_status")
    )
    bundle["portfolio_snapshot"] = snapshot


def apply_portfolio_overrides(
    bundle: Mapping[str, object],
    override_document: PortfolioOverrideDocument,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    """Apply patch-only reviewed-truth overrides to a portfolio snapshot bundle."""

    reviewed_bundle = deepcopy(dict(bundle))
    applications: list[dict[str, object]] = []

    for target in LIST_TARGETS:
        rules = [rule for rule in override_document.rules if rule.target == target]
        reviewed_records, target_applications = _apply_rules_to_records(
            reviewed_bundle.get(target, []),  # type: ignore[arg-type]
            rules=rules,
        )
        reviewed_bundle[target] = reviewed_records
        applications.extend(target_applications)

    for target in SINGULAR_TARGETS:
        rules = [rule for rule in override_document.rules if rule.target == target]
        current_record = reviewed_bundle.get(target)
        source_records = [] if current_record is None else [current_record]
        reviewed_records, target_applications = _apply_rules_to_records(
            source_records,  # type: ignore[arg-type]
            rules=rules,
        )
        reviewed_bundle[target] = None if not reviewed_records else reviewed_records[0]
        applications.extend(target_applications)

    _refresh_portfolio_snapshot(reviewed_bundle)
    return reviewed_bundle, applications


def build_portfolio_reviewed_truth_artifact(
    *,
    override_document: PortfolioOverrideDocument,
    applications: Sequence[dict[str, object]],
    snapshot_summary: Mapping[str, object],
) -> dict[str, object]:
    """Build a JSON-friendly artifact describing applied portfolio override rules."""

    unmatched_rules = [row for row in applications if row.get("matched_count") == 0]
    return {
        "override_file_path": override_document.file_path,
        "version": override_document.version,
        "description": override_document.description,
        "rule_count": len(override_document.rules),
        "applied_rule_count": len([row for row in applications if row.get("matched_count")]),
        "unmatched_rule_count": len(unmatched_rules),
        "applications": list(applications),
        "snapshot_summary": dict(snapshot_summary),
    }
