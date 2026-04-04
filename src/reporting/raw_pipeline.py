"""Run the local pipeline against landed CSV exports or live Airtable tables."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Optional, Sequence

from src.ingest.airtable_live import (
    DEFAULT_ACTIVE_MEMBERS_TABLE,
    DEFAULT_COHORTS_TABLE,
    DEFAULT_MENTORS_TABLE,
    AirtableReadConfig,
    AirtableReadClient,
    load_airtable_live_records,
)
from src.review.reviewed_truth import DEFAULT_OVERRIDES_PATH
from src.reporting.demo_pipeline import REPO_ROOT, build_bundle_from_raw_records, build_demo_bundle, write_demo_outputs


DEFAULT_INPUT_DIR = REPO_ROOT / "data" / "raw"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "processed" / "local_run"
DEFAULT_OVERRIDES_FILE = DEFAULT_OVERRIDES_PATH
DEFAULT_SOURCE = "csv"


def _normalize_name(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


def resolve_source_paths(input_dir: Path) -> dict[str, Path]:
    """Find the pilot export files in a local raw-data directory."""

    discovered: dict[str, Path] = {}
    for path in input_dir.glob("*.csv"):
        normalized = _normalize_name(path.stem)
        if "activemembers" in normalized:
            discovered["active_members"] = path
        elif "mentors" in normalized or normalized == "mentor":
            discovered["mentors"] = path
        elif "cohorts" in normalized or "cohortsgridview" in normalized:
            discovered["cohorts"] = path

    missing = [key for key in ("active_members", "mentors") if key not in discovered]
    if missing:
        raise FileNotFoundError(
            "Missing required raw source files in %s. Expected CSV files matching Active Members and Mentors."
            % input_dir
        )
    return discovered


def build_local_bundle(
    input_dir: Path = DEFAULT_INPUT_DIR,
    overrides_path: Optional[Path] = DEFAULT_OVERRIDES_FILE,
    *,
    source: str = DEFAULT_SOURCE,
    active_members_table: str = DEFAULT_ACTIVE_MEMBERS_TABLE,
    mentors_table: str = DEFAULT_MENTORS_TABLE,
    cohorts_table: str = DEFAULT_COHORTS_TABLE,
) -> dict[str, object]:
    """Build a normalized bundle from either landed CSV exports or live Airtable tables."""

    if source == "airtable":
        config = AirtableReadConfig.from_env()
        client = AirtableReadClient(config)
        raw_active_members = load_airtable_live_records(
            client,
            table_name=active_members_table,
            required=True,
        )
        raw_mentors = load_airtable_live_records(
            client,
            table_name=mentors_table,
            required=True,
        )
        raw_cohorts = load_airtable_live_records(
            client,
            table_name=cohorts_table,
            required=False,
        )
        return build_bundle_from_raw_records(
            raw_active_members=raw_active_members,
            raw_mentors=raw_mentors,
            raw_cohorts=raw_cohorts,
            overrides_path=overrides_path,
            raw_sources={
                "active_members": {
                    "file_path": "airtable://%s/%s" % (config.base_id, active_members_table),
                    "row_count": len(raw_active_members),
                },
                "mentors": {
                    "file_path": "airtable://%s/%s" % (config.base_id, mentors_table),
                    "row_count": len(raw_mentors),
                },
                "cohorts": {
                    "file_path": "airtable://%s/%s" % (config.base_id, cohorts_table),
                    "row_count": len(raw_cohorts),
                },
            },
        )

    if source != "csv":
        raise ValueError("Unsupported source %s. Expected 'csv' or 'airtable'." % source)

    source_paths = resolve_source_paths(input_dir)
    return build_demo_bundle(
        active_members_path=source_paths["active_members"],
        mentors_path=source_paths["mentors"],
        cohorts_path=source_paths.get("cohorts"),
        overrides_path=overrides_path,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the local raw-file pipeline and write processed outputs."""

    parser = argparse.ArgumentParser(
        description="Run the OM Content Engine pipeline against landed CSV files or live Airtable tables."
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
        help="Directory containing Active Members and Mentors CSV exports when --source csv is used.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where processed outputs should be written.",
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

    bundle = build_local_bundle(
        Path(args.input_dir),
        overrides_path=Path(args.overrides) if args.overrides else None,
        source=args.source,
        active_members_table=args.active_members_table,
        mentors_table=args.mentors_table,
        cohorts_table=args.cohorts_table,
    )
    written_paths = write_demo_outputs(bundle, Path(args.output_dir))

    print("Wrote local pipeline outputs:")
    for path in written_paths:
        print("- %s" % path)
    print("")
    print(json.dumps(bundle["ecosystem_summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
