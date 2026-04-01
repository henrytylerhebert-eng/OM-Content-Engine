"""Lightweight reviewed-truth overrides applied after normalization."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OVERRIDES_PATH = REPO_ROOT / "data" / "reviewed_truth" / "overrides.json"

NORMALIZED_TARGETS = {
    "organizations",
    "people",
    "affiliations",
    "programs",
    "cohorts",
    "participations",
    "mentor_profiles",
}
CONTENT_TARGETS = {
    "organization_content": "organizations",
    "person_content": "people",
}
REVIEW_ROW_TARGET = "review_rows"
SUPPORTED_TARGETS = NORMALIZED_TARGETS | set(CONTENT_TARGETS.keys()) | {REVIEW_ROW_TARGET}
CONTENT_ONLY_FIELDS = {"externally_publishable"}


@dataclass(frozen=True)
class OverrideRule:
    """Single reviewed-truth rule loaded from JSON."""

    rule_id: str
    target: str
    match: dict[str, object]
    set_values: dict[str, object] = field(default_factory=dict)
    suppress: bool = False
    reason: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    note: Optional[str] = None


@dataclass(frozen=True)
class OverrideDocument:
    """Loaded override document plus normalized rule objects."""

    file_path: Optional[str]
    version: int
    description: Optional[str]
    rules: list[OverrideRule]


def _normalize_text(value: object) -> str:
    return " ".join(str(value).strip().split()).lower()


def _values_equal(actual: object, expected: object) -> bool:
    if isinstance(expected, bool):
        if isinstance(actual, bool):
            return actual is expected
        return _normalize_text(actual) == ("true" if expected else "false")
    if expected is None:
        return actual in (None, "", [])
    if isinstance(actual, list):
        if isinstance(expected, list):
            return actual == expected
        return any(_values_equal(item, expected) for item in actual)
    return _normalize_text(actual) == _normalize_text(expected)


def _record_matches(record: Mapping[str, object], match_fields: Mapping[str, object]) -> bool:
    if not match_fields:
        return False
    return all(_values_equal(record.get(field_name), expected_value) for field_name, expected_value in match_fields.items())


def _append_override_metadata(record: dict[str, object], rule: OverrideRule) -> None:
    existing_ids = list(record.get("reviewed_override_ids", []))
    if rule.rule_id not in existing_ids:
        existing_ids.append(rule.rule_id)
    record["reviewed_override_ids"] = existing_ids
    record["reviewed_truth_applied"] = True


def _application_row(
    rule: OverrideRule,
    *,
    matched_count: int,
    updated_count: int,
    suppressed_count: int,
) -> dict[str, object]:
    status = "unmatched"
    if suppressed_count:
        status = "suppressed"
    elif updated_count:
        status = "updated"

    return {
        "rule_id": rule.rule_id,
        "target": rule.target,
        "matched_count": matched_count,
        "updated_count": updated_count,
        "suppressed_count": suppressed_count,
        "status": status,
        "reason": rule.reason,
        "reviewed_by": rule.reviewed_by,
        "reviewed_at": rule.reviewed_at,
        "note": rule.note,
    }


def _rule_from_payload(index: int, payload: Mapping[str, object]) -> OverrideRule:
    rule_id = str(payload.get("id") or "override_%s" % index)
    target = str(payload.get("target") or "").strip()
    match = payload.get("match") or {}
    set_values = payload.get("set") or {}
    if target not in SUPPORTED_TARGETS:
        raise ValueError("Unsupported reviewed-truth target: %s" % target)
    if not isinstance(match, dict):
        raise ValueError("Override rule %s must use an object for match." % rule_id)
    if not isinstance(set_values, dict):
        raise ValueError("Override rule %s must use an object for set." % rule_id)
    if target not in CONTENT_TARGETS and CONTENT_ONLY_FIELDS.intersection(set_values.keys()):
        raise ValueError(
            "Override rule %s uses content-only fields on %s. "
            "Use organization_content or person_content for externally publishable decisions."
            % (rule_id, target)
        )

    return OverrideRule(
        rule_id=rule_id,
        target=target,
        match=dict(match),
        set_values=dict(set_values),
        suppress=bool(payload.get("suppress", False)),
        reason=None if payload.get("reason") is None else str(payload.get("reason")),
        reviewed_by=None if payload.get("reviewed_by") is None else str(payload.get("reviewed_by")),
        reviewed_at=None if payload.get("reviewed_at") is None else str(payload.get("reviewed_at")),
        note=None if payload.get("note") is None else str(payload.get("note")),
    )


def load_override_document(file_path: Optional[Path] = DEFAULT_OVERRIDES_PATH) -> OverrideDocument:
    """Load a reviewed-truth override file or return an empty document."""

    if file_path is None or not file_path.exists():
        return OverrideDocument(file_path=None if file_path is None else str(file_path), version=1, description=None, rules=[])

    with file_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    raw_rules = payload.get("rules", [])
    if not isinstance(raw_rules, list):
        raise ValueError("Reviewed-truth overrides must define rules as a list.")

    rules = [_rule_from_payload(index, item) for index, item in enumerate(raw_rules, start=1)]
    return OverrideDocument(
        file_path=str(file_path),
        version=int(payload.get("version", 1)),
        description=None if payload.get("description") is None else str(payload.get("description")),
        rules=rules,
    )


def _apply_rules_to_records(
    records: Sequence[dict[str, object]],
    *,
    rules: Sequence[OverrideRule],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    working = deepcopy(list(records))
    applications: list[dict[str, object]] = []

    for rule in rules:
        matched_indexes = [index for index, record in enumerate(working) if _record_matches(record, rule.match)]
        updated_count = 0
        suppressed_count = 0

        if rule.suppress:
            for index in reversed(matched_indexes):
                working.pop(index)
                suppressed_count += 1
        else:
            for index in matched_indexes:
                record = dict(working[index])
                for field_name, value in rule.set_values.items():
                    record[field_name] = value
                _append_override_metadata(record, rule)
                working[index] = record
                updated_count += 1

        applications.append(
            _application_row(
                rule,
                matched_count=len(matched_indexes),
                updated_count=updated_count,
                suppressed_count=suppressed_count,
            )
        )

    return working, applications


def apply_normalized_overrides(
    normalized: Mapping[str, Sequence[dict[str, object]]],
    override_document: OverrideDocument,
) -> tuple[dict[str, list[dict[str, object]]], list[dict[str, object]]]:
    """Apply reviewed-truth overrides to normalized collections."""

    reviewed: dict[str, list[dict[str, object]]] = {}
    applications: list[dict[str, object]] = []

    for collection_name in (
        "organizations",
        "people",
        "affiliations",
        "programs",
        "cohorts",
        "participations",
        "mentor_profiles",
    ):
        rules = [rule for rule in override_document.rules if rule.target == collection_name]
        reviewed_records, collection_applications = _apply_rules_to_records(
            normalized.get(collection_name, []),  # type: ignore[arg-type]
            rules=rules,
        )
        reviewed[collection_name] = reviewed_records
        applications.extend(collection_applications)

    return reviewed, applications


def apply_content_bundle_overrides(
    content_bundle: Mapping[str, object],
    override_document: OverrideDocument,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    """Apply reviewed-truth overrides to derived content-intelligence records."""

    reviewed_bundle = deepcopy(dict(content_bundle))
    applications: list[dict[str, object]] = []

    for target_name, collection_name in CONTENT_TARGETS.items():
        rules = [rule for rule in override_document.rules if rule.target == target_name]
        reviewed_records, collection_applications = _apply_rules_to_records(
            reviewed_bundle.get(collection_name, []),  # type: ignore[arg-type]
            rules=rules,
        )
        reviewed_bundle[collection_name] = reviewed_records
        applications.extend(collection_applications)

    return reviewed_bundle, applications


def apply_review_row_overrides(
    review_rows: Sequence[dict[str, object]],
    override_document: OverrideDocument,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Apply reviewed-truth overrides to the exported review queue."""

    rules = [rule for rule in override_document.rules if rule.target == REVIEW_ROW_TARGET]
    return _apply_rules_to_records(review_rows, rules=rules)


def build_reviewed_truth_artifact(
    *,
    override_document: OverrideDocument,
    reviewed_collections: Mapping[str, Sequence[dict[str, object]]],
    review_rows: Sequence[dict[str, object]],
    applications: Sequence[dict[str, object]],
) -> dict[str, object]:
    """Build a JSON-friendly reviewed-truth artifact for inspection."""

    unmatched_rules = [row for row in applications if row.get("matched_count") == 0]
    return {
        "override_file_path": override_document.file_path,
        "version": override_document.version,
        "description": override_document.description,
        "rule_count": len(override_document.rules),
        "applied_rule_count": len([row for row in applications if row.get("matched_count")]),
        "unmatched_rule_count": len(unmatched_rules),
        "applications": list(applications),
        "collections": {key: list(value) for key, value in reviewed_collections.items()},
        "review_rows": list(review_rows),
    }
