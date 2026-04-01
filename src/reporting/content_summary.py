"""Content-focused reporting helpers built from the content intelligence bundle."""

from __future__ import annotations

from collections import Counter
from typing import Optional, Sequence


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "active"}


def _record_key(record: dict[str, object]) -> Optional[object]:
    value = record.get("id")
    if value is not None:
        return value
    return record.get("source_record_id")


def _split_missing_assets(value: object) -> list[str]:
    if value is None:
        return []
    return [part.strip() for part in str(value).split(",") if part.strip()]


def _override_ids(record: Optional[dict[str, object]]) -> list[str]:
    if record is None:
        return []
    value = record.get("reviewed_override_ids", [])
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _reviewed_truth_applied(record: Optional[dict[str, object]]) -> bool:
    if record is None:
        return False
    return _truthy(record.get("reviewed_truth_applied")) or bool(_override_ids(record))


def reviewed_truth_applied(record: Optional[dict[str, object]]) -> bool:
    """Return whether reviewed truth touched the record."""

    return _reviewed_truth_applied(record)


def derive_review_state(record: dict[str, object]) -> str:
    """Return whether a normalized record is source-derived or review-backed."""

    return "reviewed_truth_backed" if _reviewed_truth_applied(record) else "source_derived"


def _reviewed_override_count(*records: Optional[dict[str, object]]) -> int:
    override_ids: set[str] = set()
    for record in records:
        override_ids.update(_override_ids(record))
    return len(override_ids)


def reviewed_override_count(*records: Optional[dict[str, object]]) -> int:
    """Return the deduplicated override count across one or more records."""

    return _reviewed_override_count(*records)


def derive_person_source_path(person: dict[str, object]) -> str:
    """Classify how a person record entered the normalized layer."""

    if str(person.get("person_type") or "").strip().lower() == "mentor":
        return "mentor_structured"
    if str(person.get("person_resolution_basis") or "").strip().lower() == "semi_structured_member_side":
        return "semi_structured_member_side"
    return "structured_member_fields"


def derive_content_trust_basis(
    intelligence: dict[str, object],
    linked_record: Optional[dict[str, object]],
) -> str:
    """Return whether content readiness is heuristic, reviewed, or human-approved."""

    if _truthy(intelligence.get("externally_publishable")):
        return "human_approved"
    if _reviewed_truth_applied(intelligence) or _reviewed_truth_applied(linked_record):
        return "reviewed_truth_backed"
    return "heuristic_only"


def derive_highest_readiness_level(record: dict[str, object]) -> str:
    """Return the highest readiness level reached by a content-intelligence row."""

    if _truthy(record.get("externally_publishable")):
        return "externally_publishable"
    if _truthy(record.get("spotlight_ready")):
        return "spotlight_ready"
    if _truthy(record.get("content_ready")):
        return "content_ready"
    if _truthy(record.get("internally_usable")):
        return "internally_usable"
    return "below_internal"


def _sort_by_score_and_label(rows: list[dict[str, object]], label_field: str) -> list[dict[str, object]]:
    return sorted(
        rows,
        key=lambda row: (-int(row.get("profile_completeness_score") or 0), str(row.get(label_field) or "")),
    )


