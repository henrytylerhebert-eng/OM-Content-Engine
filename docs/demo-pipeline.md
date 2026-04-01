# Demo Pipeline

This repo includes a local demo pipeline for the safe synthetic sample exports in `tests/fixtures/`.

The goal is simple:

1. load sample raw source files
2. run the current normalization layer
3. emit inspectable normalized outputs
4. emit review flags
5. generate a simple ecosystem summary and markdown report

## Command

Run the demo from the repo root:

```bash
python3 -m src.reporting.demo_pipeline
```

Optional arguments:

```bash
python3 -m src.reporting.demo_pipeline \
  --active-members tests/fixtures/active_members.csv \
  --mentors tests/fixtures/mentors.csv \
  --cohorts tests/fixtures/cohorts.csv \
  --output-dir data/processed/demo
```

## What The Demo Uses

- `tests/fixtures/active_members.csv`
- `tests/fixtures/mentors.csv`
- `tests/fixtures/cohorts.csv`

These are safe synthetic fixtures. They are not live OM exports.

## What The Demo Writes

The command writes files into `data/processed/demo/` by default:

- `normalized_bundle.json`
- `reviewed_truth.json`
- `review_flags.json`
- `content_intelligence.json`
- `reporting_snapshot.json`
- `ecosystem_summary.json`
- `ecosystem_report.md`
- `snapshot_manifest.json`

The manifest is the quick index for the run. It lists the source files used, the key summary counts, and the standard output files that were produced.

## Output Shape

`normalized_bundle.json` includes:

- organizations
- people
- affiliations
- programs
- cohorts
- participations
- mentor profiles

`review_flags.json` includes review rows from:

- normalization
- content intelligence checks

`ecosystem_summary.json` includes compact counts such as:

- total organizations
- total people
- total mentor profiles
- participation count
- organization types
- person types
- review flag count
- content-ready counts

## Expected Demo Behavior

With the current sample fixtures, the demo should:

- load `Active Members` and `Mentors`
- load the explicit `Cohorts` export when present
- create startup, partner, internal, and other organization records
- create founder, operator, and mentor people records
- send grouped personnel fields to review
- keep `Active Members` multi-cohort text review-first
- use the explicit `Cohorts` export to split safe multi-cohort history and prefer explicit cohort provenance during reconciliation
- produce a markdown report for quick inspection

## Example Summary

The command prints a compact summary after writing files. Example shape:

```json
{
  "organization_count": 6,
  "people_count": 11,
  "mentor_profile_count": 3,
  "participation_count": 4,
  "organization_types": {
    "startup": 3,
    "partner": 1,
    "other": 1,
    "internal": 1
  },
  "person_types": {
    "founder": 3,
    "operator": 5,
    "mentor": 3
  },
  "review_flag_count": 26,
  "content_ready_organization_count": 4,
  "content_ready_people_count": 4
}
```

The exact counts may change if the sample fixtures change.

## Notes

- This is a demo path, not a production ingest job.
- It is intentionally file-based and inspectable.
- It does not write back to any operational source.
