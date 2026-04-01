"""Build a compact internal-only content candidate export from the current snapshot."""

from __future__ import annotations

import argparse
import csv
import io
import json
from collections import defaultdict
from pathlib import Path
from typing import Optional, Sequence

from src.reporting.content_summary import (
    derive_content_trust_basis,
    derive_highest_readiness_level,
    derive_person_source_path,
    reviewed_override_count,
    reviewed_truth_applied,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_DIR = REPO_ROOT / "data" / "processed" / "local_run"

INPUT_FILE_NAMES = {
    "normalized_bundle": "normalized_bundle.json",
    "content_intelligence": "content_intelligence.json",
    "reporting_snapshot": "reporting_snapshot.json",
    "reviewed_truth": "reviewed_truth.json",
    "review_flags": "review_flags.json",
    "ecosystem_summary": "ecosystem_summary.json",
    "snapshot_manifest": "snapshot_manifest.json",
}

OUTPUT_JSON_NAME = "content_candidates.json"
OUTPUT_CSV_NAME = "content_candidates.csv"

MATERIAL_REVIEW_FLAGS = {
    "review_placeholder_record",
    "review_duplicate_suspected",
    "review_missing_name",
    "review_missing_organization_name",
    "review_internal_record_detected",
}

SUGGESTED_USE_VALUES = {
    "linkedin_post",
    "short_form_video",
    "carousel",
    "mini_feature",
    "hold_for_review",
}


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "active"}


def _slug(value: object) -> str:
    return "".join(char.lower() if char.isalnum() else "_" for char in str(value or "")).strip("_")


def _split_csv_text(value: object) -> list[str]:
    if value in (None, "", []):
        return []
    return [part.strip() for part in str(value).split(",") if part.strip()]


