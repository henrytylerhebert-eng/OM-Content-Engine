"""Build a lightweight assignment tracker from the weekly editorial plan."""

from __future__ import annotations

import argparse
import csv
import io
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from src.reporting.content_briefs import (
    build_content_briefs,
    load_brief_inputs,
)
from src.reporting.editorial_plan import (
    OUTPUT_JSON_NAME as EDITORIAL_PLAN_JSON_NAME,
    build_plan,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_DIR = REPO_ROOT / "data" / "processed" / "local_run"
OUTPUT_JSON_NAME = "editorial_assignments.json"
OUTPUT_MARKDOWN_NAME = "editorial_assignments.md"
OUTPUT_CSV_NAME = "editorial_assignments.csv"

ALLOWED_STATUSES = {
    "unassigned",
    "not_started",
    "in_progress",
    "drafted",
    "approved_internal",
    "shipped",
    "dropped",
}
ALLOWED_PRIORITIES = {"high", "medium", "low"}
ALLOWED_TARGET_CYCLES = {"this_week", "next_week", "this_month", "backlog"}
REVIEW_NEXT_STEPS = {
    "confirm_person",
    "resolve_review_flag",
    "apply_reviewed_truth_override",
}


def _load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _utc_timestamp() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _slug(value: object) -> str:
    text = str(value or "").strip().lower()
    chars = [char if char.isalnum() else "_" for char in text]
    return "".join(chars).strip("_") or "record"


def _csv_text(rows: Sequence[dict[str, object]]) -> str:
    fieldnames = [
        "assignment_id",
        "entity_id",
        "org_name",
        "primary_person_name",
        "bucket",
        "brief_status",
        "readiness_level",
        "trust_basis",
        "public_ready",
        "suggested_angle",
        "suggested_format",
        "recommended_action",
        "owner",
        "target_cycle",
        "assignment_status",
        "priority",
        "blocking_notes",
        "next_step",
        "source_hook",
        "evidence_summary",
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({name: row.get(name, "") for name in fieldnames})
    return buffer.getvalue()


def load_editorial_plan(run_dir: Path = DEFAULT_RUN_DIR) -> dict[str, object]:
    """Load the editorial plan from an existing run directory."""

    path = run_dir / EDITORIAL_PLAN_JSON_NAME
    if path.exists():
        return dict(_load_json(path))

    snapshot = load_brief_inputs(run_dir)
    briefs = build_content_briefs(snapshot)
    return build_plan(briefs)


def _entries_with_bucket(plan: dict[str, object], *, include_hold: bool = False) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for bucket in ("use_now", "needs_review"):
        for entry in plan.get(bucket, []):
            row = dict(entry)
            row["bucket"] = bucket
            rows.append(row)
    if include_hold:
        for entry in plan.get("hold", []):
            row = dict(entry)
            row["bucket"] = "hold"
            rows.append(row)
    return rows


def _assignment_status(entry: dict[str, object], bucket: str) -> str:
    if bucket == "hold":
        return "dropped"
    return "not_started"


def _priority(entry: dict[str, object], bucket: str) -> str:
    if bucket == "use_now":
        return "high"
    if bucket == "needs_review":
        return "medium"
    return "low"


def _target_cycle(entry: dict[str, object], bucket: str) -> str:
    if bucket == "use_now":
        return "this_week"
    if bucket == "needs_review":
        return "next_week"
    return "backlog"


def _next_step(entry: dict[str, object], bucket: str) -> str:
    if bucket == "hold":
        return "hold"

    recommended_action = str(entry.get("recommended_action") or "").strip()
    unresolved = str(entry.get("unresolved_review_notes") or "").lower()
    if "review_missing_content_assets" in unresolved:
        return "gather_asset"
    if recommended_action in REVIEW_NEXT_STEPS:
        return recommended_action

    suggested_format = str(entry.get("suggested_format") or "").strip()
    if suggested_format == "mini_feature":
        return "draft_feature"
    return "draft_post"


def _blocking_notes(entry: dict[str, object], bucket: str) -> str:
    if bucket == "use_now":
        return ""
    unresolved = str(entry.get("unresolved_review_notes") or "").strip()
    if unresolved and not unresolved.startswith("No matched unresolved review flags"):
        return unresolved
    reason = str(entry.get("reason") or "").strip()
    if bucket == "hold":
        return reason
    return ""


def _assignment_id(entry: dict[str, object], bucket: str) -> str:
    return "assignment:%s:%s" % (bucket, _slug(entry.get("entity_id")))


def _source_hook(entry: dict[str, object]) -> str:
    return str(entry.get("top_hook") or entry.get("core_story") or "").strip()


def _sort_key(row: dict[str, object]) -> tuple[object, ...]:
    priority_order = {"high": 0, "medium": 1, "low": 2}
    cycle_order = {"this_week": 0, "next_week": 1, "this_month": 2, "backlog": 3}
    status_order = {
        "unassigned": 0,
        "not_started": 1,
        "in_progress": 2,
        "drafted": 3,
        "approved_internal": 4,
        "shipped": 5,
        "dropped": 6,
    }
    return (
        cycle_order.get(str(row.get("target_cycle") or "backlog"), 99),
        priority_order.get(str(row.get("priority") or "low"), 99),
        status_order.get(str(row.get("assignment_status") or "not_started"), 99),
        0 if str(row.get("primary_person_name") or "").strip() else 1,
        str(row.get("primary_person_name") or ""),
        str(row.get("org_name") or ""),
        str(row.get("assignment_id") or ""),
    )


def build_assignments(plan: dict[str, object], *, include_hold: bool = False) -> list[dict[str, object]]:
    """Build default assignment rows from the editorial plan."""

    assignments: list[dict[str, object]] = []
    for entry in _entries_with_bucket(plan, include_hold=include_hold):
        bucket = str(entry.get("bucket") or "")
        assignment = {
            "assignment_id": _assignment_id(entry, bucket),
            "entity_id": entry.get("entity_id"),
            "org_name": entry.get("org_name"),
            "primary_person_name": entry.get("primary_person_name"),
            "bucket": bucket,
            "brief_status": entry.get("brief_status"),
            "readiness_level": entry.get("readiness_level"),
            "trust_basis": entry.get("trust_basis"),
            "public_ready": entry.get("public_ready"),
            "suggested_angle": entry.get("suggested_angle"),
            "suggested_format": entry.get("suggested_format"),
            "recommended_action": entry.get("recommended_action"),
            "owner": "",
            "target_cycle": _target_cycle(entry, bucket),
            "assignment_status": _assignment_status(entry, bucket),
            "priority": _priority(entry, bucket),
            "blocking_notes": _blocking_notes(entry, bucket),
            "next_step": _next_step(entry, bucket),
            "source_hook": _source_hook(entry),
            "evidence_summary": entry.get("evidence_summary"),
        }
        assignments.append(assignment)
    return sorted(assignments, key=_sort_key)


def summarize_assignments(assignments: Sequence[dict[str, object]]) -> dict[str, object]:
    """Build compact status and cycle counts for the assignment pack."""

    status_counts = Counter(str(row.get("assignment_status") or "unassigned") for row in assignments)
    cycle_counts = Counter(str(row.get("target_cycle") or "backlog") for row in assignments)
    bucket_counts = Counter(str(row.get("bucket") or "needs_review") for row in assignments)
    review_work_count = sum(1 for row in assignments if str(row.get("next_step") or "") in REVIEW_NEXT_STEPS)
    return {
        "total_assignments": len(assignments),
        "status_counts": dict(status_counts),
        "target_cycle_counts": dict(cycle_counts),
        "bucket_counts": dict(bucket_counts),
        "review_work_count": review_work_count,
    }


def _entry_title(entry: dict[str, object]) -> str:
    primary_person = str(entry.get("primary_person_name") or "").strip()
    org_name = str(entry.get("org_name") or "").strip()
    if primary_person and org_name and primary_person != org_name:
        return "%s (%s)" % (primary_person, org_name)
    return primary_person or org_name or str(entry.get("entity_id") or "Record")


def _section_rows(assignments: Sequence[dict[str, object]], *cycles: str) -> list[dict[str, object]]:
    cycle_set = set(cycles)
    return [row for row in assignments if str(row.get("target_cycle") or "") in cycle_set]


def render_assignment_markdown(assignments: Sequence[dict[str, object]]) -> str:
    """Render the assignment tracker in a compact meeting-friendly markdown format."""

    summary = summarize_assignments(assignments)
    lines = [
        "# Editorial Assignments",
        "",
        "- Run date: `%s`" % _utc_timestamp(),
        "- Total assignments: `%s`" % summary["total_assignments"],
        "- Status counts: `%s`" % ", ".join(
            "%s=%s" % (key, value) for key, value in sorted(summary["status_counts"].items())
        ),
        "- Target cycles: `%s`" % ", ".join(
            "%s=%s" % (key, value) for key, value in sorted(summary["target_cycle_counts"].items())
        ),
        "",
    ]

    sections = [
        ("This Week", _section_rows(assignments, "this_week")),
        ("Next Week / This Month", _section_rows(assignments, "next_week", "this_month")),
        (
            "Review Work",
            [row for row in assignments if str(row.get("next_step") or "") in REVIEW_NEXT_STEPS],
        ),
        ("Backlog", _section_rows(assignments, "backlog")),
    ]

    for title, rows in sections:
        if title == "Backlog" and not rows:
            continue
        lines.append("## %s" % title)
        lines.append("")
        if not rows:
            lines.append("_No entries._")
            lines.append("")
            continue
        for row in rows:
            lines.append("### %s" % _entry_title(row))
            lines.append("")
            lines.append("- Owner: `%s`" % (row.get("owner") or "unassigned"))
            lines.append("- Format: `%s`" % row.get("suggested_format"))
            lines.append("- Priority: `%s`" % row.get("priority"))
            lines.append("- Next step: `%s`" % row.get("next_step"))
            lines.append("- Hook: %s" % row.get("source_hook"))
            blocking = str(row.get("blocking_notes") or "").strip()
            if blocking:
                lines.append("- Blocking note: %s" % blocking)
            lines.append("")
    return "\n".join(lines).strip() + "\n"


def write_assignment_outputs(assignments: Sequence[dict[str, object]], run_dir: Path) -> list[Path]:
    """Write assignment outputs into an existing run directory."""

    run_dir.mkdir(parents=True, exist_ok=True)
    written_paths: list[Path] = []

    json_path = run_dir / OUTPUT_JSON_NAME
    json_path.write_text(json.dumps(list(assignments), indent=2) + "\n", encoding="utf-8")
    written_paths.append(json_path)

    markdown_path = run_dir / OUTPUT_MARKDOWN_NAME
    markdown_path.write_text(render_assignment_markdown(assignments), encoding="utf-8")
    written_paths.append(markdown_path)

    csv_path = run_dir / OUTPUT_CSV_NAME
    csv_path.write_text(_csv_text(assignments), encoding="utf-8")
    written_paths.append(csv_path)

    return written_paths


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Build editorial assignments from the current editorial plan."""

    parser = argparse.ArgumentParser(description="Build editorial assignments from an editorial plan.")
    parser.add_argument(
        "--run-dir",
        default=str(DEFAULT_RUN_DIR),
        help="Run directory containing editorial_plan.json or the upstream plan inputs.",
    )
    parser.add_argument(
        "--include-hold",
        action="store_true",
        help="Include hold items in the default assignment output as low-priority backlog rows.",
    )
    args = parser.parse_args(argv)

    run_dir = Path(args.run_dir)
    plan = load_editorial_plan(run_dir)
    assignments = build_assignments(plan, include_hold=args.include_hold)
    written_paths = write_assignment_outputs(assignments, run_dir)

    print("Wrote editorial assignment outputs:")
    for path in written_paths:
        print("- %s" % path)
    print("")
    print(json.dumps(summarize_assignments(assignments), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
