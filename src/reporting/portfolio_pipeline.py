"""Run the local phase-one portfolio snapshot pipeline against a JSON input file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from src.portfolio.pipeline import (
    build_portfolio_snapshot_bundle_with_overrides,
    write_portfolio_snapshot_outputs,
)
from src.portfolio.reviewed_truth import EXAMPLE_PORTFOLIO_OVERRIDES_PATH


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_FILE = REPO_ROOT / "data" / "raw" / "portfolio_example" / "acme_phase_one.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "processed" / "portfolio_example"
DEFAULT_OVERRIDES_FILE = EXAMPLE_PORTFOLIO_OVERRIDES_PATH


def build_local_portfolio_bundle(
    input_file: Path = DEFAULT_INPUT_FILE,
    overrides_path: Optional[Path] = DEFAULT_OVERRIDES_FILE,
) -> dict[str, object]:
    """Build a one-company portfolio snapshot bundle from a local JSON input file."""

    return build_portfolio_snapshot_bundle_with_overrides(input_file, overrides_path=overrides_path)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the local portfolio snapshot pipeline and write JSON artifacts."""

    parser = argparse.ArgumentParser(
        description="Run the phase-one portfolio snapshot pipeline against a local JSON input file."
    )
    parser.add_argument(
        "--input-file",
        default=str(DEFAULT_INPUT_FILE),
        help="Path to the local portfolio example JSON input file.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where portfolio snapshot artifacts should be written.",
    )
    parser.add_argument(
        "--overrides",
        default=str(DEFAULT_OVERRIDES_FILE),
        help="Optional portfolio reviewed-truth override JSON file. Missing files are ignored.",
    )
    args = parser.parse_args(argv)

    bundle = build_local_portfolio_bundle(
        Path(args.input_file),
        overrides_path=Path(args.overrides) if args.overrides else None,
    )
    written_paths = write_portfolio_snapshot_outputs(bundle, Path(args.output_dir))

    print("Wrote portfolio snapshot outputs:")
    for path in written_paths:
        print("- %s" % path)
    print("")
    print(json.dumps(bundle["portfolio_snapshot"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
