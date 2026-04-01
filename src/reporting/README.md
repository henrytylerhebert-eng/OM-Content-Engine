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

One-click weekly operator command:

```bash
python3 -m src.reporting.weekly_run
```

Both pipeline entry points write the standard operational snapshot pack, including `snapshot_manifest.json` as a short index for the run.

The same run also writes `content_candidates.json` and `content_candidates.csv` for internal planning use.
It also writes `content_briefs.json` and `content_briefs.md` for internal drafting and review.
It also writes `editorial_plan.json` and `editorial_plan.md` for weekly planning and owner assignment.
It also writes `editorial_assignments.json`, `editorial_assignments.md`, and `editorial_assignments.csv` for weekly execution tracking.
It also writes `weekly_export_summary.md` for a fast weekly roll-up of use-now counts, review workload, and assignment status.