def _unique(values: Sequence[object]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


def _normalized_label(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_snapshot_inputs(run_dir: Path = DEFAULT_RUN_DIR) -> dict[str, object]:
    """Load the existing pipeline output bundle from a run directory."""

    loaded: dict[str, object] = {"run_dir": str(run_dir)}
    missing: list[str] = []
    for key, file_name in INPUT_FILE_NAMES.items():
        path = run_dir / file_name
        if not path.exists():
            missing.append(file_name)
            continue
        loaded[key] = _load_json(path)

    required_keys = {"content_intelligence", "reporting_snapshot", "reviewed_truth", "review_flags"}
    if required_keys.difference(loaded.keys()):
        raise FileNotFoundError(
            "Missing required pipeline output files in %s: %s"
            % (run_dir, ", ".join(sorted(missing)))
        )
    return loaded


def _primary_person_for_org(
    organization_id: str,
    *,
    affiliations_by_org: dict[str, list[dict[str, object]]],
    people_by_id: dict[str, dict[str, object]],
) -> Optional[dict[str, object]]:
    ranked = sorted(
        affiliations_by_org.get(organization_id, []),
        key=lambda row: (
            0 if _truthy(row.get("spokesperson_flag")) else 1,
            0 if _truthy(row.get("founder_flag")) else 1,
            0 if _truthy(row.get("primary_contact_flag")) else 1,
            0 if _truthy(row.get("active_flag")) else 1,
            str(row.get("role_title") or ""),
        ),
    )
    for affiliation in ranked:
        person = people_by_id.get(str(affiliation.get("person_id") or ""))
        if person is not None:
            return person
    return None


def _primary_org_for_person(
    person_id: str,
    *,
    affiliations_by_person: dict[str, list[dict[str, object]]],
    organizations_by_id: dict[str, dict[str, object]],
) -> Optional[dict[str, object]]:
    ranked = sorted(
        affiliations_by_person.get(person_id, []),
        key=lambda row: (
            0 if _truthy(row.get("founder_flag")) else 1,
            0 if _truthy(row.get("spokesperson_flag")) else 1,
            0 if _truthy(row.get("primary_contact_flag")) else 1,
            0 if _truthy(row.get("active_flag")) else 1,
            str(row.get("role_title") or ""),
        ),
    )
    for affiliation in ranked:
        organization = organizations_by_id.get(str(affiliation.get("organization_id") or ""))
        if organization is not None:
            return organization
    return None


def _participations_for_candidate(
    *,
    organization_id: Optional[str],
    person_id: Optional[str],
    participations_by_org: dict[str, list[dict[str, object]]],
    participations_by_person: dict[str, list[dict[str, object]]],
) -> list[dict[str, object]]:
    if person_id:
        direct = participations_by_person.get(person_id, [])
        if direct:
            return direct
    if organization_id:
        return participations_by_org.get(organization_id, [])
    return []


def _status_rank(value: object) -> int:
    order = {
        "active": 0,
        "alumni": 1,
        "pending": 2,
        "withdrawn": 3,
        "unknown": 4,
    }
    return order.get(str(value or "").strip().lower(), 99)


def _participation_summary(
    participations: Sequence[dict[str, object]],
    *,
    cohorts_by_id: dict[str, dict[str, object]],
    programs_by_id: dict[str, dict[str, object]],
) -> tuple[Optional[str], list[str]]:
    if not participations:
        return None, []

    statuses = sorted(
        _unique(participation.get("participation_status") for participation in participations),
        key=_status_rank,
    )
    program_names: list[str] = []
    for participation in participations:
        cohort = cohorts_by_id.get(str(participation.get("cohort_id") or ""))
        if cohort is None:
            continue
        program = programs_by_id.get(str(cohort.get("program_id") or ""))
        if program is not None:
            program_names.append(program.get("program_name"))
    return (statuses[0] if statuses else None), _unique(program_names)


def _matched_review_rows(
    *,
    source_record_id: object,
    record_label: Optional[str],
    review_rows: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    source_id_text = str(source_record_id or "").strip()
    label_text = _normalized_label(record_label)
    rows: list[dict[str, object]] = []
    for row in review_rows:
        if str(row.get("source_record_id") or "").strip() != source_id_text:
            continue
        row_label = _normalized_label(row.get("record_label"))
        if label_text and row_label and row_label != label_text:
            continue
        rows.append(dict(row))
    return rows


def _material_review_burden(rows: Sequence[dict[str, object]]) -> bool:
    return any(str(row.get("flag_code") or "") in MATERIAL_REVIEW_FLAGS for row in rows)


def _review_flag_summary(rows: Sequence[dict[str, object]]) -> str:
    codes = _unique(row.get("flag_code") for row in rows)
    if not codes:
        return "none"
    if len(codes) <= 3:
        return "; ".join(codes)
    return "%s; +%s more" % ("; ".join(codes[:3]), len(codes) - 3)


def _has_minimum_narrative_substance(
    *,
    intelligence: dict[str, object],
    person: Optional[dict[str, object]],
    organization: Optional[dict[str, object]],
    program_names: Sequence[str],
    participation_status: Optional[str],
) -> bool:
    anchors = [
        intelligence.get("narrative_theme"),
        intelligence.get("message_pillar"),
        intelligence.get("story_type"),
        intelligence.get("audience_tags"),
        intelligence.get("proof_tags"),
        person.get("bio") if person is not None else None,
        person.get("expertise_tags") if person is not None else None,
        organization.get("website") if organization is not None else None,
        organization.get("description") if organization is not None else None,
        program_names,
        participation_status,
    ]
    return any(bool(value) for value in anchors)


def _supporting_evidence_summary(
    *,
    intelligence: dict[str, object],
    person: Optional[dict[str, object]],
    organization: Optional[dict[str, object]],
    primary_person: Optional[dict[str, object]],
    participation_status: Optional[str],
    program_names: Sequence[str],
    trust_basis: str,
) -> str:
    items: list[str] = []
    if organization is not None and organization.get("org_type"):
        items.append("org_type=%s" % organization.get("org_type"))
    if person is not None and person.get("person_type"):
        items.append("person_type=%s" % person.get("person_type"))
    if person is not None and person.get("bio"):
        items.append("bio")
    if person is not None and person.get("expertise_tags"):
        items.append("expertise")
    if person is not None and person.get("headshot_url"):
        items.append("headshot")
    if organization is not None and organization.get("website"):
        items.append("website")
    if organization is not None and organization.get("description"):
        items.append("description")
    if primary_person is not None and primary_person.get("full_name"):
        items.append("spokesperson=%s" % primary_person.get("full_name"))
    if participation_status:
        items.append("participation=%s" % participation_status)
    if program_names:
        items.append("programs=%s" % ", ".join(program_names))
    if trust_basis != "heuristic_only":
        items.append("trust=%s" % trust_basis)
    return "; ".join(_unique(items[:5]))


def _why_it_matters(
    *,
    record_type: str,
    label: str,
    organization: Optional[dict[str, object]],
    intelligence: dict[str, object],
    participation_status: Optional[str],
) -> str:
    if _truthy(intelligence.get("founder_story_candidate")):
        if participation_status == "active":
            return "%s is tied to an active founder story with current program proof." % label
        return "%s has a usable founder-story angle for internal planning." % label
    if _truthy(intelligence.get("mentor_story_candidate")):
        return "%s has usable mentor expertise and profile detail for a feature shortlist." % label
    if _truthy(intelligence.get("ecosystem_proof_candidate")):
        if record_type == "organization" and organization is not None and str(organization.get("org_type") or "") == "partner":
            return "%s supports ecosystem-proof and partner visibility planning." % label
        return "%s supports ecosystem-proof or recruitment messaging." % label
    if _truthy(intelligence.get("spokesperson_candidate")):
        return "%s can serve as a spokesperson candidate in internal planning." % label
    return "%s is usable enough to consider for internal content planning." % label


def _suggested_use(
    *,
    intelligence: dict[str, object],
    planning_safe: bool,
    public_ready: bool,
) -> str:
    if not planning_safe or not _truthy(intelligence.get("content_ready")):
        return "hold_for_review"
    story_type = str(intelligence.get("story_type") or "")
    if story_type in {"founder_spotlight", "mentor_feature"}:
        return "mini_feature"
    if story_type == "ecosystem_proof":
        return "carousel"
    if public_ready and _truthy(intelligence.get("spokesperson_candidate")):
        return "short_form_video"
    return "linkedin_post"


def _is_internal_context(
    *,
    person: Optional[dict[str, object]],
    organization: Optional[dict[str, object]],
) -> bool:
    if organization is not None and str(organization.get("org_type") or "") == "internal":
        return True
    if person is not None and organization is None and "internal" in str(person.get("source_table") or "").lower():
        return True
    return False


def _candidate_record(
    *,
    record_type: str,
    intelligence: dict[str, object],
    person: Optional[dict[str, object]],
    organization: Optional[dict[str, object]],
    primary_person: Optional[dict[str, object]],
    participation_status: Optional[str],
    program_names: Sequence[str],
    review_rows: Sequence[dict[str, object]],
    trust_basis: str,
) -> dict[str, object]:
    label = (
        str(person.get("full_name") or "")
        if record_type == "person" and person is not None
        else str(organization.get("name") or "")
    )
    public_ready = _truthy(intelligence.get("externally_publishable"))
    planning_safe = True
    return {
        "entity_id": (person or organization or {}).get("id"),
        "record_type": record_type,
        "org_name": None if organization is None else organization.get("name"),
        "primary_person_name": (
            person.get("full_name")
            if record_type == "person" and person is not None
            else None if primary_person is None else primary_person.get("full_name")
        ),
        "person_provenance": (
            None
            if record_type == "organization" and primary_person is None
            else derive_person_source_path(person if record_type == "person" else primary_person or {})
        ),
        "org_type": None if organization is None else organization.get("org_type"),
        "participation_status": participation_status,
        "program_names": list(program_names),
        "audience_names": _split_csv_text(intelligence.get("audience_tags")),
        "readiness_level": derive_highest_readiness_level(intelligence),
        "trust_basis": trust_basis,
        "reviewed_truth_applied": reviewed_truth_applied(intelligence)
        or reviewed_truth_applied(person)
        or reviewed_truth_applied(organization),
        "reviewed_override_count": reviewed_override_count(intelligence, person, organization),
        "why_it_matters": _why_it_matters(
            record_type=record_type,
            label=label,
            organization=organization,
            intelligence=intelligence,
            participation_status=participation_status,
        ),
        "narrative_theme": intelligence.get("narrative_theme"),
        "message_pillar": intelligence.get("message_pillar"),
        "suggested_use": _suggested_use(
            intelligence=intelligence,
            planning_safe=planning_safe,
            public_ready=public_ready,
        ),
        "supporting_evidence_summary": _supporting_evidence_summary(
            intelligence=intelligence,
            person=person,
            organization=organization,
            primary_person=primary_person,
            participation_status=participation_status,
            program_names=program_names,
            trust_basis=trust_basis,
        ),
        "review_flag_summary": _review_flag_summary(review_rows),
        "planning_safe": planning_safe,
        "public_ready": public_ready,
    }


def _include_candidate(
    *,
    intelligence: dict[str, object],
    person: Optional[dict[str, object]],
    organization: Optional[dict[str, object]],
    program_names: Sequence[str],
    participation_status: Optional[str],
    review_rows: Sequence[dict[str, object]],
) -> bool:
    reviewed = reviewed_truth_applied(intelligence) or reviewed_truth_applied(person) or reviewed_truth_applied(organization)
    spotlight = _truthy(intelligence.get("spotlight_ready"))
    if not (spotlight or reviewed):
        return False
    if not _truthy(intelligence.get("content_eligible")):
        return False
    if _is_internal_context(person=person, organization=organization):
        return False
    if person is not None and derive_person_source_path(person) == "semi_structured_member_side" and not reviewed_truth_applied(person):
        return False
    if _material_review_burden(review_rows):
        return False
    if not _has_minimum_narrative_substance(
        intelligence=intelligence,
        person=person,
        organization=organization,
        program_names=program_names,
        participation_status=participation_status,
    ):
        return False
    return True


def build_content_candidates(snapshot: dict[str, object]) -> list[dict[str, object]]:
    """Build the internal-only candidate export from a loaded snapshot."""

    reviewed_truth = dict(snapshot.get("reviewed_truth", {}))
    content_bundle = dict(snapshot.get("content_intelligence", {}))
    review_rows = list(snapshot.get("review_flags", []))
    collections = dict(reviewed_truth.get("collections", {}))

    organizations = list(collections.get("organizations", []))
    people = list(collections.get("people", []))
    affiliations = list(collections.get("affiliations", []))
    programs = list(collections.get("programs", []))
    cohorts = list(collections.get("cohorts", []))
    participations = list(collections.get("participations", []))

    organizations_by_id = {str(item.get("id")): item for item in organizations}
    people_by_id = {str(item.get("id")): item for item in people}
    programs_by_id = {str(item.get("id")): item for item in programs}
    cohorts_by_id = {str(item.get("id")): item for item in cohorts}

    affiliations_by_org: dict[str, list[dict[str, object]]] = defaultdict(list)
    affiliations_by_person: dict[str, list[dict[str, object]]] = defaultdict(list)
    for affiliation in affiliations:
        affiliations_by_org[str(affiliation.get("organization_id") or "")].append(affiliation)
        affiliations_by_person[str(affiliation.get("person_id") or "")].append(affiliation)

    participations_by_org: dict[str, list[dict[str, object]]] = defaultdict(list)
    participations_by_person: dict[str, list[dict[str, object]]] = defaultdict(list)
    for participation in participations:
        participations_by_org[str(participation.get("organization_id") or "")].append(participation)
        participations_by_person[str(participation.get("person_id") or "")].append(participation)

    candidates: list[dict[str, object]] = []

    for intelligence in content_bundle.get("organizations", []):
        organization = organizations_by_id.get(str(intelligence.get("linked_organization_id") or ""))
        if organization is None:
            continue
        primary_person = _primary_person_for_org(
            str(organization.get("id")),
            affiliations_by_org=affiliations_by_org,
            people_by_id=people_by_id,
        )
        participation_rows = _participations_for_candidate(
            organization_id=str(organization.get("id")),
            person_id=None,
            participations_by_org=participations_by_org,
            participations_by_person=participations_by_person,
        )
        participation_status, program_names = _participation_summary(
            participation_rows,
            cohorts_by_id=cohorts_by_id,
            programs_by_id=programs_by_id,
        )
        matched_flags = _matched_review_rows(
            source_record_id=organization.get("source_record_id"),
            record_label=str(organization.get("name") or ""),
            review_rows=review_rows,
        )
        if not _include_candidate(
            intelligence=intelligence,
            person=None,
            organization=organization,
            program_names=program_names,
            participation_status=participation_status,
            review_rows=matched_flags,
        ):
            continue
        trust_basis = derive_content_trust_basis(intelligence, organization)
        candidates.append(
            _candidate_record(
                record_type="organization",
                intelligence=intelligence,
                person=None,
                organization=organization,
                primary_person=primary_person,
                participation_status=participation_status,
                program_names=program_names,
                review_rows=matched_flags,
                trust_basis=trust_basis,
            )
        )

    for intelligence in content_bundle.get("people", []):
        person = people_by_id.get(str(intelligence.get("linked_person_id") or ""))
        if person is None:
            continue
        primary_org = _primary_org_for_person(
            str(person.get("id")),
            affiliations_by_person=affiliations_by_person,
            organizations_by_id=organizations_by_id,
        )
        participation_rows = _participations_for_candidate(
            organization_id=None if primary_org is None else str(primary_org.get("id")),
            person_id=str(person.get("id")),
            participations_by_org=participations_by_org,
            participations_by_person=participations_by_person,
        )
        participation_status, program_names = _participation_summary(
            participation_rows,
            cohorts_by_id=cohorts_by_id,
            programs_by_id=programs_by_id,
        )
        matched_flags = _matched_review_rows(
            source_record_id=person.get("source_record_id"),
            record_label=str(person.get("full_name") or ""),
            review_rows=review_rows,
        )
        if not _include_candidate(
            intelligence=intelligence,
            person=person,
            organization=primary_org,
            program_names=program_names,
            participation_status=participation_status,
            review_rows=matched_flags,
        ):
            continue
        trust_basis = derive_content_trust_basis(intelligence, person)
        candidates.append(
            _candidate_record(
                record_type="person",
                intelligence=intelligence,
                person=person,
                organization=primary_org,
                primary_person=person,
                participation_status=participation_status,
                program_names=program_names,
                review_rows=matched_flags,
                trust_basis=trust_basis,
            )
        )

    return sorted(
        candidates,
        key=lambda row: (
            0 if str(row.get("readiness_level")) == "externally_publishable" else 1,
            0 if str(row.get("readiness_level")) == "spotlight_ready" else 1,
            -int(row.get("reviewed_override_count") or 0),
            str(row.get("org_name") or ""),
            str(row.get("primary_person_name") or ""),
        ),
    )


def build_content_candidates_from_bundle(bundle: dict[str, object]) -> list[dict[str, object]]:
    """Build content candidates directly from an in-memory pipeline bundle."""

    snapshot = {
        "content_intelligence": bundle.get("content_intelligence", {}),
        "reporting_snapshot": bundle.get("reporting_snapshot", {}),
        "reviewed_truth": bundle.get("reviewed_truth", {}),
        "review_flags": bundle.get("review_rows", []),
        "ecosystem_summary": bundle.get("ecosystem_summary", {}),
    }
    return build_content_candidates(snapshot)


def _csv_ready_row(record: dict[str, object]) -> dict[str, object]:
    csv_row = dict(record)
    for key in ("program_names", "audience_names"):
        value = csv_row.get(key)
        if isinstance(value, list):
            csv_row[key] = "; ".join(str(item) for item in value)
    return csv_row


def render_candidates_csv(candidates: Sequence[dict[str, object]]) -> str:
    """Render the compact candidate export as CSV."""

    if not candidates:
        return ""
    fieldnames = list(candidates[0].keys())
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in candidates:
        writer.writerow(_csv_ready_row(row))
    return buffer.getvalue()


def write_content_candidate_outputs(
    candidates: Sequence[dict[str, object]],
    run_dir: Path,
    *,
    write_csv: bool = True,
) -> list[Path]:
    """Write content candidate exports into an existing run directory."""

    run_dir.mkdir(parents=True, exist_ok=True)
    written_paths: list[Path] = []

    json_path = run_dir / OUTPUT_JSON_NAME
    json_path.write_text(json.dumps(list(candidates), indent=2) + "\n", encoding="utf-8")
    written_paths.append(json_path)

    if write_csv:
        csv_path = run_dir / OUTPUT_CSV_NAME
        csv_path.write_text(render_candidates_csv(candidates), encoding="utf-8")
        written_paths.append(csv_path)

    return written_paths


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Build the content candidate export from an existing run directory."""

    parser = argparse.ArgumentParser(description="Build internal content candidate exports from a pipeline run.")
    parser.add_argument(
        "--run-dir",
        default=str(DEFAULT_RUN_DIR),
        help="Run directory containing content_intelligence.json, reviewed_truth.json, and related snapshot files.",
    )
    parser.add_argument(
        "--no-csv",
        action="store_true",
        help="Write only JSON output.",
    )
    args = parser.parse_args(argv)

    run_dir = Path(args.run_dir)
    snapshot = load_snapshot_inputs(run_dir)
    candidates = build_content_candidates(snapshot)
    written_paths = write_content_candidate_outputs(candidates, run_dir, write_csv=not args.no_csv)

    print("Wrote content candidate outputs:")
    for path in written_paths:
        print("- %s" % path)
    print("")
    print(json.dumps({"candidate_count": len(candidates), "run_dir": str(run_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
