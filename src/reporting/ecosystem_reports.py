"""Lightweight reporting outputs for the normalized ecosystem CRM."""

from __future__ import annotations

import argparse
import csv
import io
import json
from collections import Counter
from typing import Any, Dict, Iterable, Optional, Sequence

from src.enrich.content_intelligence import build_content_intelligence_bundle
from src.enrich.ecosystem_segments import segment_active_mentors, segment_local_mentors, segment_non_local_mentors
from src.reporting.content_summary import (
    derive_review_state,
    derive_person_source_path,
    report_all_organization_content_rows,
    report_all_person_content_rows,
    report_externally_publishable_records,
    report_internally_usable_organizations as build_internally_usable_organizations_report,
    report_internally_usable_people as build_internally_usable_people_report,
    report_content_ready_organizations as build_content_ready_organizations_report,
    report_content_ready_people as build_content_ready_people_report,
    report_missing_content_asset_counts,
    report_spotlight_ready_organizations as build_spotlight_ready_organizations_report,
    report_spotlight_ready_people as build_spotlight_ready_people_report,
)


REPORT_SECTION_ORDER = [
    "active_organizations_by_type",
    "active_people_by_type",
    "active_people_by_source_path",
    "active_mentor_summary",
    "readiness_trust_summary",
    "structured_people",
    "semi_structured_auto_created_people",
    "mentor_derived_people",
    "review_needed_people_candidates",
    "organizations_by_cohort",
    "organizations_by_membership_tier",
    "internally_usable_organizations",
    "internally_usable_people",
    "content_ready_organizations",
    "content_ready_people",
    "spotlight_ready_organizations",
    "spotlight_ready_people",
    "externally_publishable_records",
    "missing_content_asset_counts",
    "review_burden_by_flag",
    "review_needed_records",
]


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


