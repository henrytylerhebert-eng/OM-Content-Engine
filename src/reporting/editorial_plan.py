"""Build a compact weekly editorial planning pack from internal content briefs."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from src.reporting.content_briefs import (
    OUTPUT_JSON_NAME as CONTENT_BRIEFS_JSON_NAME,
    build_content_briefs,
    load_brief_inputs,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_DIR = REPO_ROOT / "data" / "processed" / "local_run"
OUTPUT_JSON_NAME = "editorial_plan.json"
OUTPUT_MARKDOWN_NAME = "editorial_plan.md"

BUCKET_ORDER = ["use_now", "needs_review", "hold"]
TRUST_STRENGTH_ORDER = {
    "human_approved": 0,
    "reviewed_truth_backed": 1,
    "heuristic_only": 2,
}
READINESS_LEVEL_ORDER = {
    "externally_publishable": 0,
    "spotlight_ready": 1,
    "content_ready": 2,
    "internally_usable": 3,
    "below_internal": 4,
}
BLOCKING_REVIEW_CODES = {
    "review_personnel_parse",
    "review_grouped_record_detected",
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


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "active"}


def _load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _utc_timestamp() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _normalized_text(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def load_briefs(run_dir: Path = DEFAULT_RUN_DIR) -> list[dict[str, object]]:
    """Load content briefs from an existing run directory."""

    path = run_dir / CONTENT_BRIEFS_JSON_NAME
    if path.exists():
        return list(_load_json(path))

    snapshot = load_brief_inputs(run_dir)
    return build_content_briefs(snapshot)


def _has_unresolved_review_notes(brief: dict[str, object]) -> bool:
    notes = _normalized_text(brief.get("unresolved_review_notes"))
    if not notes:
        return False
    return not notes.startswith("no matched unresolved review flags")


def _matched_blocking_codes(brief: dict[str, object]) -> list[str]:
    notes = _normalized_text(brief.get("unresolved_review_notes"))
    return [code for code in BLOCKING_REVIEW_CODES if code in notes]


def _has_blocking_review_burden(brief: dict[str, object]) -> bool:
    return bool(_matched_blocking_codes(brief))


def _weak_org_only_signal(brief: dict[str, object]) -> bool:
    if str(brief.get("primary_person_name") or "").strip():
        return False
    if list(brief.get("program_names") or []):
        return False
    if str(brief.get("readiness_level") or "") == "spotlight_ready":
        return False
    if str(brief.get("trust_basis") or "") != "heuristic_only":
        return False
    return True


def _top_hook(brief: dict[str, object]) -> str:
    hooks = list(brief.get("hook_options") or [])
    return str(hooks[0]) if hooks else str(brief.get("core_story") or "")


def _recommended_action(bucket: str, brief: dict[str, object]) -> str:
    if bucket == "use_now":
        if str(brief.get("brief_status") or "") == "public_ready":
            return "draft_this"
        return "assign_owner"
    if bucket == "needs_review":
        if not str(brief.get("primary_person_name") or "").strip():
            return "confirm_person"
        if _has_unresolved_review_notes(brief):
            return "resolve_review_flag"
        return "apply_reviewed_truth_override"
    if _has_blocking_review_burden(brief):
        return "requires_structural_fix"
    if _weak_org_only_signal(brief):
        return "wait_for_signal"
    return "defer"


def _reason(bucket: str, brief: dict[str, object]) -> str:
    if bucket == "use_now":
        if str(brief.get("brief_status") or "") == "public_ready":
            return "reviewed truth confirmed, strong evidence"
        return "reviewed for internal use with no blocking review burden"
    if bucket == "needs_review":
        if not str(brief.get("primary_person_name") or "").strip():
            return "missing person attribution"
        if _has_unresolved_review_notes(brief):
            return "fixable review burden remains"
        return "planning-safe but still heuristic"
    if _weak_org_only_signal(brief):
        return "weak signal, organization-only"
    if _has_blocking_review_burden(brief):
        return "unresolved review burden still blocks drafting"
    return "trust is still too weak for this cycle"


def _resolution_note(entry: dict[str, object]) -> str:
    action = str(entry.get("recommended_action") or "")
    notes = str(entry.get("unresolved_review_notes") or "").strip()
    if action == "confirm_person":
        return "Confirm a real named person or spokesperson before drafting."
    if action == "apply_reviewed_truth_override":
        return "Apply a reviewed-truth decision if staff wants this in the active queue."
    if action == "resolve_review_flag":
        if notes:
            return notes
        return "Resolve the remaining review flag before drafting."
    if action == "requires_structural_fix":
        return "Clean up the source or reviewed-truth issue before this returns to planning."
    if action == "wait_for_signal":
        return "Wait for a stronger person-linked or participation-linked signal."
    if action == "defer":
        return "Defer until the trust picture improves."
    return "Assign an owner and move into drafting."


def classify_brief(brief: dict[str, object]) -> str:
    """Classify a brief into one weekly planning bucket."""

    brief_status = str(brief.get("brief_status") or "")
    trust_basis = str(brief.get("trust_basis") or "heuristic_only")
    blocking_review = _has_blocking_review_burden(brief)

    if brief_status == "public_ready":
        return "use_now"
    if brief_status == "reviewed_for_internal_use" and trust_basis in {
        "reviewed_truth_backed",
        "human_approved",
    } and not blocking_review:
        return "use_now"
    if brief_status == "hold_for_review" or blocking_review or _weak_org_only_signal(brief):
        return "hold"
    return "needs_review"


def _plan_entry(brief: dict[str, object], bucket: str) -> dict[str, object]:
    return {
        "entity_id": brief.get("entity_id"),
        "org_name": brief.get("org_name"),
        "primary_person_name": brief.get("primary_person_name"),
        "brief_status": brief.get("brief_status"),
        "readiness_level": brief.get("readiness_level"),
        "trust_basis": brief.get("trust_basis"),
        "reviewed_truth_applied": brief.get("reviewed_truth_applied"),
        "public_ready": brief.get("public_ready"),
        "core_story": brief.get("core_story"),
        "recommended_action": _recommended_action(bucket, brief),
        "reason": _reason(bucket, brief),
        "suggested_angle": brief.get("suggested_angle"),
        "suggested_format": brief.get("suggested_format"),
        "top_hook": _top_hook(brief),
        "guardrails": list(brief.get("guardrails") or []),
        "evidence_summary": brief.get("evidence_summary"),
        "unresolved_review_notes": brief.get("unresolved_review_notes"),
    }


def _sort_key(entry: dict[str, object]) -> tuple[object, ...]:
    return (
        TRUST_STRENGTH_ORDER.get(str(entry.get("trust_basis") or "heuristic_only"), 99),
        READINESS_LEVEL_ORDER.get(str(entry.get("readiness_level") or "below_internal"), 99),
        0 if str(entry.get("primary_person_name") or "").strip() else 1,
        str(entry.get("primary_person_name") or ""),
        str(entry.get("org_name") or ""),
        str(entry.get("entity_id") or ""),
    )


def build_plan(briefs: Sequence[dict[str, object]]) -> dict[str, object]:
    """Build the weekly editorial planning pack from content briefs."""

    brief_rows = [dict(brief) for brief in briefs]
    buckets = {name: [] for name in BUCKET_ORDER}
    for brief in brief_rows:
        bucket = classify_brief(brief)
        buckets[bucket].append(_plan_entry(brief, bucket))

    for bucket_name in BUCKET_ORDER:
        buckets[bucket_name] = sorted(buckets[bucket_name], key=_sort_key)

    return {
        "generated_at": _utc_timestamp(),
        "total_candidates": len(brief_rows),
        "bucket_counts": {name: len(buckets[name]) for name in BUCKET_ORDER},
        "use_now": buckets["use_now"],
        "needs_review": buckets["needs_review"],
        "hold": buckets["hold"],
    }


def _entry_title(entry: dict[str, object]) -> str:
    primary_person = str(entry.get("primary_person_name") or "").strip()
    org_name = str(entry.get("org_name") or "").strip()
    if primary_person and org_name and primary_person != org_name:
        return "%s (%s)" % (primary_person, org_name)
    return primary_person or org_name or str(entry.get("entity_id") or "Record")


def _short_guardrails(entry: dict[str, object]) -> str:
    items = list(entry.get("guardrails") or [])
    if not items:
        return "No extra guardrails recorded."
    return " | ".join(str(item) for item in items[:2])


def render_markdown_plan(plan: dict[str, object]) -> str:
    """Render the editorial plan as a compact meeting-friendly markdown pack."""

    lines = [
        "# Weekly Editorial Plan",
        "",
        "- Run date: `%s`" % plan.get("generated_at"),
        "- Total candidates: `%s`" % plan.get("total_candidates"),
        "- Use now: `%s`" % plan.get("bucket_counts", {}).get("use_now", 0),
        "- Needs review: `%s`" % plan.get("bucket_counts", {}).get("needs_review", 0),
        "- Hold: `%s`" % plan.get("bucket_counts", {}).get("hold", 0),
        "",
    ]

    sections = [
        ("use_now", "Use Now"),
        ("needs_review", "Needs Review"),
        ("hold", "Hold"),
    ]
    for key, title in sections:
        lines.append("## %s" % title)
        lines.append("")
        rows = list(plan.get(key) or [])
        if not rows:
            lines.append("_No entries._")
            lines.append("")
            continue
        for entry in rows:
            lines.append("### %s" % _entry_title(entry))
            lines.append("")
            if key == "use_now":
                lines.append("- Story: %s" % entry.get("core_story"))
                lines.append("- Suggested format: `%s`" % entry.get("suggested_format"))
                lines.append("- Top hook: %s" % entry.get("top_hook"))
                lines.append("- Guardrails: %s" % _short_guardrails(entry))
                lines.append("- Action: `%s`" % entry.get("recommended_action"))
            elif key == "needs_review":
                lines.append("- Issue: %s" % entry.get("reason"))
                lines.append("- What needs to be resolved: %s" % _resolution_note(entry))
                lines.append("- Suggested angle: `%s`" % entry.get("suggested_angle"))
                lines.append("- Action: `%s`" % entry.get("recommended_action"))
            else:
                lines.append("- Why held: %s" % entry.get("reason"))
                lines.append("- What would unlock it: %s" % _resolution_note(entry))
                lines.append("- Suggested angle: `%s`" % entry.get("suggested_angle"))
                lines.append("- Action: `%s`" % entry.get("recommended_action"))
            lines.append("")
    return "\n".join(lines).strip() + "\n"


def write_outputs(plan: dict[str, object], run_dir: Path) -> list[Path]:
    """Write the editorial plan pack into an existing run directory."""

    run_dir.mkdir(parents=True, exist_ok=True)
    written_paths: list[Path] = []

    json_path = run_dir / OUTPUT_JSON_NAME
    json_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    written_paths.append(json_path)

    markdown_path = run_dir / OUTPUT_MARKDOWN_NAME
    markdown_path.write_text(render_markdown_plan(plan), encoding="utf-8")
    written_paths.append(markdown_path)
    return written_paths


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Build a weekly editorial plan from an existing pipeline run."""

    parser = argparse.ArgumentParser(description="Build the weekly editorial planning pack from content briefs.")
    parser.add_argument(
        "--run-dir",
        default=str(DEFAULT_RUN_DIR),
        help="Run directory containing content_briefs.json or the upstream snapshot files.",
    )
    args = parser.parse_args(argv)

    run_dir = Path(args.run_dir)
    briefs = load_briefs(run_dir)
    plan = build_plan(briefs)
    written_paths = write_outputs(plan, run_dir)

    print("Wrote editorial planning outputs:")
    for path in written_paths:
        print("- %s" % path)
    print("")
    print(json.dumps(plan.get("bucket_counts", {}), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
