# OM Content Engine

OM Content Engine is a separate intelligence layer for Opportunity Machine.

It is designed to sit beside the current Airtable and spreadsheet workflow, not replace it. The job of this repo is to ingest operational exports, normalize messy records into clearer entities, and make it easier to support reporting, mentor matching, segmentation, and future content workflows.

## What This Repo Is

- A read-optimized ecosystem CRM and intelligence layer
- A one-way import pipeline from Airtable exports and synced CSVs
- A place to normalize people, organizations, programs, cohorts, participation, mentors, and interactions
- A foundation for future Codex, Canva, and Loomly outputs

## What This Repo Is Not

- Not the day-to-day operational source of truth
- Not a full staff CRM replacement
- Not a frontend application
- Not a bidirectional sync tool
- Not a place for premature workflow automation

## First-Pass Stack

- Python for ingestion, normalization, and reporting scripts
- SQLModel for readable schema definitions that can work with SQLite now and move to Postgres later
- CSV and Airtable export support from day one

## Operating Shape

The system is intentionally split into three layers:

1. Raw source layer: landed exports with traceable source metadata
2. Transformed layer: normalized domain records
3. Enrichment layer: derived tags, readiness signals, and segmentation helpers

The first phase is one-way only. Nothing in this repo should write back into the operational source.

## Repo Layout

```text
OM Content Engine/
  docs/
  src/
    config/
    ingest/
    review/
    transform/
    enrich/
    models/
    reporting/
  data/
    raw/
    processed/
    reviewed_truth/
  tests/
```

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .[dev]
pytest
```

## Developer Workflow

Set up the local environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .[dev]
```

Run the test suite:

```bash
python3 -m pytest
```

Run the demo normalization pipeline:

```bash
python3 -m src.reporting.demo_pipeline
```

Run the same pipeline against local CSV exports placed in `data/raw/`:

```bash
python3 -m src.reporting.raw_pipeline
```

Run the phase-one portfolio snapshot example against a local JSON input:

```bash
python3 -m src.reporting.portfolio_pipeline
```

The portfolio example also includes a tracked reviewed-truth file at `data/reviewed_truth/portfolio_example_overrides.json`.

Run the same phase-one portfolio flow for multiple local company inputs:

```bash
python3 -m src.reporting.portfolio_batch
```

Create or update one file-backed portfolio override rule safely:

```bash
python3 -m src.reporting.portfolio_override_tool --help
```

Write Airtable-aligned portfolio operational tables from the local example:

```bash
python3 -m src.reporting.portfolio_operational_export
```

Run the one-click weekly operator cycle against local CSV exports:

```bash
python3 -m src.reporting.weekly_run
```

Put landed `Active Members`, `Mentors`, and `Cohorts` CSV exports in `data/raw/`.

Optional reviewed-truth overrides live in `data/reviewed_truth/overrides.json`. Start from `data/reviewed_truth/overrides.example.json` if you need a local template.

Inspect generated demo and processed outputs in `data/processed/`.
The portfolio example input lives in `data/raw/portfolio_example/acme_phase_one.json`.
The runnable portfolio example writes JSON artifacts to `data/processed/portfolio_example/`.
That snapshot now includes a rules-based internal recommendation draft alongside the existing portfolio draft artifacts.

## Demo Pipeline

The repo includes a local demo pipeline that runs end to end against the safe synthetic sample exports in `tests/fixtures/`.

```bash
python3 -m src.reporting.demo_pipeline
```

This writes inspectable demo artifacts into `data/processed/demo/`:

- `normalized_bundle.json`
- `reviewed_truth.json`
- `review_flags.json`
- `content_intelligence.json`
- `reporting_snapshot.json`
- `ecosystem_summary.json`
- `ecosystem_report.md`

The demo uses only local files. It does not require Airtable access or any external service.

More detail: `docs/demo-pipeline.md`
Reviewed-truth model: `docs/reviewed-truth.md`
Portfolio reviewed-truth model: `docs/portfolio-reviewed-truth.md`
Portfolio override authoring helper: `docs/portfolio-override-authoring.md`
Portfolio recommendation rules: `docs/portfolio-recommendations.md`
Portfolio batching: `docs/portfolio-batching.md`
Portfolio Airtable contract: `docs/portfolio-airtable-contract.md`
Portfolio Airtable example mapping: `docs/portfolio-airtable-example.md`
Quick system map and examples: `docs/system-map.md`
Business definitions: `docs/business-definitions.md`
Operational snapshot pack: `docs/operational-snapshot.md`
Recurring owner checklist: `docs/owner-checklist.md`
Content candidate export: `docs/content-candidates.md`
Content brief export: `docs/content-briefs.md`
Editorial planning pack: `docs/editorial-planning.md`
Editorial assignment tracker: `docs/editorial-assignments.md`
Editorial assignment Airtable sync: `docs/editorial-assignments-sync.md`
Editorial operator runbook: `docs/editorial-operator-runbook.md`

## Current Scope

This scaffold covers:

- repo structure
- first-pass schema definitions
- starter ingest helpers
- starter normalization helpers
- starter enrichment helpers
- lightweight tests for messy source handling

It does not yet cover:

- UI
- auth
- scheduling
- bidirectional sync
- Canva integration
- Loomly integration

## Future Output Direction

The eventual goal is to expose clean, structured outputs that downstream tools can use without touching the raw Airtable layer:

- Canva-ready profile and storytelling records
- Loomly-ready audience segments and campaign exports
- Codex-friendly structured context for copy generation and reporting
