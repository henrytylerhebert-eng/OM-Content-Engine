"""Minimal multi-company batch runner for phase-one portfolio processing."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Optional, Sequence

from src.portfolio.pipeline import (
    build_portfolio_snapshot_bundle_with_overrides,
    write_portfolio_snapshot_outputs,
)


def _slug(value: object) -> str:
    return "".join(char if char.isalnum() else "_" for char in str(value or "").strip().lower()).strip("_") or "record"


def discover_portfolio_batch_inputs(input_dir: Path) -> list[Path]:
    """Discover local company JSON input files for batch processing."""

    if not input_dir.exists():
        raise FileNotFoundError("Portfolio batch input directory does not exist: %s" % input_dir)

    input_files = sorted(path for path in input_dir.glob("*.json") if path.is_file())
    if not input_files:
        raise ValueError("No portfolio input JSON files were found in %s." % input_dir)
    return input_files


def resolve_batch_override_path(input_file: Path, overrides_dir: Optional[Path]) -> Optional[Path]:
    """Resolve the optional companion override file for one input file."""

    if overrides_dir is None or not overrides_dir.exists():
        return None

    candidate = overrides_dir / ("%s_overrides.json" % input_file.stem)
    if candidate.exists():
        return candidate
    return None


def run_portfolio_batch(
    input_files: Sequence[Path],
    *,
    output_dir: Path,
    overrides_dir: Optional[Path] = None,
) -> tuple[dict[str, object], dict[str, object], list[Path]]:
    """Run the existing one-company flow for multiple local company inputs."""

    if not input_files:
        raise ValueError("Portfolio batch processing requires at least one input file.")

    output_dir.mkdir(parents=True, exist_ok=True)

    company_runs: list[dict[str, object]] = []
    index_rows: list[dict[str, object]] = []
    written_paths: list[Path] = []

    for input_file in sorted(input_files):
        overrides_path = resolve_batch_override_path(input_file, overrides_dir)
        bundle = build_portfolio_snapshot_bundle_with_overrides(
            input_file,
            overrides_path=overrides_path,
        )
        company_output_dir = output_dir / _slug(input_file.stem)
        company_written_paths = write_portfolio_snapshot_outputs(bundle, company_output_dir)
        written_paths.extend(company_written_paths)

        snapshot = dict(bundle.get("portfolio_snapshot", {}))
        company_entry = {
            "input_file": str(input_file),
            "overrides_file": None if overrides_path is None else str(overrides_path),
            "output_dir": str(company_output_dir),
            "organization_id": snapshot.get("organization_id"),
            "report_period": snapshot.get("report_period"),
            "snapshot_id": snapshot.get("id"),
            "artifact_count": len(company_written_paths),
            "reviewed_truth_applied": "portfolio_reviewed_truth" in bundle,
            "founder_report_draft_status": snapshot.get("founder_report_draft_status"),
            "internal_report_draft_status": snapshot.get("internal_report_draft_status"),
            "portfolio_recommendation_draft_status": snapshot.get("portfolio_recommendation_draft_status"),
            "summary": {
                "reviewed_evidence_count": snapshot.get("reviewed_evidence_count", 0),
                "review_ready_domain_score_count": snapshot.get("review_ready_domain_score_count", 0),
                "capital_readiness_draft_count": snapshot.get("capital_readiness_draft_count", 0),
                "support_routing_draft_count": snapshot.get("support_routing_draft_count", 0),
                "milestone_draft_count": snapshot.get("milestone_draft_count", 0),
            },
        }
        company_runs.append(company_entry)
        index_rows.append(
            {
                "organization_id": snapshot.get("organization_id"),
                "report_period": snapshot.get("report_period"),
                "input_file": str(input_file),
                "output_dir": str(company_output_dir),
                "snapshot_file": str(company_output_dir / "portfolio_snapshot.json"),
                "reviewed_truth_applied": "portfolio_reviewed_truth" in bundle,
                "portfolio_recommendation_draft_status": snapshot.get("portfolio_recommendation_draft_status"),
            }
        )

    manifest = {
        "artifact_type": "portfolio_batch",
        "processed_at": datetime.utcnow().isoformat(),
        "company_count": len(company_runs),
        "input_count": len(input_files),
        "output_dir": str(output_dir),
        "companies": company_runs,
    }
    index = {
        "artifact_type": "portfolio_batch_index",
        "processed_at": manifest["processed_at"],
        "company_count": len(index_rows),
        "companies": index_rows,
    }

    manifest_path = output_dir / "portfolio_batch_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    written_paths.append(manifest_path)

    index_path = output_dir / "portfolio_batch_index.json"
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    written_paths.append(index_path)

    return manifest, index, written_paths
