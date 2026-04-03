"""Tests for minimal multi-company portfolio batching."""

import json
from pathlib import Path

from src.portfolio.batch import discover_portfolio_batch_inputs, resolve_batch_override_path, run_portfolio_batch
from src.reporting.portfolio_batch import build_local_portfolio_batch, main


REPO_ROOT = Path(__file__).resolve().parents[1]
BATCH_INPUT_DIR = REPO_ROOT / "data" / "raw" / "portfolio_example"
OVERRIDES_DIR = REPO_ROOT / "data" / "reviewed_truth"


def test_discover_portfolio_batch_inputs_finds_multiple_company_files() -> None:
    input_files = discover_portfolio_batch_inputs(BATCH_INPUT_DIR)

    assert [path.name for path in input_files] == [
        "acme_phase_one.json",
        "brightpath_phase_one.json",
    ]


def test_resolve_batch_override_path_uses_companion_file_when_present() -> None:
    override_path = resolve_batch_override_path(
        BATCH_INPUT_DIR / "acme_phase_one.json",
        OVERRIDES_DIR,
    )

    assert override_path == OVERRIDES_DIR / "acme_phase_one_overrides.json"


def test_run_portfolio_batch_writes_company_outputs_and_batch_index(tmp_path: Path) -> None:
    manifest, index, written_paths = run_portfolio_batch(
        discover_portfolio_batch_inputs(BATCH_INPUT_DIR),
        output_dir=tmp_path,
        overrides_dir=OVERRIDES_DIR,
    )

    assert manifest["artifact_type"] == "portfolio_batch"
    assert manifest["company_count"] == 2
    assert index["artifact_type"] == "portfolio_batch_index"
    assert index["company_count"] == 2
    assert (tmp_path / "portfolio_batch_manifest.json").exists()
    assert (tmp_path / "portfolio_batch_index.json").exists()
    assert (tmp_path / "acme_phase_one" / "portfolio_snapshot.json").exists()
    assert (tmp_path / "brightpath_phase_one" / "portfolio_snapshot.json").exists()
    assert any(path.name == "portfolio_batch_manifest.json" for path in written_paths)

    acme_entry = next(item for item in manifest["companies"] if item["organization_id"] == "org:acme_automation")
    brightpath_entry = next(item for item in manifest["companies"] if item["organization_id"] == "org:brightpath_health")

    assert acme_entry["reviewed_truth_applied"] is True
    assert acme_entry["overrides_file"].endswith("acme_phase_one_overrides.json")
    assert brightpath_entry["reviewed_truth_applied"] is False
    assert brightpath_entry["overrides_file"] is None

    batch_index = json.loads((tmp_path / "portfolio_batch_index.json").read_text(encoding="utf-8"))
    assert batch_index["company_count"] == 2
    assert any(item["organization_id"] == "org:brightpath_health" for item in batch_index["companies"])


def test_portfolio_batch_main_writes_default_style_outputs(tmp_path: Path) -> None:
    exit_code = main(
        [
            "--input-dir",
            str(BATCH_INPUT_DIR),
            "--overrides-dir",
            str(OVERRIDES_DIR),
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert (tmp_path / "portfolio_batch_manifest.json").exists()
    assert (tmp_path / "portfolio_batch_index.json").exists()


def test_build_local_portfolio_batch_uses_existing_single_company_flow(tmp_path: Path) -> None:
    manifest, _, _ = build_local_portfolio_batch(
        BATCH_INPUT_DIR,
        output_dir=tmp_path,
        overrides_dir=OVERRIDES_DIR,
    )

    assert manifest["company_count"] == 2
    assert all(company["portfolio_recommendation_draft_status"] == "draft" for company in manifest["companies"])
