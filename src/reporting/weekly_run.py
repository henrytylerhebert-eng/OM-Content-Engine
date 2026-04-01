"""Run the weekly local operator cycle and print a compact summary."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path
from typing import Optional, Sequence

from src.reporting.demo_pipeline import SNAPSHOT_ARTIFACT_DESCRIPTIONS, write_demo_outputs
from src.reporting.editorial_assignments_airtable_sync import (
    DEFAULT_EDITORIAL_ASSIGNMENTS_TABLE,
    DEFAULT_SYNC_LOGS_TABLE,
)
from src.reporting.raw_pipeline import (
    DEFAULT_INPUT_DIR,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_OVERRIDES_FILE,
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


def _story_label(assignment: dict[str, object]) -> str:
    person = str(assignment.get("primary_person_name") or "").strip()
    org = str(assignment.get("org_name") or "").strip()
    if person and org:
        return "%s (%s)" % (person, org)
    if person:
        return person
    if org:
        return org
    return str(assignment.get("entity_id") or "unknown")


def _duplicate_story_labels(assignments: list[dict[str, object]]) -> list[str]:
    labels = [
        _story_label(assignment)
        for assignment in assignments
        if str(assignment.get("primary_person_name") or "").strip()
        or str(assignment.get("org_name") or "").strip()
    ]
    counts = Counter(labels)
    duplicates = [
        "%s x%d" % (label, count)
        for label, count in sorted(counts.items())
        if count > 1
    ]
    return duplicates[:3]


def build_weekly_run_summary(run_dir: Path) -> dict[str, object]:
    """Build the compact operator summary from the generated run outputs."""

    candidates = list(_load_json(run_dir / "content_candidates.json"))
    briefs = list(_load_json(run_dir / "content_briefs.json"))
    editorial_plan = dict(_load_json(run_dir / "editorial_plan.json"))
    assignments = list(_load_json(run_dir / "editorial_assignments.json"))

    bucket_counts = dict(editorial_plan.get("bucket_counts", {}))
    has_token = bool(os.environ.get("AIRTABLE_TOKEN", "").strip())
    has_base_id = bool(os.environ.get("AIRTABLE_BASE_ID", "").strip())
    missing_env = []
    if not has_token:
        missing_env.append("AIRTABLE_TOKEN")
    if not has_base_id:
        missing_env.append("AIRTABLE_BASE_ID")

    return {
        "output_dir": str(run_dir),
        "candidate_count": len(candidates),
        "brief_count": len(briefs),
        "use_now_count": int(bucket_counts.get("use_now", 0)),
        "needs_review_count": int(bucket_counts.get("needs_review", 0)),
        "hold_count": int(bucket_counts.get("hold", 0)),
        "assignment_count": len(assignments),
        "open_first": list(OUTPUT_OPEN_FIRST),
        "duplicate_story_labels": _duplicate_story_labels(assignments),
        "airtable_ready": has_token and has_base_id,
        "airtable_missing_env": missing_env,
        "airtable_base_id": os.environ.get("AIRTABLE_BASE_ID", "").strip(),
        "airtable_editorial_table": os.environ.get(
            "AIRTABLE_EDITORIAL_ASSIGNMENTS_TABLE",
            DEFAULT_EDITORIAL_ASSIGNMENTS_TABLE,
        ).strip()
        or DEFAULT_EDITORIAL_ASSIGNMENTS_TABLE,
        "airtable_sync_logs_table": os.environ.get(
            "AIRTABLE_SYNC_LOGS_TABLE",
            DEFAULT_SYNC_LOGS_TABLE,
        ).strip()
        or DEFAULT_SYNC_LOGS_TABLE,
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

    notes: list[str] = []
    if int(summary.get("use_now_count", 0)) == 0:
        notes.append(
            "No use_now items. Start with needs_review in editorial_plan.md, resolve the top review blocker, and assign 1-3 rows in editorial_assignments.md before drafting."
        )

    duplicates = list(summary.get("duplicate_story_labels", []))
    if duplicates:
        notes.append(
            "Duplicate-looking story rows: %s. This usually means separate org/person records are pointing at the same story lane."
            % ", ".join(duplicates)
        )

    lines.append("")
    if notes:
        lines.append("Operator Notes:")
        lines.extend("- %s" % note for note in notes)
    else:
        lines.append("Operator Notes:")
        lines.append("- No immediate operator warnings.")

    lines.append("")
    if summary.get("airtable_ready"):
        lines.append(
            "Airtable Sync: READY (base %s, tables: %s / %s)"
            % (
                summary.get("airtable_base_id", ""),
                summary.get("airtable_editorial_table", DEFAULT_EDITORIAL_ASSIGNMENTS_TABLE),
                summary.get("airtable_sync_logs_table", DEFAULT_SYNC_LOGS_TABLE),
            )
        )
    else:
        lines.append(
            "Airtable Sync: NOT CONFIGURED (missing %s)"
            % ", ".join(summary.get("airtable_missing_env", []))
        )
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the local weekly operator flow and print a compact summary."""

    parser = argparse.ArgumentParser(
        description="Run the local OM weekly operator cycle and print a compact summary.",
    )
    parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_INPUT_DIR),
        help="Directory containing Active Members, Mentors, and optional Cohorts CSV exports.",
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
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    bundle = build_local_bundle(
        Path(args.input_dir),
        overrides_path=Path(args.overrides) if args.overrides else None,
    )
    write_demo_outputs(bundle, output_dir)
    verify_expected_outputs(output_dir)
    print(render_weekly_run_summary(build_weekly_run_summary(output_dir)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
