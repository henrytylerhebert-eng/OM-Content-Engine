"""Run the local phase-one portfolio snapshot flow for multiple company JSON inputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from src.portfolio.batch import discover_portfolio_batch_inputs, run_portfolio_batch


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = REPO_ROOT / "data" / "raw" / "portfolio_example"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "processed" / "portfolio_batch_example"
DEFAULT_OVERRIDES_DIR = REPO_ROOT / "data" / "reviewed_truth"


def build_local_portfolio_batch(
    input_dir: Path = DEFAULT_INPUT_DIR,
    *,
    output_dir: Path,
    overrides_dir: Optional[Path] = DEFAULT_OVERRIDES_DIR,
) -> tuple[dict[str, object], dict[str, object], list[Path]]:
    """Run the batch portfolio flow against all JSON inputs in one local directory."""

    input_files = discover_portfolio_batch_inputs(input_dir)
    return run_portfolio_batch(
        input_files,
        output_dir=output_dir,
        overrides_dir=overrides_dir,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the multi-company portfolio batch flow and write a batch manifest."""

    parser = argparse.ArgumentParser(
        description="Run the phase-one portfolio snapshot flow for multiple local JSON company inputs."
    )
    parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_INPUT_DIR),
        help="Directory containing local company JSON input files.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where batch portfolio artifacts should be written.",
    )
    parser.add_argument(
        "--overrides-dir",
        default=str(DEFAULT_OVERRIDES_DIR),
        help="Optional directory containing companion override files named <input_stem>_overrides.json.",
    )
    args = parser.parse_args(argv)

    manifest, index, written_paths = build_local_portfolio_batch(
        Path(args.input_dir),
        output_dir=Path(args.output_dir),
        overrides_dir=Path(args.overrides_dir) if args.overrides_dir else None,
    )

    print("Wrote portfolio batch outputs:")
    for path in written_paths:
        print("- %s" % path)
    print("")
    print(json.dumps(manifest, indent=2))
    print("")
    print(json.dumps(index, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