def _organization_content_rows(
    content_bundle: dict[str, object],
    organizations: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Build reporting rows for organization-level content intelligence."""

    organizations_by_key = {
        _record_key(organization): organization
        for organization in organizations
        if _record_key(organization) is not None
    }
    rows: list[dict[str, object]] = []
    for item in content_bundle.get("organizations", []):
        intelligence = dict(item)
        organization = organizations_by_key.get(intelligence.get("linked_organization_id"))
        rows.append(
            {
                "organization_name": None if organization is None else organization.get("name"),
                "org_type": None if organization is None else organization.get("org_type"),
                "trust_basis": derive_content_trust_basis(intelligence, organization),
                "reviewed_truth_applied": _reviewed_truth_applied(intelligence) or _reviewed_truth_applied(organization),
                "reviewed_override_count": _reviewed_override_count(intelligence, organization),
                "internally_usable": intelligence.get("internally_usable"),
                "content_ready": intelligence.get("content_ready"),
                "spotlight_ready": intelligence.get("spotlight_ready"),
                "externally_publishable": intelligence.get("externally_publishable"),
                "profile_completeness_score": intelligence.get("profile_completeness_score"),
                "story_type": intelligence.get("story_type"),
                "message_pillar": intelligence.get("message_pillar"),
                "missing_content_assets": intelligence.get("missing_content_assets"),
            }
        )
    return _sort_by_score_and_label(rows, "organization_name")


def _person_content_rows(
    content_bundle: dict[str, object],
    people_payloads: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Build reporting rows for person-level content intelligence."""

    people_by_key = {
        _record_key(person): person
        for person in people_payloads
        if _record_key(person) is not None
    }
    rows: list[dict[str, object]] = []
    for item in content_bundle.get("people", []):
        intelligence = dict(item)
        person = people_by_key.get(intelligence.get("linked_person_id"))
        rows.append(
            {
                "full_name": None if person is None else person.get("full_name"),
                "person_type": None if person is None else person.get("person_type"),
                "person_resolution_basis": None if person is None else person.get("person_resolution_basis"),
                "person_source_path": None if person is None else derive_person_source_path(person),
                "trust_basis": derive_content_trust_basis(intelligence, person),
                "reviewed_truth_applied": _reviewed_truth_applied(intelligence) or _reviewed_truth_applied(person),
                "reviewed_override_count": _reviewed_override_count(intelligence, person),
                "internally_usable": intelligence.get("internally_usable"),
                "content_ready": intelligence.get("content_ready"),
                "spotlight_ready": intelligence.get("spotlight_ready"),
                "externally_publishable": intelligence.get("externally_publishable"),
                "profile_completeness_score": intelligence.get("profile_completeness_score"),
                "story_type": intelligence.get("story_type"),
                "message_pillar": intelligence.get("message_pillar"),
                "missing_content_assets": intelligence.get("missing_content_assets"),
            }
        )
    return _sort_by_score_and_label(rows, "full_name")


def report_internally_usable_organizations(
    content_bundle: dict[str, object],
    organizations: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return organizations trusted enough for internal planning use."""

    return [
        row
        for row in _organization_content_rows(content_bundle, organizations)
        if _truthy(row.get("internally_usable"))
    ]


def report_all_organization_content_rows(
    content_bundle: dict[str, object],
    organizations: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return all organization content rows with trust metadata attached."""

    return _organization_content_rows(content_bundle, organizations)


def report_internally_usable_people(
    content_bundle: dict[str, object],
    people_payloads: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return people trusted enough for internal planning use."""

    return [
        row
        for row in _person_content_rows(content_bundle, people_payloads)
        if _truthy(row.get("internally_usable"))
    ]


def report_all_person_content_rows(
    content_bundle: dict[str, object],
    people_payloads: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return all person content rows with trust metadata attached."""

    return _person_content_rows(content_bundle, people_payloads)


def report_content_ready_organizations(
    content_bundle: dict[str, object],
    organizations: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return organizations that are draftable for content workflows."""

    return [
        row
        for row in _organization_content_rows(content_bundle, organizations)
        if _truthy(row.get("content_ready"))
    ]


def report_content_ready_people(
    content_bundle: dict[str, object],
    people_payloads: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return people that are draftable for content workflows."""

    return [
        row
        for row in _person_content_rows(content_bundle, people_payloads)
        if _truthy(row.get("content_ready"))
    ]


def report_spotlight_ready_organizations(
    content_bundle: dict[str, object],
    organizations: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return organizations that are ready for spotlight-style content."""

    return [
        row
        for row in _organization_content_rows(content_bundle, organizations)
        if _truthy(row.get("spotlight_ready"))
    ]


def report_spotlight_ready_people(
    content_bundle: dict[str, object],
    people_payloads: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return people that are ready for spotlight-style content."""

    return [
        row
        for row in _person_content_rows(content_bundle, people_payloads)
        if _truthy(row.get("spotlight_ready"))
    ]


def report_externally_publishable_records(
    content_bundle: dict[str, object],
    organizations: Sequence[dict[str, object]],
    people_payloads: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return human-approved records that may be used publicly."""

    rows: list[dict[str, object]] = []
    for row in _organization_content_rows(content_bundle, organizations):
        if not _truthy(row.get("externally_publishable")):
            continue
        rows.append(
            {
                "record_type": "organization",
                "label": row.get("organization_name"),
                "entity_type": row.get("org_type"),
                "trust_basis": row.get("trust_basis"),
                "reviewed_override_count": row.get("reviewed_override_count"),
                "content_ready": row.get("content_ready"),
                "spotlight_ready": row.get("spotlight_ready"),
                "externally_publishable": row.get("externally_publishable"),
                "profile_completeness_score": row.get("profile_completeness_score"),
                "story_type": row.get("story_type"),
                "message_pillar": row.get("message_pillar"),
                "missing_content_assets": row.get("missing_content_assets"),
            }
        )
    for row in _person_content_rows(content_bundle, people_payloads):
        if not _truthy(row.get("externally_publishable")):
            continue
        rows.append(
            {
                "record_type": "person",
                "label": row.get("full_name"),
                "entity_type": row.get("person_type"),
                "trust_basis": row.get("trust_basis"),
                "reviewed_override_count": row.get("reviewed_override_count"),
                "content_ready": row.get("content_ready"),
                "spotlight_ready": row.get("spotlight_ready"),
                "externally_publishable": row.get("externally_publishable"),
                "profile_completeness_score": row.get("profile_completeness_score"),
                "story_type": row.get("story_type"),
                "message_pillar": row.get("message_pillar"),
                "missing_content_assets": row.get("missing_content_assets"),
            }
        )
    return _sort_by_score_and_label(rows, "label")


def report_missing_content_asset_counts(
    content_bundle: dict[str, object],
    organizations: Sequence[dict[str, object]] = (),
    people_payloads: Sequence[dict[str, object]] = (),
) -> list[dict[str, object]]:
    """Count missing content assets across content-eligible people and organizations."""

    counts: Counter[tuple[str, str, str, str]] = Counter()
    typed_rows: list[tuple[str, list[dict[str, object]]]] = []
    typed_rows.append(
        (
            "organization",
            _organization_content_rows(content_bundle, organizations)
            if organizations
            else [
                {
                    "trust_basis": derive_content_trust_basis(dict(item), None),
                    "internally_usable": dict(item).get("internally_usable"),
                    "content_ready": dict(item).get("content_ready"),
                    "spotlight_ready": dict(item).get("spotlight_ready"),
                    "externally_publishable": dict(item).get("externally_publishable"),
                    "missing_content_assets": dict(item).get("missing_content_assets"),
                }
                for item in content_bundle.get("organizations", [])
            ],
        )
    )
    typed_rows.append(
        (
            "person",
            _person_content_rows(content_bundle, people_payloads)
            if people_payloads
            else [
                {
                    "trust_basis": derive_content_trust_basis(dict(item), None),
                    "internally_usable": dict(item).get("internally_usable"),
                    "content_ready": dict(item).get("content_ready"),
                    "spotlight_ready": dict(item).get("spotlight_ready"),
                    "externally_publishable": dict(item).get("externally_publishable"),
                    "missing_content_assets": dict(item).get("missing_content_assets"),
                }
                for item in content_bundle.get("people", [])
            ],
        )
    )

    for record_type, rows in typed_rows:
        for row in rows:
            if not _truthy(row.get("internally_usable")) and not _truthy(row.get("content_ready")):
                continue
            for asset_name in _split_missing_assets(row.get("missing_content_assets")):
                counts[
                    (
                        record_type,
                        str(row.get("trust_basis") or "heuristic_only"),
                        derive_highest_readiness_level(row),
                        asset_name,
                    )
                ] += 1

    rows = [
        {
            "record_type": record_type,
            "trust_basis": trust_basis,
            "readiness_level": readiness_level,
            "asset_name": asset_name,
            "count": count,
        }
        for (record_type, trust_basis, readiness_level, asset_name), count in counts.items()
    ]
    return sorted(
        rows,
        key=lambda row: (
            -int(row["count"]),
            str(row["record_type"]),
            str(row["trust_basis"]),
            str(row["readiness_level"]),
            str(row["asset_name"]),
        ),
    )
