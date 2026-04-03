"""Write Airtable-aligned operational export artifacts from the local portfolio example."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Sequence

from src.portfolio.airtable_contract import (
    build_portfolio_airtable_operational_export,
    write_portfolio_airtable_operational_exports,
)
from src.reporting.portfolio_pipeline import (
    DEFAULT_INPUT_FILE,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_OVERRIDES_FILE,
    build_local_portfolio_bundle,
)


DEFAULT_AIRTABLE_OUTPUT_DIR = DEFAULT_OUTPUT_DIR / "airtable_operational_export"


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Build a one-company operational export bundle and write Airtable-aligned JSON artifacts."""

    parser = argparse.ArgumentParser(
        description="Write Airtable-aligned operational export artifacts from a local portfolio input file."
    )
    parser.add_argument(
        "--input-file",
        default=str(DEFAULT_INPUT_FILE),
        help="Path to the local portfolio example JSON input file.",
    )
    parser.add_argument(
        "--overrides",
        default=str(DEFAULT_OVERRIDES_FILE),
        help="Optional portfolio reviewed-truth override JSON file. Missing files are ignored.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_AIRTABLE_OUTPUT_DIR),
        help="Directory where Airtable-aligned operational export artifacts should be written.",
    )
    args = parser.parse_args(argv)

    bundle = build_local_portfolio_bundle(
        Path(args.input_file),
        overrides_path=Path(args.overrides) if args.overrides else None,
    )
    export_bundle = build_portfolio_airtable_operational_export(bundle)
    written_paths = write_portfolio_airtable_operational_exports(export_bundle, Path(args.output_dir))

    print("Wrote Airtable-aligned operational export outputs:")
    for path in written_paths:
        print("- %s" % path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