def _status(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _sorted_counter_rows(counter: Counter, field_name: str) -> list[dict[str, object]]:
    rows = [{field_name: key, "count": count} for key, count in counter.items()]
    return sorted(rows, key=lambda row: (-int(row["count"]), str(row[field_name])))


def _reviewed_override_count(record: dict[str, object]) -> int:
    value = record.get("reviewed_override_ids", [])
    if not isinstance(value, list):
        return 0
    return len([item for item in value if str(item).strip()])


def report_active_organizations_by_type(
    organizations: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Count active organizations by organization type."""

    counts = Counter(
        str(org.get("org_type") or "other")
        for org in organizations
        if _truthy(org.get("active_flag"))
    )
    return _sorted_counter_rows(counts, "org_type")


def report_active_people_by_type(
    people_payloads: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Count active people by person type."""

    counts = Counter(
        str(person.get("person_type") or "other")
        for person in people_payloads
        if _truthy(person.get("active_flag"))
    )
    return _sorted_counter_rows(counts, "person_type")


def report_active_people_by_source_path(
    people_payloads: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Count active people by the path that created them."""

    grouped: Dict[str, dict[str, object]] = {}
    for person in people_payloads:
        if not _truthy(person.get("active_flag")):
            continue
        source_path = derive_person_source_path(person)
        bucket = grouped.setdefault(
            source_path,
            {
                "person_source_path": source_path,
                "count": 0,
                "reviewed_truth_backed_count": 0,
                "source_derived_count": 0,
            },
        )
        bucket["count"] = int(bucket["count"]) + 1
        if derive_review_state(person) == "reviewed_truth_backed":
            bucket["reviewed_truth_backed_count"] = int(bucket["reviewed_truth_backed_count"]) + 1
        else:
            bucket["source_derived_count"] = int(bucket["source_derived_count"]) + 1

    return sorted(grouped.values(), key=lambda row: (-int(row["count"]), str(row["person_source_path"])))


def _people_provenance_rows(
    people_payloads: Sequence[dict[str, object]],
    *,
    source_path: str,
) -> list[dict[str, object]]:
    rows = [
        {
            "full_name": person.get("full_name"),
            "person_type": person.get("person_type"),
            "person_resolution_basis": person.get("person_resolution_basis"),
            "person_source_path": derive_person_source_path(person),
            "review_state": derive_review_state(person),
            "reviewed_override_count": _reviewed_override_count(person),
            "active_flag": person.get("active_flag"),
            "email": person.get("email"),
            "source_record_id": person.get("source_record_id"),
            "source_system": person.get("source_system"),
        }
        for person in people_payloads
        if derive_person_source_path(person) == source_path
    ]
    return sorted(rows, key=lambda row: (str(row.get("full_name") or ""), str(row.get("source_record_id") or "")))


def report_structured_people(
    people_payloads: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return people created from structured member-side fields."""

    return _people_provenance_rows(people_payloads, source_path="structured_member_fields")


def report_semi_structured_auto_created_people(
    people_payloads: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return people created by the conservative dual-signal member-side path."""

    return _people_provenance_rows(people_payloads, source_path="semi_structured_member_side")


def report_mentor_derived_people(
    people_payloads: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return people created from the mentor source path."""

    return _people_provenance_rows(people_payloads, source_path="mentor_structured")


def report_active_mentor_summary(
    people_payloads: Sequence[dict[str, object]],
    mentor_profiles: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return active mentor counts for overall, local, and non-local groups."""

    return [
        {"metric": "active_mentors", "count": len(segment_active_mentors(people_payloads, mentor_profiles))},
        {"metric": "local_mentors", "count": len(segment_local_mentors(people_payloads, mentor_profiles))},
        {"metric": "non_local_mentors", "count": len(segment_non_local_mentors(people_payloads, mentor_profiles))},
    ]


TRUST_BASIS_ORDER = {
    "human_approved": 0,
    "reviewed_truth_backed": 1,
    "heuristic_only": 2,
}


def report_readiness_trust_summary(
    content_bundle: dict[str, object],
    organizations: Sequence[dict[str, object]],
    people_payloads: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Summarize readiness counts by record type and trust basis."""

    rows: list[dict[str, object]] = []
    for record_type, records in (
        ("organization", report_all_organization_content_rows(content_bundle, organizations)),
        ("person", report_all_person_content_rows(content_bundle, people_payloads)),
    ):
        grouped: Dict[str, dict[str, object]] = {}
        for record in records:
            trust_basis = str(record.get("trust_basis") or "heuristic_only")
            bucket = grouped.setdefault(
                trust_basis,
                {
                    "record_type": record_type,
                    "trust_basis": trust_basis,
                    "row_count": 0,
                    "internally_usable_count": 0,
                    "content_ready_count": 0,
                    "spotlight_ready_count": 0,
                    "externally_publishable_count": 0,
                },
            )
            bucket["row_count"] = int(bucket["row_count"]) + 1
            if _truthy(record.get("internally_usable")):
                bucket["internally_usable_count"] = int(bucket["internally_usable_count"]) + 1
            if _truthy(record.get("content_ready")):
                bucket["content_ready_count"] = int(bucket["content_ready_count"]) + 1
            if _truthy(record.get("spotlight_ready")):
                bucket["spotlight_ready_count"] = int(bucket["spotlight_ready_count"]) + 1
            if _truthy(record.get("externally_publishable")):
                bucket["externally_publishable_count"] = int(bucket["externally_publishable_count"]) + 1
        rows.extend(grouped.values())

    return sorted(
        rows,
        key=lambda row: (
            str(row["record_type"]),
            TRUST_BASIS_ORDER.get(str(row["trust_basis"]), 99),
        ),
    )


def report_organizations_by_cohort(
    organizations: Sequence[dict[str, object]],
    participations: Sequence[dict[str, object]],
    cohorts: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Group organizations by cohort."""

    organizations_by_key = {
        _record_key(organization): organization
        for organization in organizations
        if _record_key(organization) is not None
    }
    cohorts_by_key = {
        _record_key(cohort): cohort
        for cohort in cohorts
        if _record_key(cohort) is not None
    }

    grouped: Dict[str, dict[str, Any]] = {}
    for participation in participations:
        organization = organizations_by_key.get(participation.get("organization_id"))
        cohort = cohorts_by_key.get(participation.get("cohort_id"))
        if organization is None or cohort is None:
            continue

        cohort_name = str(cohort.get("cohort_name") or "Unknown Cohort")
        bucket = grouped.setdefault(
            cohort_name,
            {
                "cohort_name": cohort_name,
                "_organization_names": set(),
                "_active_names": set(),
                "_alumni_names": set(),
            },
        )
        organization_name = str(organization.get("name") or "Unknown Organization")
        bucket["_organization_names"].add(organization_name)

        status = _status(participation.get("participation_status"))
        if status == "active":
            bucket["_active_names"].add(organization_name)
        elif status == "alumni":
            bucket["_alumni_names"].add(organization_name)

    rows: list[dict[str, object]] = []
    for cohort_name, bucket in grouped.items():
        organization_names = sorted(bucket["_organization_names"])
        rows.append(
            {
                "cohort_name": cohort_name,
                "organization_count": len(bucket["_organization_names"]),
                "active_organization_count": len(bucket["_active_names"]),
                "alumni_organization_count": len(bucket["_alumni_names"]),
                "organization_names": "; ".join(organization_names),
            }
        )

    return sorted(rows, key=lambda row: str(row["cohort_name"]))


def report_content_ready_organizations(
    content_bundle: dict[str, object],
    organizations: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return organizations with content-ready profiles."""

    return build_content_ready_organizations_report(content_bundle, organizations)


def report_content_ready_people(
    content_bundle: dict[str, object],
    people_payloads: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return people with content-ready profiles."""

    return build_content_ready_people_report(content_bundle, people_payloads)


def report_internally_usable_organizations(
    content_bundle: dict[str, object],
    organizations: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return organizations usable for internal planning."""

    return build_internally_usable_organizations_report(content_bundle, organizations)


def report_internally_usable_people(
    content_bundle: dict[str, object],
    people_payloads: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return people usable for internal planning."""

    return build_internally_usable_people_report(content_bundle, people_payloads)


def report_spotlight_ready_organizations(
    content_bundle: dict[str, object],
    organizations: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return organizations that are ready for spotlight-style content."""

    return build_spotlight_ready_organizations_report(content_bundle, organizations)


def report_spotlight_ready_people(
    content_bundle: dict[str, object],
    people_payloads: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return people that are ready for spotlight-style content."""

    return build_spotlight_ready_people_report(content_bundle, people_payloads)


def report_externally_publishable(
    content_bundle: dict[str, object],
    organizations: Sequence[dict[str, object]],
    people_payloads: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return records explicitly approved for public-facing use."""

    return report_externally_publishable_records(content_bundle, organizations, people_payloads)


def report_review_needed_records(
    review_rows: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return rows already marked for human review."""

    rows = [
        {
            "source_table": row.get("source_table"),
            "source_record_id": row.get("source_record_id"),
            "flag_code": row.get("flag_code"),
            "flag_type": row.get("flag_type"),
            "severity": row.get("severity"),
            "record_label": row.get("record_label"),
            "source_field": row.get("source_field"),
            "note": row.get("note"),
        }
        for row in review_rows
    ]
    return sorted(rows, key=lambda row: (str(row["severity"]), str(row["source_table"]), str(row["source_record_id"])))


PERSON_CANDIDATE_REVIEW_FLAGS = {
    "review_no_person_found",
    "review_person_missing_email",
    "review_personnel_parse",
    "review_member_side_person_multiple_candidates",
    "review_member_side_person_name_incomplete",
    "review_member_side_person_generic_email",
    "review_member_side_person_context_ambiguous",
    "review_grouped_record_detected",
    "review_duplicate_suspected",
}


def report_review_needed_people_candidates(
    review_rows: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Return only review rows that matter to person creation or person trust."""

    rows = [
        {
            "source_table": row.get("source_table"),
            "source_record_id": row.get("source_record_id"),
            "flag_code": row.get("flag_code"),
            "severity": row.get("severity"),
            "record_label": row.get("record_label"),
            "source_field": row.get("source_field"),
            "note": row.get("note"),
        }
        for row in review_rows
        if str(row.get("flag_code") or "") in PERSON_CANDIDATE_REVIEW_FLAGS
    ]
    return sorted(rows, key=lambda row: (str(row["severity"]), str(row["source_table"]), str(row["source_record_id"])))


def report_review_burden_by_flag(
    review_rows: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Summarize review burden by flag code and severity."""

    grouped: Dict[tuple[str, str], dict[str, object]] = {}
    for row in review_rows:
        flag_code = str(row.get("flag_code") or "")
        severity = str(row.get("severity") or "")
        key = (flag_code, severity)
        bucket = grouped.setdefault(
            key,
            {
                "flag_code": flag_code,
                "flag_type": row.get("flag_type"),
                "severity": severity,
                "review_scope": "people_candidate" if flag_code in PERSON_CANDIDATE_REVIEW_FLAGS else "general",
                "count": 0,
                "_source_tables": set(),
            },
        )
        bucket["count"] = int(bucket["count"]) + 1
        source_table = row.get("source_table")
        if source_table:
            bucket["_source_tables"].add(str(source_table))

    rows: list[dict[str, object]] = []
    for bucket in grouped.values():
        rows.append(
            {
                "flag_code": bucket["flag_code"],
                "flag_type": bucket["flag_type"],
                "severity": bucket["severity"],
                "review_scope": bucket["review_scope"],
                "count": bucket["count"],
                "source_tables": ", ".join(sorted(bucket["_source_tables"])),
            }
        )
    return sorted(rows, key=lambda row: (-int(row["count"]), str(row["severity"]), str(row["flag_code"])))


def report_organizations_by_membership_tier(
    organizations: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Count active organizations by membership tier when present."""

    counts = Counter(
        str(organization.get("membership_tier"))
        for organization in organizations
        if _truthy(organization.get("active_flag")) and organization.get("membership_tier")
    )
    return _sorted_counter_rows(counts, "membership_tier")


def build_reporting_snapshot(
    *,
    organizations: Sequence[dict[str, object]],
    people_payloads: Sequence[dict[str, object]],
    mentor_profiles: Sequence[dict[str, object]],
    affiliations: Sequence[dict[str, object]] = (),
    participations: Sequence[dict[str, object]] = (),
    cohorts: Sequence[dict[str, object]] = (),
    review_rows: Sequence[dict[str, object]] = (),
    content_bundle: Optional[dict[str, object]] = None,
) -> dict[str, object]:
    """Build a reporting snapshot from normalized and enriched records."""

    computed_content_bundle = content_bundle or build_content_intelligence_bundle(
        organizations=organizations,
        people_payloads=people_payloads,
        affiliations=affiliations,
        participations=participations,
        cohorts=cohorts,
    )
    combined_review_rows = list(review_rows) + list(computed_content_bundle.get("review_rows", []))

    return {
        "active_organizations_by_type": report_active_organizations_by_type(organizations),
        "active_people_by_type": report_active_people_by_type(people_payloads),
        "active_people_by_source_path": report_active_people_by_source_path(people_payloads),
        "active_mentor_summary": report_active_mentor_summary(people_payloads, mentor_profiles),
        "readiness_trust_summary": report_readiness_trust_summary(
            computed_content_bundle,
            organizations,
            people_payloads,
        ),
        "structured_people": report_structured_people(people_payloads),
        "semi_structured_auto_created_people": report_semi_structured_auto_created_people(people_payloads),
        "mentor_derived_people": report_mentor_derived_people(people_payloads),
        "review_needed_people_candidates": report_review_needed_people_candidates(combined_review_rows),
        "organizations_by_cohort": report_organizations_by_cohort(organizations, participations, cohorts),
        "organizations_by_membership_tier": report_organizations_by_membership_tier(organizations),
        "internally_usable_organizations": report_internally_usable_organizations(computed_content_bundle, organizations),
        "internally_usable_people": report_internally_usable_people(computed_content_bundle, people_payloads),
        "content_ready_organizations": report_content_ready_organizations(computed_content_bundle, organizations),
        "content_ready_people": report_content_ready_people(computed_content_bundle, people_payloads),
        "spotlight_ready_organizations": report_spotlight_ready_organizations(computed_content_bundle, organizations),
        "spotlight_ready_people": report_spotlight_ready_people(computed_content_bundle, people_payloads),
        "externally_publishable_records": report_externally_publishable(
            computed_content_bundle,
            organizations,
            people_payloads,
        ),
        "missing_content_asset_counts": report_missing_content_asset_counts(
            computed_content_bundle,
            organizations,
            people_payloads,
        ),
        "review_burden_by_flag": report_review_burden_by_flag(combined_review_rows),
        "review_needed_records": report_review_needed_records(combined_review_rows),
    }


def _markdown_table(rows: Sequence[dict[str, object]]) -> str:
    if not rows:
        return "_No rows._"
    headers = list(rows[0].keys())
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        values = [str(row.get(header, "")) for header in headers]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


SECTION_TITLES = {
    "active_organizations_by_type": "Active Organizations By Type",
    "active_people_by_type": "Active People By Type",
    "active_people_by_source_path": "Active People By Source Path",
    "active_mentor_summary": "Active Mentor Summary",
    "readiness_trust_summary": "Readiness Trust Summary",
    "structured_people": "Structured People",
    "semi_structured_auto_created_people": "Semi-Structured Auto-Created People",
    "mentor_derived_people": "Mentor-Derived People",
    "review_needed_people_candidates": "Review-Needed People Candidates",
    "organizations_by_cohort": "Organizations By Cohort",
    "organizations_by_membership_tier": "Organizations By Membership Tier",
    "internally_usable_organizations": "Internally Usable Organizations",
    "internally_usable_people": "Internally Usable People",
    "content_ready_organizations": "Organizations With Content-Ready Profiles",
    "content_ready_people": "People With Content-Ready Profiles",
    "spotlight_ready_organizations": "Spotlight-Ready Organizations",
    "spotlight_ready_people": "Spotlight-Ready People",
    "externally_publishable_records": "Externally Publishable Records",
    "missing_content_asset_counts": "Missing Content Asset Counts",
    "review_burden_by_flag": "Review Burden By Flag",
    "review_needed_records": "Records Requiring Review",
}


def render_markdown_report(snapshot: dict[str, object]) -> str:
    """Render the reporting snapshot as markdown."""

    sections: list[str] = ["# Ecosystem Report"]
    for section_name in REPORT_SECTION_ORDER:
        rows = snapshot.get(section_name, [])
        sections.append("")
        sections.append("## " + SECTION_TITLES[section_name])
        sections.append("")
        sections.append(_markdown_table(rows if isinstance(rows, list) else []))
    return "\n".join(sections).strip() + "\n"


def render_csv_section(snapshot: dict[str, object], section_name: str) -> str:
    """Render one report section as CSV."""

    rows = snapshot.get(section_name)
    if not isinstance(rows, list):
        return ""
    if not rows:
        return ""

    buffer = io.StringIO()
    fieldnames = list(rows[0].keys())
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()


def load_reporting_input(file_path: str) -> dict[str, object]:
    """Load normalized reporting input from a JSON file."""

    with open(file_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def build_snapshot_from_input(payload: dict[str, object]) -> dict[str, object]:
    """Build a reporting snapshot from a JSON-compatible input bundle."""

    return build_reporting_snapshot(
        organizations=payload.get("organizations", []),  # type: ignore[arg-type]
        people_payloads=payload.get("people", []),  # type: ignore[arg-type]
        mentor_profiles=payload.get("mentor_profiles", []),  # type: ignore[arg-type]
        affiliations=payload.get("affiliations", []),  # type: ignore[arg-type]
        participations=payload.get("participations", []),  # type: ignore[arg-type]
        cohorts=payload.get("cohorts", []),  # type: ignore[arg-type]
        review_rows=payload.get("review_rows", []),  # type: ignore[arg-type]
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run reporting from the command line."""

    parser = argparse.ArgumentParser(description="Build first-pass OM ecosystem reports from JSON input.")
    parser.add_argument("--input", required=True, help="Path to a JSON file containing normalized reporting input.")
    parser.add_argument(
        "--format",
        choices=("markdown", "json", "csv"),
        default="markdown",
        help="Output format.",
    )
    parser.add_argument(
        "--section",
        choices=REPORT_SECTION_ORDER,
        help="Required for CSV output. Optional for JSON or markdown.",
    )
    args = parser.parse_args(argv)

    payload = load_reporting_input(args.input)
    snapshot = build_snapshot_from_input(payload)

    if args.format == "markdown":
        print(render_markdown_report(snapshot), end="")
        return 0
    if args.format == "json":
        print(json.dumps(snapshot if args.section is None else snapshot.get(args.section, []), indent=2))
        return 0
    if args.section is None:
        raise SystemExit("--section is required when --format csv is used.")
    print(render_csv_section(snapshot, args.section), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
