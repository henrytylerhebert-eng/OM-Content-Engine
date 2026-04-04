"""Simple local demo pipeline for the OM sample exports."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Sequence

from src.enrich.content_intelligence import build_content_intelligence_bundle
from src.ingest.airtable_import import RawImportRecord, load_airtable_csv_export
from src.review.reviewed_truth import (
    DEFAULT_OVERRIDES_PATH,
    apply_content_bundle_overrides,
    apply_normalized_overrides,
    apply_review_row_overrides,
    build_reviewed_truth_artifact,
    load_override_document,
)
from src.reporting.content_candidates import build_content_candidates_from_bundle, write_content_candidate_outputs
from src.reporting.content_briefs import build_content_briefs_from_bundle, write_content_brief_outputs
from src.reporting.editorial_assignments import build_assignments as build_editorial_assignments
from src.reporting.editorial_assignments import write_assignment_outputs
from src.reporting.editorial_plan import build_plan as build_editorial_plan
from src.reporting.editorial_plan import write_outputs as write_editorial_plan_outputs
from src.reporting.ecosystem_reports import build_reporting_snapshot, render_markdown_report
from src.reporting.ecosystem_summary import build_ecosystem_summary
from src.reporting.weekly_export_summary import write_weekly_export_summary
from src.transform.normalize_affiliations import normalize_affiliations_from_row
from src.transform.normalize_organizations import normalize_organization_row
from src.transform.normalize_participation import normalize_explicit_cohort_row, normalize_participation_row
from src.transform.normalize_people import PersonDraft, normalize_people_from_row
from src.transform.review_flags import ReviewFlag, build_review_flag, build_review_queue_rows


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ACTIVE_MEMBERS_PATH = REPO_ROOT / "tests" / "fixtures" / "active_members.csv"
DEFAULT_MENTORS_PATH = REPO_ROOT / "tests" / "fixtures" / "mentors.csv"
DEFAULT_COHORTS_PATH = REPO_ROOT / "tests" / "fixtures" / "cohorts.csv"
DEFAULT_OVERRIDES_FILE = DEFAULT_OVERRIDES_PATH
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "processed" / "demo"

SNAPSHOT_ARTIFACT_DESCRIPTIONS = {
    "normalized_bundle.json": "Source-derived normalized entities before reviewed truth is applied.",
    "reviewed_truth.json": "Reviewed copies plus override application metadata.",
    "review_flags.json": "Current review queue after normalization, content checks, and review-row overrides.",
    "content_intelligence.json": "Readiness ladder, content-use signals, and content review rows.",
    "reporting_snapshot.json": "Machine-friendly reporting sections for planning and inspection.",
    "ecosystem_summary.json": "Compact run summary with high-level counts.",
    "ecosystem_report.md": "Readable markdown summary for quick internal review.",
    "content_candidates.json": "Compact internal-only candidate list for content planning and brief generation.",
    "content_candidates.csv": "Flat CSV version of the internal content candidate list.",
    "content_briefs.json": "Compact internal briefing pack built from the trust-aware candidate export.",
    "content_briefs.md": "Readable markdown briefing pack for weekly planning and drafting review.",
    "editorial_plan.json": "Weekly planning buckets built from internal briefs: use now, needs review, and hold.",
    "editorial_plan.md": "Readable markdown planning pack for weekly editorial meetings.",
    "editorial_assignments.json": "Execution tracker for editorial owners, cycles, and status updates.",
    "editorial_assignments.md": "Readable markdown assignment tracker for weekly execution review.",
    "editorial_assignments.csv": "Flat CSV version of the editorial assignment tracker.",
    "weekly_export_summary.md": "Compact weekly roll-up of plan counts, assignment status, and top unresolved blockers.",
    "snapshot_manifest.json": "Concise manifest describing the run inputs and produced artifacts.",
}


def _slug(value: object) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower())
    return text.strip("_") or "record"


def _json_default(value: object) -> object:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    raise TypeError("Object of type %s is not JSON serializable" % type(value).__name__)


def _utc_timestamp() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _dedupe_key_for_person(draft: PersonDraft) -> str:
    payload = draft.payload
    return str(payload.get("email") or payload.get("full_name") or payload.get("source_record_id") or "person")


def _upsert_record(
    collection: dict[str, dict[str, object]],
    record: dict[str, object],
    *,
    prefer_incoming_keys: Sequence[str] = (),
) -> dict[str, object]:
    """Merge records conservatively while preserving provenance."""

    record_id = str(record["id"])
    existing = collection.get(record_id)
    if existing is None:
        collection[record_id] = dict(record)
        return collection[record_id]

    existing_provenance = list(existing.get("source_provenance", []))
    for entry in record.get("source_provenance", []):
        if entry not in existing_provenance:
            existing_provenance.append(entry)
    if existing_provenance:
        existing["source_provenance"] = existing_provenance

    for key, value in record.items():
        if key in {"id", "source_provenance"}:
            continue
        if key in prefer_incoming_keys and value not in (None, "", []):
            existing[key] = value
            continue
        if existing.get(key) in (None, "", []):
            existing[key] = value
        elif isinstance(existing.get(key), bool) and isinstance(value, bool):
            existing[key] = bool(existing[key] or value)
    return existing


def _review_rows_for_flags(
    *,
    source_table: str,
    source_record_id: Optional[str],
    flag_codes: Sequence[object],
    record_label: Optional[str],
) -> list[dict[str, Optional[str]]]:
    if not flag_codes:
        return []
    return build_review_queue_rows(
        source_table=source_table,
        source_record_id=source_record_id,
        flag_codes=flag_codes,
        record_label=record_label,
    )


def _has_participation_context(row: dict[str, str]) -> bool:
    return any(
        bool(row.get(key))
        for key in (
            "Cohort Name",
            "Cohort",
            "Builder Cohort",
            "Program Name",
            "Participation Status",
        )
    )


def _source_record_id(raw_record: RawImportRecord) -> str:
    return str(raw_record.source_record_id or raw_record.row_hash)


def _source_provenance_entry(raw_record: RawImportRecord, *, origin: str) -> dict[str, str]:
    return {
        "source_table": raw_record.source_table,
        "source_record_id": _source_record_id(raw_record),
        "source_system": raw_record.source_system,
        "file_path": raw_record.file_path,
        "row_hash": raw_record.row_hash,
        "origin": origin,
    }


def _person_id_from_draft(draft: PersonDraft) -> str:
    return "person:%s" % _slug(_dedupe_key_for_person(draft))


def _organization_id(payload: dict[str, object]) -> str:
    return "org:%s" % _slug(payload.get("source_record_id") or payload.get("name"))


def _program_id(program_name: object) -> str:
    return "program:%s" % _slug(program_name)


def _canonical_cohort_name(cohort_name: object) -> str:
    text = " ".join(str(cohort_name or "").strip().split())
    lowered = text.lower()
    for prefix in ("builder ", "accelerator ", "mentor "):
        if lowered.startswith(prefix):
            return text[len(prefix) :].strip()
    return text


def _cohort_id(cohort_name: object) -> str:
    return "cohort:%s" % _slug(_canonical_cohort_name(cohort_name))


def _name_key(value: object) -> str:
    return _slug(value)


def _email_key(value: object) -> str:
    return str(value or "").strip().lower()


def _organization_lookup_keys(row: dict[str, str]) -> list[str]:
    keys: list[str] = []
    for value in (row.get("Company Name"), row.get("Organization Name"), row.get("Link to Application")):
        cleaned = str(value or "").strip()
        if cleaned:
            keys.append(_name_key(cleaned))
    return keys


def _person_lookup_keys(row: dict[str, str]) -> list[str]:
    keys: list[str] = []
    for field in ("Primary Email (from Link to Application)", "Your Email (from Participants)"):
        value = str(row.get(field) or "").replace(";", ",")
        for part in value.split(","):
            cleaned = _email_key(part)
            if cleaned:
                keys.append(cleaned)
    return keys


def _build_unresolved_link_flag(raw_record: RawImportRecord, row: dict[str, str]) -> ReviewFlag:
    return build_review_flag(
        "review_participation_link_unresolved",
        source_table=raw_record.source_table,
        row=row,
        source_record_id=_source_record_id(raw_record),
        source_system=raw_record.source_system,
        source_field="Company Name",
        raw_value=row.get("Company Name") or row.get("Link to Application"),
    )


def build_bundle_from_raw_records(
    *,
    raw_active_members: Sequence[RawImportRecord],
    raw_mentors: Sequence[RawImportRecord],
    raw_cohorts: Sequence[RawImportRecord],
    overrides_path: Optional[Path] = DEFAULT_OVERRIDES_FILE,
    raw_sources: Optional[dict[str, dict[str, object]]] = None,
) -> dict[str, object]:
    """Run the core pipeline against already-landed raw import records."""

    organizations_by_id: dict[str, dict[str, object]] = {}
    people_by_id: dict[str, dict[str, object]] = {}
    mentor_profiles_by_id: dict[str, dict[str, object]] = {}
    programs_by_id: dict[str, dict[str, object]] = {}
    cohorts_by_id: dict[str, dict[str, object]] = {}
    affiliation_ids: set[str] = set()
    affiliations: list[dict[str, object]] = []
    participation_ids: set[str] = set()
    participations_by_id: dict[str, dict[str, object]] = {}
    review_rows: list[dict[str, Optional[str]]] = []

    for raw_record in raw_active_members:
        row = dict(raw_record.raw)
        organization = None
        raw_source_record_id = _source_record_id(raw_record)

        organization_result = normalize_organization_row(
            row,
            source_table=raw_record.source_table,
            source_system=raw_record.source_system,
        )
        if organization_result.organization is not None:
            organization = dict(organization_result.organization)
            organization["id"] = _organization_id(organization)
            organization["source_table"] = raw_record.source_table
            organization["source_record_id"] = organization.get("source_record_id") or raw_source_record_id
            organization["source_provenance"] = [_source_provenance_entry(raw_record, origin="direct_organization")]
            organization = _upsert_record(organizations_by_id, organization)

        record_label = None if organization is None else str(organization.get("name") or "")
        review_rows.extend(
            _review_rows_for_flags(
                source_table=raw_record.source_table,
                source_record_id=raw_source_record_id,
                flag_codes=organization_result.review_flags,
                record_label=record_label,
            )
        )

        people_result = normalize_people_from_row(
            row,
            source_table=raw_record.source_table,
            source_system=raw_record.source_system,
        )
        person_ids: list[str] = []
        for draft in people_result.people:
            person_payload = dict(draft.payload)
            person_payload["id"] = _person_id_from_draft(draft)
            person_payload["source_table"] = raw_record.source_table
            person_payload["source_record_id"] = person_payload.get("source_record_id") or raw_source_record_id
            person_payload["source_provenance"] = [_source_provenance_entry(raw_record, origin="direct_person")]
            stored_person = _upsert_record(people_by_id, person_payload)
            person_ids.append(str(stored_person["id"]))

        review_rows.extend(
            _review_rows_for_flags(
                source_table=raw_record.source_table,
                source_record_id=raw_source_record_id,
                flag_codes=people_result.review_flags,
                record_label=record_label or row.get("Founder Name") or row.get("Primary Contact Name"),
            )
        )

        affiliation_result = normalize_affiliations_from_row(
            row,
            source_table=raw_record.source_table,
            people=people_result.people,
            organization=organization,
            source_system=raw_record.source_system,
        )
        if organization is not None:
            for index, (person_id, affiliation) in enumerate(zip(person_ids, affiliation_result.affiliations), start=1):
                linked = dict(affiliation)
                linked["id"] = "%s:%s:%s" % (organization["id"], person_id, index)
                linked["person_id"] = person_id
                linked["organization_id"] = organization["id"]
                linked["source_table"] = raw_record.source_table
                linked["source_record_id"] = linked.get("source_record_id") or raw_source_record_id
                linked["source_provenance"] = [_source_provenance_entry(raw_record, origin="inferred_affiliation")]
                if str(linked["id"]) not in affiliation_ids:
                    affiliation_ids.add(str(linked["id"]))
                    affiliations.append(linked)

        review_rows.extend(
            _review_rows_for_flags(
                source_table=raw_record.source_table,
                source_record_id=raw_source_record_id,
                flag_codes=affiliation_result.review_flags,
                record_label=record_label,
            )
        )

        if not _has_participation_context(row):
            continue

        participation_result = normalize_participation_row(
            row,
            source_table=raw_record.source_table,
            source_system=raw_record.source_system,
        )
        if participation_result.program is not None:
            program = dict(participation_result.program)
            program["id"] = _program_id(program.get("program_name"))
            program["source_table"] = raw_record.source_table
            program["source_record_id"] = program.get("source_record_id") or raw_source_record_id
            program["source_provenance"] = [_source_provenance_entry(raw_record, origin="inferred_program")]
            _upsert_record(programs_by_id, program)

        if participation_result.cohort is not None:
            cohort = dict(participation_result.cohort)
            cohort["id"] = _cohort_id(cohort.get("cohort_name"))
            cohort["program_id"] = None if participation_result.program is None else _program_id(
                participation_result.program.get("program_name")
            )
            cohort["source_table"] = raw_record.source_table
            cohort["source_record_id"] = cohort.get("source_record_id") or raw_source_record_id
            cohort["source_provenance"] = [_source_provenance_entry(raw_record, origin="inferred_cohort")]
            _upsert_record(cohorts_by_id, cohort)

        if participation_result.participation is not None and organization is not None and participation_result.cohort is not None:
            participation = dict(participation_result.participation)
            participation["id"] = "participation:%s:%s" % (
                organization["id"],
                _cohort_id(participation_result.cohort.get("cohort_name")),
            )
            participation["organization_id"] = organization["id"]
            participation["cohort_id"] = _cohort_id(participation_result.cohort.get("cohort_name"))
            participation["source_table"] = raw_record.source_table
            participation["source_record_id"] = participation.get("source_record_id") or raw_source_record_id
            participation["participation_origin"] = "inferred_member_row"
            participation["source_provenance"] = [_source_provenance_entry(raw_record, origin="inferred_member_row")]
            if str(participation["id"]) not in participation_ids:
                participation_ids.add(str(participation["id"]))
                participations_by_id[str(participation["id"])] = participation

        review_rows.extend(
            _review_rows_for_flags(
                source_table=raw_record.source_table,
                source_record_id=raw_source_record_id,
                flag_codes=participation_result.review_flags,
                record_label=row.get("Builder Cohort") or row.get("Cohort Name") or record_label,
            )
        )

    for raw_record in raw_mentors:
        row = dict(raw_record.raw)
        raw_source_record_id = _source_record_id(raw_record)
        people_result = normalize_people_from_row(
            row,
            source_table=raw_record.source_table,
            source_system=raw_record.source_system,
        )

        mentor_person_id = None
        for draft in people_result.people:
            person_payload = dict(draft.payload)
            person_payload["id"] = _person_id_from_draft(draft)
            person_payload["source_table"] = raw_record.source_table
            person_payload["source_record_id"] = person_payload.get("source_record_id") or raw_source_record_id
            person_payload["source_provenance"] = [_source_provenance_entry(raw_record, origin="direct_person")]
            stored_person = _upsert_record(people_by_id, person_payload)
            mentor_person_id = str(stored_person["id"])

        review_rows.extend(
            _review_rows_for_flags(
                source_table=raw_record.source_table,
                source_record_id=raw_source_record_id,
                flag_codes=people_result.review_flags,
                record_label=row.get("Full Name") or row.get("Mentor Name") or row.get("Name"),
            )
        )

        if people_result.mentor_profile is None or mentor_person_id is None:
            continue

        mentor_profile = dict(people_result.mentor_profile)
        mentor_profile["id"] = "mentor_profile:%s" % mentor_person_id
        mentor_profile["person_id"] = mentor_person_id
        mentor_profile["source_table"] = raw_record.source_table
        mentor_profile["source_record_id"] = mentor_profile.get("source_record_id") or raw_source_record_id
        mentor_profile["source_provenance"] = [_source_provenance_entry(raw_record, origin="direct_mentor_profile")]
        _upsert_record(mentor_profiles_by_id, mentor_profile)

    organizations_by_name = {
        _name_key(organization.get("name")): str(organization["id"])
        for organization in organizations_by_id.values()
        if organization.get("name")
    }
    people_by_email: dict[str, list[str]] = {}
    for person in people_by_id.values():
        email_key = _email_key(person.get("email"))
        if email_key:
            people_by_email.setdefault(email_key, []).append(str(person["id"]))

    for raw_record in raw_cohorts:
        row = dict(raw_record.raw)
        raw_source_record_id = _source_record_id(raw_record)
        batch = normalize_explicit_cohort_row(
            row,
            source_table=raw_record.source_table,
            source_system=raw_record.source_system,
        )

        for program_payload in batch.programs:
            program = dict(program_payload)
            program["id"] = _program_id(program.get("program_name"))
            program["source_table"] = raw_record.source_table
            program["source_record_id"] = program.get("source_record_id") or raw_source_record_id
            program["source_provenance"] = [_source_provenance_entry(raw_record, origin="explicit_program")]
            _upsert_record(programs_by_id, program, prefer_incoming_keys=("source_table", "source_record_id"))

        for cohort_payload in batch.cohorts:
            cohort = dict(cohort_payload)
            cohort["id"] = _cohort_id(cohort.get("cohort_name"))
            cohort["program_id"] = None if not batch.programs else _program_id(batch.programs[0].get("program_name"))
            cohort["source_table"] = raw_record.source_table
            cohort["source_record_id"] = cohort.get("source_record_id") or raw_source_record_id
            cohort["source_provenance"] = [_source_provenance_entry(raw_record, origin="explicit_cohort")]
            _upsert_record(
                cohorts_by_id,
                cohort,
                prefer_incoming_keys=("source_table", "source_record_id", "start_date", "end_date", "active_flag"),
            )

        resolved_organization_id = next(
            (organizations_by_name[key] for key in _organization_lookup_keys(row) if key in organizations_by_name),
            None,
        )
        person_candidates = {
            person_id
            for key in _person_lookup_keys(row)
            for person_id in people_by_email.get(key, [])
        }
        resolved_person_id = next(iter(person_candidates)) if len(person_candidates) == 1 else None

        if resolved_organization_id is None and resolved_person_id is None:
            review_rows.extend(
                _review_rows_for_flags(
                    source_table=raw_record.source_table,
                    source_record_id=raw_source_record_id,
                    flag_codes=[_build_unresolved_link_flag(raw_record, row)],
                    record_label=row.get("Company Name") or row.get("Link to Application"),
                )
            )

        for participation_payload in batch.participations:
            cohort_name = participation_payload.get("cohort_name")
            cohort_id = _cohort_id(cohort_name)
            participation = dict(participation_payload)
            participation["id"] = "participation:%s:%s" % (
                resolved_organization_id or resolved_person_id or _slug(raw_source_record_id),
                cohort_id,
            )
            participation["organization_id"] = resolved_organization_id
            participation["person_id"] = resolved_person_id
            participation["cohort_id"] = cohort_id
            participation["source_table"] = raw_record.source_table
            participation["source_record_id"] = participation.get("source_record_id") or raw_source_record_id
            participation["participation_origin"] = "explicit_cohort"
            participation["source_provenance"] = [_source_provenance_entry(raw_record, origin="explicit_cohort")]

            if resolved_organization_id is None and resolved_person_id is None:
                continue

            if str(participation["id"]) in participation_ids:
                _upsert_record(
                    participations_by_id,
                    participation,
                    prefer_incoming_keys=(
                        "source_table",
                        "source_record_id",
                        "participation_status",
                        "notes",
                        "participation_origin",
                        "person_id",
                    ),
                )
            else:
                participation_ids.add(str(participation["id"]))
                participations_by_id[str(participation["id"])] = participation

        review_rows.extend(
            _review_rows_for_flags(
                source_table=raw_record.source_table,
                source_record_id=raw_source_record_id,
                flag_codes=batch.review_flags,
                record_label=row.get("Company Name") or row.get("Link to Application"),
            )
        )

    organizations = list(organizations_by_id.values())
    people = list(people_by_id.values())
    mentor_profiles = list(mentor_profiles_by_id.values())
    programs = list(programs_by_id.values())
    cohorts = list(cohorts_by_id.values())
    participations = list(participations_by_id.values())

    normalized = {
        "organizations": organizations,
        "people": people,
        "affiliations": affiliations,
        "programs": programs,
        "cohorts": cohorts,
        "participations": participations,
        "mentor_profiles": mentor_profiles,
    }
    override_document = load_override_document(overrides_path)
    reviewed_collections, normalized_override_applications = apply_normalized_overrides(normalized, override_document)

    content_bundle = build_content_intelligence_bundle(
        organizations=reviewed_collections["organizations"],
        people_payloads=reviewed_collections["people"],
        affiliations=reviewed_collections["affiliations"],
        participations=reviewed_collections["participations"],
        cohorts=reviewed_collections["cohorts"],
        source_system="demo_pipeline",
    )
    reviewed_content_bundle, content_override_applications = apply_content_bundle_overrides(
        content_bundle,
        override_document,
    )
    combined_review_rows = review_rows + list(content_bundle.get("review_rows", []))
    reviewed_review_rows, review_override_applications = apply_review_row_overrides(
        combined_review_rows,
        override_document,
    )
    reviewed_truth = build_reviewed_truth_artifact(
        override_document=override_document,
        reviewed_collections=reviewed_collections,
        review_rows=reviewed_review_rows,
        applications=normalized_override_applications + content_override_applications + review_override_applications,
    )

    reporting_snapshot = build_reporting_snapshot(
        organizations=reviewed_collections["organizations"],
        people_payloads=reviewed_collections["people"],
        mentor_profiles=reviewed_collections["mentor_profiles"],
        affiliations=reviewed_collections["affiliations"],
        participations=reviewed_collections["participations"],
        cohorts=reviewed_collections["cohorts"],
        review_rows=reviewed_review_rows,
        content_bundle=reviewed_content_bundle,
    )

    ecosystem_summary = build_ecosystem_summary(
        organizations=reviewed_collections["organizations"],
        people=reviewed_collections["people"],
        mentor_profiles=reviewed_collections["mentor_profiles"],
        participation_records=reviewed_collections["participations"],
    )
    ecosystem_summary["review_flag_count"] = len(reviewed_review_rows)
    ecosystem_summary["content_ready_organization_count"] = len(reporting_snapshot["content_ready_organizations"])
    ecosystem_summary["content_ready_people_count"] = len(reporting_snapshot["content_ready_people"])

    return {
        "raw_sources": raw_sources
        or {
            "active_members": {
                "file_path": "",
                "row_count": len(raw_active_members),
            },
            "mentors": {
                "file_path": "",
                "row_count": len(raw_mentors),
            },
            "cohorts": {
                "file_path": "",
                "row_count": len(raw_cohorts),
            },
        },
        "normalized": normalized,
        "reviewed_truth": reviewed_truth,
        "content_intelligence": reviewed_content_bundle,
        "review_rows": reviewed_review_rows,
        "reporting_snapshot": reporting_snapshot,
        "ecosystem_summary": ecosystem_summary,
    }


def build_demo_bundle(
    active_members_path: Path = DEFAULT_ACTIVE_MEMBERS_PATH,
    mentors_path: Path = DEFAULT_MENTORS_PATH,
    cohorts_path: Optional[Path] = DEFAULT_COHORTS_PATH,
    overrides_path: Optional[Path] = DEFAULT_OVERRIDES_FILE,
) -> dict[str, object]:
    """Run the sample demo pipeline end to end."""

    raw_active_members = load_airtable_csv_export(active_members_path, source_table="Active Members")
    raw_mentors = load_airtable_csv_export(mentors_path, source_table="Mentors")
    raw_cohorts = (
        load_airtable_csv_export(cohorts_path, source_table="Cohorts")
        if cohorts_path is not None and cohorts_path.exists()
        else []
    )

    return build_bundle_from_raw_records(
        raw_active_members=raw_active_members,
        raw_mentors=raw_mentors,
        raw_cohorts=raw_cohorts,
        overrides_path=overrides_path,
        raw_sources={
            "active_members": {
                "file_path": str(active_members_path),
                "row_count": len(raw_active_members),
            },
            "mentors": {
                "file_path": str(mentors_path),
                "row_count": len(raw_mentors),
            },
            "cohorts": {
                "file_path": None if cohorts_path is None else str(cohorts_path),
                "row_count": len(raw_cohorts),
            },
        },
    )


def write_demo_outputs(bundle: dict[str, object], output_dir: Path = DEFAULT_OUTPUT_DIR) -> list[Path]:
    """Write demo outputs to a local folder for inspection."""

    output_dir.mkdir(parents=True, exist_ok=True)
    normalized = dict(bundle.get("normalized", {}))
    reporting_snapshot = dict(bundle.get("reporting_snapshot", {}))
    reviewed_truth = dict(bundle.get("reviewed_truth", {}))

    files = {
        "normalized_bundle.json": normalized,
        "reviewed_truth.json": reviewed_truth,
        "review_flags.json": bundle.get("review_rows", []),
        "content_intelligence.json": bundle.get("content_intelligence", {}),
        "reporting_snapshot.json": reporting_snapshot,
        "ecosystem_summary.json": bundle.get("ecosystem_summary", {}),
    }

    written_paths: list[Path] = []
    for file_name, payload in files.items():
        path = output_dir / file_name
        path.write_text(json.dumps(payload, indent=2, default=_json_default) + "\n", encoding="utf-8")
        written_paths.append(path)

    markdown_path = output_dir / "ecosystem_report.md"
    markdown_path.write_text(render_markdown_report(reporting_snapshot), encoding="utf-8")
    written_paths.append(markdown_path)

    candidate_rows = build_content_candidates_from_bundle(bundle)
    written_paths.extend(write_content_candidate_outputs(candidate_rows, output_dir))
    brief_rows = build_content_briefs_from_bundle(bundle)
    written_paths.extend(write_content_brief_outputs(brief_rows, output_dir))
    editorial_plan = build_editorial_plan(brief_rows)
    written_paths.extend(write_editorial_plan_outputs(editorial_plan, output_dir))
    editorial_assignments = build_editorial_assignments(editorial_plan)
    written_paths.extend(write_assignment_outputs(editorial_assignments, output_dir))
    written_paths.append(
        write_weekly_export_summary(editorial_plan, editorial_assignments, bundle.get("review_rows", []), output_dir)
    )

    manifest_path = output_dir / "snapshot_manifest.json"
    artifact_paths = written_paths + [manifest_path]
    manifest = {
        "snapshot_name": output_dir.name,
        "generated_at": _utc_timestamp(),
        "output_dir": str(output_dir),
        "raw_sources": bundle.get("raw_sources", {}),
        "summary": bundle.get("ecosystem_summary", {}),
        "reviewed_truth": {
            "override_file_path": reviewed_truth.get("override_file_path"),
            "rule_count": reviewed_truth.get("rule_count", 0),
            "applied_rule_count": reviewed_truth.get("applied_rule_count", 0),
            "unmatched_rule_count": reviewed_truth.get("unmatched_rule_count", 0),
        },
        "artifacts": [
            {
                "file_name": path.name,
                "path": str(path),
                "description": SNAPSHOT_ARTIFACT_DESCRIPTIONS.get(path.name, ""),
            }
            for path in artifact_paths
        ],
        "reporting_sections": list(reporting_snapshot.keys()),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, default=_json_default) + "\n", encoding="utf-8")
    written_paths.append(manifest_path)
    return written_paths


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the local sample-data demo pipeline."""

    parser = argparse.ArgumentParser(description="Run the OM Content Engine sample-data demo pipeline.")
    parser.add_argument(
        "--active-members",
        default=str(DEFAULT_ACTIVE_MEMBERS_PATH),
        help="Path to the sample Active Members CSV export.",
    )
    parser.add_argument(
        "--mentors",
        default=str(DEFAULT_MENTORS_PATH),
        help="Path to the sample Mentors CSV export.",
    )
    parser.add_argument(
        "--cohorts",
        default=str(DEFAULT_COHORTS_PATH),
        help="Path to the sample Cohorts CSV export.",
    )
    parser.add_argument(
        "--overrides",
        default=str(DEFAULT_OVERRIDES_FILE),
        help="Optional reviewed-truth JSON override file. Missing files are ignored.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where demo outputs should be written.",
    )
    args = parser.parse_args(argv)

    bundle = build_demo_bundle(
        active_members_path=Path(args.active_members),
        mentors_path=Path(args.mentors),
        cohorts_path=Path(args.cohorts),
        overrides_path=Path(args.overrides) if args.overrides else None,
    )
    written_paths = write_demo_outputs(bundle, Path(args.output_dir))

    print("Wrote demo outputs:")
    for path in written_paths:
        print("- %s" % path)
    print("")
    print(json.dumps(bundle["ecosystem_summary"], indent=2, default=_json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
