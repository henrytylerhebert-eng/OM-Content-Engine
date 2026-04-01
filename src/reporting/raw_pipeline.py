"""Run the local pipeline against CSV exports placed in data/raw."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Optional, Sequence

from src.review.reviewed_truth import DEFAULT_OVERRIDES_PATH
from src.reporting.demo_pipeline import REPO_ROOT, build_demo_bundle, write_demo_outputs


DEFAULT_INPUT_DIR = REPO_ROOT / "data" / "raw"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "processed" / "local_run"
DEFAULT_OVERRIDES_FILE = DEFAULT_OVERRIDES_PATH


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
) -> dict[str, object]:
    """Build a normalized bundle from CSV exports placed in data/raw."""

    source_paths = resolve_source_paths(input_dir)
    return build_demo_bundle(
        active_members_path=source_paths["active_members"],
        mentors_path=source_paths["mentors"],
        cohorts_path=source_paths.get("cohorts"),
        overrides_path=overrides_path,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the local raw-file pipeline and write processed outputs."""

    parser = argparse.ArgumentParser(description="Run the OM Content Engine pipeline against CSV files in data/raw.")
    parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_INPUT_DIR),
        help="Directory containing Active Members and Mentors CSV exports.",
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
    args = parser.parse_args(argv)

    bundle = build_local_bundle(
        Path(args.input_dir),
        overrides_path=Path(args.overrides) if args.overrides else None,
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
