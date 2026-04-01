"""Tests for the local raw-data pipeline."""

from pathlib import Path
from shutil import copyfile

import pytest

from src.reporting.raw_pipeline import build_local_bundle, resolve_source_paths
from tests.fixtures.pilot_rows import fixture_path


def test_resolve_source_paths_finds_expected_exports(tmp_path: Path) -> None:
    copyfile(fixture_path("active_members.csv"), tmp_path / "Active Members.csv")
    copyfile(fixture_path("mentors.csv"), tmp_path / "Mentors.csv")
    copyfile(fixture_path("cohorts.csv"), tmp_path / "Cohorts.csv")

    paths = resolve_source_paths(tmp_path)

    assert paths["active_members"].name == "Active Members.csv"
    assert paths["mentors"].name == "Mentors.csv"
    assert paths["cohorts"].name == "Cohorts.csv"


def test_resolve_source_paths_accepts_airtable_export_style_names(tmp_path: Path) -> None:
    copyfile(fixture_path("active_members.csv"), tmp_path / "Active Members-Active Members.csv")
    copyfile(fixture_path("mentors.csv"), tmp_path / "Mentors-Grid view.csv")
    copyfile(fixture_path("cohorts.csv"), tmp_path / "Cohorts-Grid view.csv")

    paths = resolve_source_paths(tmp_path)

    assert paths["active_members"].name == "Active Members-Active Members.csv"
    assert paths["mentors"].name == "Mentors-Grid view.csv"
    assert paths["cohorts"].name == "Cohorts-Grid view.csv"


def test_build_local_bundle_uses_raw_directory_exports(tmp_path: Path) -> None:
    copyfile(fixture_path("active_members.csv"), tmp_path / "active_members.csv")
    copyfile(fixture_path("mentors.csv"), tmp_path / "mentors.csv")
    copyfile(fixture_path("cohorts.csv"), tmp_path / "cohorts.csv")

    bundle = build_local_bundle(tmp_path)

    assert bundle["raw_sources"]["active_members"]["row_count"] == 6
    assert bundle["raw_sources"]["mentors"]["row_count"] == 3
    assert bundle["raw_sources"]["cohorts"]["row_count"] == 4
    assert bundle["ecosystem_summary"]["organization_count"] == 6
    assert bundle["ecosystem_summary"]["participation_count"] == 4


def test_resolve_source_paths_raises_when_required_exports_are_missing(tmp_path: Path) -> None:
    copyfile(fixture_path("mentors.csv"), tmp_path / "mentors.csv")

    with pytest.raises(FileNotFoundError):
        resolve_source_paths(tmp_path)
