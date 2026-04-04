"""Run the weekly local operator cycle and print a compact summary."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Optional, Sequence

from src.reporting.demo_pipeline import SNAPSHOT_ARTIFACT_DESCRIPTIONS, write_demo_outputs
from src.reporting.raw_pipeline import (
    DEFAULT_ACTIVE_MEMBERS_TABLE,
    DEFAULT_COHORTS_TABLE,
    DEFAULT_INPUT_DIR,
    DEFAULT_MENTORS_TABLE,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_OVERRIDES_FILE,
    DEFAULT_SOURCE,
    build_local_bundle,
)


OUTPUT_OPEN_FIRST = [
    "snapshot_manifest.json",
    "editorial_plan.md",
    "editorial_assignments.md",
]


def _load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def verify_expected_outputs(run_dir: Path) -> list[Path]:
    """Ensure the standard snapshot outputs exist and are non-empty."""

    missing: list[str] = []
    empty: list[str] = []
    paths: list[Path] = []
    for file_name in SNAPSHOT_ARTIFACT_DESCRIPTIONS:
        path = run_dir / file_name
        if not path.exists():
            missing.append(file_name)
            continue
        if path.stat().st_size == 0:
            empty.append(file_name)
        paths.append(path)

    if missing or empty:
        message_parts: list[str] = []
        if missing:
            message_parts.append("missing=%s" % ", ".join(sorted(missing)))
        if empty:
            message_parts.append("empty=%s" % ", ".join(sorted(empty)))
        raise FileNotFoundError(
            "Weekly operator run did not produce the expected snapshot outputs in %s: %s"
            % (run_dir, " | ".join(message_parts))
        )
    return paths


def _collect_attention_items(assignments: list[dict[str, object]]) -> list[dict[str, str]]:
    """Return the top 3 assignments needing attention, blocking items first."""

    needs_review = [
        a for a in assignments if str(a.get("bucket", "")) == "needs_review"
    ]
    with_blockers = [
        a for a in needs_review if str(a.get("blocking_notes", "")).strip()
    ]
    without_blockers = [
        a for a in needs_review if not str(a.get("blocking_notes", "")).strip()
    ]
    ranked = with_blockers + without_blockers

    items: list[dict[str, str]] = []
    for a in ranked[:3]:
        person = str(a.get("primary_person_name") or "unknown")
        org = str(a.get("org_name") or "")
        label = "%s (%s)" % (person, org) if org else person
        next_step = str(a.get("next_step") or "")
        blocking = str(a.get("blocking_notes") or "")
        items.append({"label": label, "next_step": next_step, "blocking": blocking})
    return items


def build_weekly_run_summary(run_dir: Path) -> dict[str, object]:
    """Build the compact operator summary from the generated run outputs."""

    candidates = list(_load_json(run_dir / "content_candidates.json"))
    briefs = list(_load_json(run_dir / "content_briefs.json"))
    editorial_plan = dict(_load_json(run_dir / "editorial_plan.json"))
    assignments = list(_load_json(run_dir / "editorial_assignments.json"))

    bucket_counts = dict(editorial_plan.get("bucket_counts", {}))

    # Assignment status distribution.
    status_dist: dict[str, int] = {}
    for a in assignments:
        status = str(a.get("assignment_status") or "unknown")
        status_dist[status] = status_dist.get(status, 0) + 1

    # Airtable sync env-var readiness.
    has_token = bool(os.environ.get("AIRTABLE_TOKEN", "").strip())
    has_base_id = bool(os.environ.get("AIRTABLE_BASE_ID", "").strip())

    return {
        "output_dir": str(run_dir),
        "candidate_count": len(candidates),
        "brief_count": len(briefs),
        "use_now_count": int(bucket_counts.get("use_now", 0)),
        "needs_review_count": int(bucket_counts.get("needs_review", 0)),
        "hold_count": int(bucket_counts.get("hold", 0)),
        "assignment_count": len(assignments),
        "open_first": list(OUTPUT_OPEN_FIRST),
        "assignment_status_dist": status_dist,
        "attention_items": _collect_attention_items(assignments),
        "airtable_token_set": has_token,
        "airtable_base_id_set": has_base_id,
    }


def render_weekly_run_summary(summary: dict[str, object]) -> str:
    """Render the operator-facing summary printed after a weekly run."""

    lines = [
        "Weekly Operator Run Complete",
        "Output folder: %s" % summary.get("output_dir"),
        "Candidates: %s" % summary.get("candidate_count", 0),
        "Briefs: %s" % summary.get("brief_count", 0),
        "Use now: %s" % summary.get("use_now_count", 0),
        "Needs review: %s" % summary.get("needs_review_count", 0),
        "Hold: %s" % summary.get("hold_count", 0),
        "Assignments: %s" % summary.get("assignment_count", 0),
        "",
        "Open first:",
    ]
    lines.extend("- %s" % name for name in summary.get("open_first", []))

    # ── Operator Summary ──────────────────────────────────────────
    lines.append("")
    lines.append("─" * 52)
    lines.append("OPERATOR SUMMARY")
    lines.append("─" * 52)

    # Assignment status distribution.
    status_dist = dict(summary.get("assignment_status_dist", {}))
    if status_dist:
        lines.append("")
        lines.append("Assignment Status:")
        for status, count in sorted(status_dist.items()):
            lines.append("  %-20s %d" % (status, count))
    else:
        lines.append("")
        lines.append("Assignment Status: (none)")

    # Top items needing attention.
    attention = list(summary.get("attention_items", []))
    lines.append("")
    if attention:
        lines.append("Top Items Needing Attention:")
        for i, item in enumerate(attention, 1):
            label = item.get("label", "unknown")
            next_step = item.get("next_step", "")
            blocking = item.get("blocking", "")
            lines.append("  %d. %s" % (i, label))
            if next_step:
                lines.append("     Next step: %s" % next_step)
            if blocking:
                lines.append("     Blocking:  %s" % blocking)
    else:
        lines.append("Top Items Needing Attention: (none)")

    # Airtable sync readiness.
    token_ok = summary.get("airtable_token_set", False)
    base_ok = summary.get("airtable_base_id_set", False)
    lines.append("")
    if token_ok and base_ok:
        lines.append("Airtable Sync: READY (AIRTABLE_TOKEN and AIRTABLE_BASE_ID set)")
    else:
        missing = []
        if not token_ok:
            missing.append("AIRTABLE_TOKEN")
        if not base_ok:
            missing.append("AIRTABLE_BASE_ID")
        lines.append("Airtable Sync: NOT CONFIGURED (missing %s)" % ", ".join(missing))

    lines.append("─" * 52)
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the local weekly operator flow and print a compact summary."""

    parser = argparse.ArgumentParser(
        description="Run the local OM weekly operator cycle and print a compact summary.",
    )
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        choices=("csv", "airtable"),
        help="Source mode: landed CSV exports or live Airtable tables.",
    )
    parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_INPUT_DIR),
        help="Directory containing Active Members, Mentors, and optional Cohorts CSV exports when --source csv is used.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where the weekly snapshot bundle should be written.",
    )
    parser.add_argument(
        "--overrides",
        default=str(DEFAULT_OVERRIDES_FILE),
        help="Optional reviewed-truth JSON override file. Missing files are ignored.",
    )
    parser.add_argument(
        "--active-members-table",
        default=DEFAULT_ACTIVE_MEMBERS_TABLE,
        help="Airtable table name for Active Members when --source airtable is used.",
    )
    parser.add_argument(
        "--mentors-table",
        default=DEFAULT_MENTORS_TABLE,
        help="Airtable table name for Mentors when --source airtable is used.",
    )
    parser.add_argument(
        "--cohorts-table",
        default=DEFAULT_COHORTS_TABLE,
        help="Airtable table name for Cohorts when --source airtable is used.",
    )
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    bundle = build_local_bundle(
        Path(args.input_dir),
        overrides_path=Path(args.overrides) if args.overrides else None,
        source=args.source,
        active_members_table=args.active_members_table,
        mentors_table=args.mentors_table,
        cohorts_table=args.cohorts_table,
    )
    write_demo_outputs(bundle, output_dir)
    verify_expected_outputs(output_dir)
    print(render_weekly_run_summary(build_weekly_run_summary(output_dir)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
