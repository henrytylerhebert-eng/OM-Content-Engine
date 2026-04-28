# Reporting Layer

The reporting layer should consume normalized and enriched data, not raw source exports.

In Phase 1, these scripts are simple helpers for counts, summaries, and export-friendly views.

Current reporting outputs support:

- total active organizations by type
- total active people by type
- total active mentors, local and non-local
- organizations by cohort
- organizations by membership tier where available
- internally usable organizations
- internally usable people
- organizations with content-ready profiles
- people with content-ready profiles
- spotlight-ready organizations
- spotlight-ready people
- externally publishable records
- internal content candidate exports
- internal content brief packs
- weekly editorial planning packs
- weekly editorial assignment trackers
- missing-content-asset counts
- records requiring review

The main entry points are:

- `src/reporting/ecosystem_reports.py`
- `src/reporting/content_summary.py`

For a full local sample-data run, use `src/reporting/demo_pipeline.py`.

Example command:

```bash
python3 -m src.reporting.ecosystem_reports --input data/processed/reporting_input.json --format markdown
```

For CSV output, pass a section name:

```bash
python3 -m src.reporting.ecosystem_reports --input data/processed/reporting_input.json --format csv --section active_organizations_by_type
```

Sample-data demo command:

```bash
python3 -m src.reporting.demo_pipeline
```

Local raw-data command:

```bash
python3 -m src.reporting.raw_pipeline
```

Local portfolio snapshot example command:

```bash
python3 -m src.reporting.portfolio_pipeline
```

That command reads `data/raw/portfolio_example/acme_phase_one.json` by default and writes JSON artifacts to `data/processed/portfolio_example/`.
It also applies `data/reviewed_truth/portfolio_example_overrides.json` by default so reviewed evidence and durable internal decisions can survive reruns.
It now also writes `portfolio_recommendation_draft.json`, which is a rules-based internal recommendation summary and remains draft-only.

Local multi-company portfolio batch command:

```bash
python3 -m src.reporting.portfolio_batch
```

That command reuses the one-company portfolio flow for every JSON file in the input directory, writes one subdirectory per company, and produces `portfolio_batch_manifest.json` plus `portfolio_batch_index.json`.

Operator-safe portfolio override authoring command:

```bash
python3 -m src.reporting.portfolio_override_tool --help
```

That helper creates or updates one validated file-backed override rule at a time and keeps raw inputs separate from reviewed-truth decisions.

Airtable-aligned operational export command:

```bash
python3 -m src.reporting.portfolio_operational_export
```

That command writes one-company JSON tables for `Companies`, `Evidence Items`, `Assumptions`, `Domain Scores`, `Capital Readiness`, `Support Routing`, `Action Items`, and `Milestones`.
It also writes `airtable_operational_example_summary.json` so the example table grouping is easy to inspect.

One-click weekly operator command:

```bash
python3 -m src.reporting.weekly_run
```

On-demand live Airtable weekly run:

```bash
python3 -m src.reporting.weekly_run --source airtable
```

Both pipeline entry points write the standard operational snapshot pack, including `snapshot_manifest.json` as a short index for the run.
The portfolio snapshot entry point writes a smaller JSON-only artifact pack for one company and keeps all outputs internal/founder draft-oriented.

The same run also writes `content_candidates.json` and `content_candidates.csv` for internal planning use.
It also writes `content_briefs.json` and `content_briefs.md` for internal drafting and review.
It also writes `editorial_plan.json` and `editorial_plan.md` for weekly planning and owner assignment.
It also writes `editorial_assignments.json`, `editorial_assignments.md`, and `editorial_assignments.csv` for weekly execution tracking.
It also writes `weekly_export_summary.md` for a fast weekly roll-up of use-now counts, review workload, and assignment status.

For shared team visibility without moving source-of-truth logic out of the repo, use:

```bash
python3 -m src.reporting.editorial_assignments_airtable_sync
```

That sync is one-way, upserts by `assignment_id`, protects manual Airtable edits by default, and logs each run to `Data Source Sync Logs`.
