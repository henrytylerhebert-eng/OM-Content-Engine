"""Build compact internal briefing packs from the trust-aware content candidates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from src.reporting.content_candidates import (
    OUTPUT_JSON_NAME as CONTENT_CANDIDATES_JSON_NAME,
    build_content_candidates,
    build_content_candidates_from_bundle,
    load_snapshot_inputs,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_DIR = REPO_ROOT / "data" / "processed" / "local_run"
OUTPUT_JSON_NAME = "content_briefs.json"
OUTPUT_MARKDOWN_NAME = "content_briefs.md"

HIGH_RISK_BRIEF_FLAGS = {
    "review_personnel_parse",
    "review_member_side_person_multiple_candidates",
    "review_member_side_person_name_incomplete",
    "review_member_side_person_generic_email",
    "review_member_side_person_context_ambiguous",
    "review_no_person_found",
    "review_no_affiliation_people",
    "review_placeholder_record",
    "review_duplicate_suspected",
    "review_missing_name",
    "review_missing_organization_name",
    "review_sparse_record",
    "review_internal_record_detected",
}

ALLOWED_BRIEF_STATUSES = {
    "planning_safe_only",
    "reviewed_for_internal_use",
    "public_ready",
    "hold_for_review",
}

ALLOWED_SUGGESTED_ANGLES = {
    "founder_journey",
    "behind_the_build",
    "moment_of_progress",
    "ecosystem_proof",
    "participation_signal",
    "hold_for_review",
}

ALLOWED_SUGGESTED_FORMATS = {
    "linkedin_post",
    "short_form_video",
    "carousel",
    "mini_feature",
    "internal_note",
}


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "active"}


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


def _load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_brief_inputs(run_dir: Path = DEFAULT_RUN_DIR) -> dict[str, object]:
    """Load the snapshot inputs used to generate internal content briefs."""

    snapshot = load_snapshot_inputs(run_dir)
    candidate_path = run_dir / CONTENT_CANDIDATES_JSON_NAME
    if candidate_path.exists():
        snapshot["content_candidates"] = _load_json(candidate_path)
    return snapshot


def _entity_collections(snapshot: dict[str, object]) -> tuple[dict[str, dict[str, object]], dict[str, dict[str, object]]]:
    reviewed_truth = dict(snapshot.get("reviewed_truth", {}))
    collections = dict(reviewed_truth.get("collections", {}))
    organizations = {str(item.get("id")): item for item in collections.get("organizations", [])}
    people = {str(item.get("id")): item for item in collections.get("people", [])}
    return organizations, people


def _matched_review_rows(
    *,
    source_record_id: object,
    record_label: Optional[str],
    review_rows: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    source_id_text = str(source_record_id or "").strip()
    label_text = " ".join(str(record_label or "").strip().lower().split())
    matched: list[dict[str, object]] = []
    for row in review_rows:
        if str(row.get("source_record_id") or "").strip() != source_id_text:
            continue
        row_label = " ".join(str(row.get("record_label") or "").strip().lower().split())
        if label_text and row_label and label_text != row_label:
            continue
        matched.append(dict(row))
    return matched


def _candidate_review_rows(
    candidate: dict[str, object],
    *,
    organizations_by_id: dict[str, dict[str, object]],
    people_by_id: dict[str, dict[str, object]],
    review_rows: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    entity = None
    label = None
    if str(candidate.get("record_type") or "") == "organization":
        entity = organizations_by_id.get(str(candidate.get("entity_id") or ""))
        label = candidate.get("org_name")
    else:
        entity = people_by_id.get(str(candidate.get("entity_id") or ""))
        label = candidate.get("primary_person_name")

    if entity is None:
        return []
    return _matched_review_rows(
        source_record_id=entity.get("source_record_id"),
        record_label=str(label or ""),
        review_rows=review_rows,
    )


def _has_high_risk_flags(rows: Sequence[dict[str, object]]) -> bool:
    return any(str(row.get("flag_code") or "") in HIGH_RISK_BRIEF_FLAGS for row in rows)


def _brief_status(candidate: dict[str, object], review_rows: Sequence[dict[str, object]]) -> str:
    if _truthy(candidate.get("public_ready")):
        return "public_ready"
    if _truthy(candidate.get("reviewed_truth_applied")):
        return "reviewed_for_internal_use"
    if not _truthy(candidate.get("planning_safe")):
        return "hold_for_review"
    if _has_high_risk_flags(review_rows):
        return "hold_for_review"
    return "planning_safe_only"


def _suggested_angle(candidate: dict[str, object], brief_status: str) -> str:
    if brief_status == "hold_for_review":
        return "hold_for_review"
    if str(candidate.get("person_provenance") or "") == "mentor_structured":
        return "ecosystem_proof"
    if str(candidate.get("org_type") or "") == "startup" and str(candidate.get("primary_person_name") or "").strip():
        if str(candidate.get("participation_status") or "") == "active":
            return "moment_of_progress"
        return "founder_journey"
    if candidate.get("participation_status"):
        return "participation_signal"
    if str(candidate.get("org_type") or "") in {
        "partner",
        "service_provider",
        "nonprofit",
        "government",
        "university",
        "investor",
        "mentor_org",
    }:
        return "ecosystem_proof"
    return "behind_the_build"


def _suggested_format(candidate: dict[str, object], brief_status: str) -> str:
    if brief_status == "hold_for_review":
        return "internal_note"
    suggested_use = str(candidate.get("suggested_use") or "").strip()
    if suggested_use == "hold_for_review":
        return "internal_note"
    if suggested_use in ALLOWED_SUGGESTED_FORMATS:
        return suggested_use
    return "internal_note"


def _core_story(candidate: dict[str, object], brief_status: str, suggested_angle: str) -> str:
    org_name = str(candidate.get("org_name") or "").strip()
    person_name = str(candidate.get("primary_person_name") or "").strip()
    org_type = str(candidate.get("org_type") or "").strip()
    participation_status = str(candidate.get("participation_status") or "").strip()
    program_names = candidate.get("program_names") or []
    program_text = ", ".join(str(item) for item in program_names if str(item).strip())

    if brief_status == "hold_for_review":
        if org_name:
            return "%s has a possible story signal, but the current record still needs review before staff drafts from it." % org_name
        return "%s has a possible story signal, but the current record still needs review before staff drafts from it." % person_name
    if str(candidate.get("person_provenance") or "") == "mentor_structured":
        return "%s is a mentor record with enough substance for an internal feature brief." % person_name
    if person_name and org_name and org_type == "startup":
        if participation_status == "active" and program_text:
            return "%s is tied to %s, an active %s participant with a usable founder or spokesperson angle." % (
                person_name,
                org_name,
                program_text,
            )
        return "%s is tied to %s and reads like a usable startup story candidate for internal planning." % (
            person_name,
            org_name,
        )
    if org_name and org_type:
        if program_text:
            return "%s is a %s with visible %s participation and enough evidence for an internal brief." % (
                org_name,
                org_type,
                program_text,
            )
        return "%s is a %s candidate with enough evidence for internal planning." % (org_name, org_type)
    return "%s has enough trusted signal for an internal content brief." % (person_name or org_name or "This record")


def _proof_points(candidate: dict[str, object], brief_status: str) -> list[str]:
    points: list[str] = []
    if candidate.get("org_type"):
        points.append("Organization type: %s" % candidate.get("org_type"))
    if candidate.get("primary_person_name") and candidate.get("person_provenance"):
        points.append(
            "Primary person: %s (%s)" % (candidate.get("primary_person_name"), candidate.get("person_provenance"))
        )
    if candidate.get("participation_status"):
        points.append("Participation status: %s" % candidate.get("participation_status"))
    if candidate.get("program_names"):
        points.append("Program context: %s" % ", ".join(candidate.get("program_names")))
    if candidate.get("supporting_evidence_summary"):
        for part in str(candidate.get("supporting_evidence_summary")).split(";"):
            cleaned = part.strip()
            if cleaned:
                points.append(cleaned)
    if _truthy(candidate.get("reviewed_truth_applied")):
        points.append("Reviewed truth has already touched this record.")
    if brief_status == "public_ready":
        points.append("Explicit public-ready approval is already present.")
    return _unique(points[:5])


def _hook_options(candidate: dict[str, object], suggested_angle: str, brief_status: str) -> list[str]:
    org_name = str(candidate.get("org_name") or "").strip()
    person_name = str(candidate.get("primary_person_name") or "").strip()
    label = person_name or org_name or "This record"
    if brief_status == "hold_for_review":
        return [
            "What is the safest story we can tell about %s right now?" % label,
            "What still needs review before %s becomes a real brief?" % label,
        ]
    if suggested_angle == "founder_journey":
        return [
            "%s as a founder story worth tracking." % label,
            "What progress does %s actually prove?" % label,
            "Why %s matters inside the OM ecosystem." % label,
        ]
    if suggested_angle == "moment_of_progress":
        return [
            "A current progress signal from %s." % label,
            "Why %s is worth revisiting right now." % label,
            "What this latest step says about %s." % label,
        ]
    if suggested_angle == "participation_signal":
        return [
            "%s as a program participation signal." % label,
            "What OM can point to in %s's program path." % label,
            "Why %s belongs in this planning cycle." % label,
        ]
    if suggested_angle == "ecosystem_proof":
        return [
            "%s as ecosystem proof." % label,
            "Why %s is a useful internal signal." % label,
            "Where %s could support a broader OM story." % label,
        ]
    return [
        "What is actually being built around %s?" % label,
        "How %s fits the current planning cycle." % label,
    ]


def _guardrails(candidate: dict[str, object], review_rows: Sequence[dict[str, object]]) -> list[str]:
    guardrails = [
        "Do not treat this brief as publication approval unless public_ready is true."
    ]
    if str(candidate.get("trust_basis") or "") == "heuristic_only":
        guardrails.append("Do not imply manual approval or final publishing clearance.")
    if str(candidate.get("person_provenance") or "") == "mentor_structured" and not candidate.get("org_name"):
        guardrails.append("Do not assume current employer or company context beyond the mentor record.")
    if candidate.get("participation_status") == "alumni":
        guardrails.append("Do not describe program participation as current.")
    if candidate.get("participation_status") == "withdrawn":
        guardrails.append("Do not describe this record as a current active participant.")
    if review_rows:
        guardrails.append(
            "Do not overclaim details that depend on unresolved review items: %s." % (
                ", ".join(_unique(row.get("flag_code") for row in review_rows[:3]))
            )
        )
    return _unique(guardrails)


def _unresolved_review_notes(candidate: dict[str, object], review_rows: Sequence[dict[str, object]]) -> str:
    if not review_rows:
        return "No matched unresolved review flags on the primary record."
    codes = _unique(row.get("flag_code") for row in review_rows)
    notes = [
        str(row.get("note") or "").strip()
        for row in review_rows
        if str(row.get("note") or "").strip()
    ]
    summary = "Unresolved review items: %s." % ", ".join(codes[:4])
    if notes:
        summary += " Notes: %s." % " | ".join(notes[:2])
    return summary


def _evidence_summary(candidate: dict[str, object], proof_points: Sequence[str]) -> str:
    base = str(candidate.get("supporting_evidence_summary") or "").strip()
    if base:
        return base
    return "; ".join(_unique(proof_points[:4]))


def _brief_record(
    candidate: dict[str, object],
    *,
    review_rows: Sequence[dict[str, object]],
) -> dict[str, object]:
    brief_status = _brief_status(candidate, review_rows)
    suggested_angle = _suggested_angle(candidate, brief_status)
    suggested_format = _suggested_format(candidate, brief_status)
    proof_points = _proof_points(candidate, brief_status)
    brief = {
        "entity_id": candidate.get("entity_id"),
        "org_name": candidate.get("org_name"),
        "primary_person_name": candidate.get("primary_person_name"),
        "program_names": list(candidate.get("program_names") or []),
        "audience_names": list(candidate.get("audience_names") or []),
        "readiness_level": candidate.get("readiness_level"),
        "trust_basis": candidate.get("trust_basis"),
        "reviewed_truth_applied": candidate.get("reviewed_truth_applied"),
        "public_ready": candidate.get("public_ready"),
        "brief_status": brief_status,
        "core_story": _core_story(candidate, brief_status, suggested_angle),
        "why_it_matters": candidate.get("why_it_matters"),
        "proof_points": proof_points,
        "suggested_angle": suggested_angle,
        "suggested_format": suggested_format,
        "hook_options": _hook_options(candidate, suggested_angle, brief_status),
        "guardrails": _guardrails(candidate, review_rows),
        "unresolved_review_notes": _unresolved_review_notes(candidate, review_rows),
        "evidence_summary": _evidence_summary(candidate, proof_points),
    }
    return brief


def build_content_briefs(snapshot: dict[str, object]) -> list[dict[str, object]]:
    """Build internal content briefs from an existing snapshot."""

    candidates = snapshot.get("content_candidates")
    if not isinstance(candidates, list):
        candidates = build_content_candidates(snapshot)

    organizations_by_id, people_by_id = _entity_collections(snapshot)
    review_rows = list(snapshot.get("review_flags", []))
    briefs = [
        _brief_record(
            candidate,
            review_rows=_candidate_review_rows(
                candidate,
                organizations_by_id=organizations_by_id,
                people_by_id=people_by_id,
                review_rows=review_rows,
            ),
        )
        for candidate in candidates
        if _truthy(candidate.get("planning_safe"))
    ]
    return briefs


def build_content_briefs_from_bundle(bundle: dict[str, object]) -> list[dict[str, object]]:
    """Build content briefs directly from an in-memory pipeline bundle."""

    snapshot = {
        "content_candidates": build_content_candidates_from_bundle(bundle),
        "reviewed_truth": bundle.get("reviewed_truth", {}),
        "review_flags": bundle.get("review_rows", []),
    }
    return build_content_briefs(snapshot)


def render_markdown_briefs(briefs: Sequence[dict[str, object]]) -> str:
    """Render the brief pack as a readable markdown document."""

    lines = ["# Content Brief Pack", ""]
    for brief in briefs:
        title = str(brief.get("primary_person_name") or brief.get("org_name") or brief.get("entity_id") or "Brief")
        subtitle = str(brief.get("org_name") or "").strip()
        if subtitle and subtitle != title:
            lines.append("## %s (%s)" % (title, subtitle))
        else:
            lines.append("## %s" % title)
        lines.append("")
        lines.append("- Brief status: `%s`" % brief.get("brief_status"))
        lines.append(
            "- Readiness / trust: `%s` / `%s` / public_ready=`%s`"
            % (
                brief.get("readiness_level"),
                brief.get("trust_basis"),
                brief.get("public_ready"),
            )
        )
        lines.append("- Core story: %s" % brief.get("core_story"))
        lines.append("- Why it matters: %s" % brief.get("why_it_matters"))
        lines.append("- Suggested angle: `%s`" % brief.get("suggested_angle"))
        lines.append("- Suggested format: `%s`" % brief.get("suggested_format"))
        lines.append("- Evidence summary: %s" % brief.get("evidence_summary"))
        lines.append("- Unresolved review notes: %s" % brief.get("unresolved_review_notes"))
        lines.append("- Proof points:")
        for point in brief.get("proof_points", []):
            lines.append("  - %s" % point)
        lines.append("- Hook options:")
        for hook in brief.get("hook_options", []):
            lines.append("  - %s" % hook)
        lines.append("- Guardrails:")
        for item in brief.get("guardrails", []):
            lines.append("  - %s" % item)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def write_content_brief_outputs(briefs: Sequence[dict[str, object]], run_dir: Path) -> list[Path]:
    """Write the internal brief pack into an existing run directory."""

    run_dir.mkdir(parents=True, exist_ok=True)
    written_paths: list[Path] = []

    json_path = run_dir / OUTPUT_JSON_NAME
    json_path.write_text(json.dumps(list(briefs), indent=2) + "\n", encoding="utf-8")
    written_paths.append(json_path)

    markdown_path = run_dir / OUTPUT_MARKDOWN_NAME
    markdown_path.write_text(render_markdown_briefs(briefs), encoding="utf-8")
    written_paths.append(markdown_path)

    return written_paths


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Build internal content briefs from an existing pipeline run."""

    parser = argparse.ArgumentParser(description="Build internal content briefs from a pipeline run.")
    parser.add_argument(
        "--run-dir",
        default=str(DEFAULT_RUN_DIR),
        help="Run directory containing content_candidates.json and the reviewed snapshot files.",
    )
    args = parser.parse_args(argv)

    run_dir = Path(args.run_dir)
    snapshot = load_brief_inputs(run_dir)
    briefs = build_content_briefs(snapshot)
    written_paths = write_content_brief_outputs(briefs, run_dir)

    print("Wrote content brief outputs:")
    for path in written_paths:
        print("- %s" % path)
    print("")
    print(json.dumps({"brief_count": len(briefs), "run_dir": str(run_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
