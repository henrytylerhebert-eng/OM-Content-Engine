# Operational Snapshot

The raw and demo pipelines now write one predictable local snapshot pack per run.

## Standard Files

Each run directory should contain:

- `normalized_bundle.json`
- `reviewed_truth.json`
- `review_flags.json`
- `content_intelligence.json`
- `content_candidates.json`
- `content_candidates.csv`
- `content_briefs.json`
- `content_briefs.md`
- `editorial_plan.json`
- `editorial_plan.md`
- `reporting_snapshot.json`
- `ecosystem_summary.json`
- `ecosystem_report.md`
- `snapshot_manifest.json`

## What The Manifest Is For

`snapshot_manifest.json` is the short index for the run.

It records:

- which raw source files were used
- where the snapshot was written
- the compact run summary
- reviewed-truth override counts
- the standard artifact list with file paths and descriptions
- the reporting sections included in the snapshot

## Operating Use

For a normal review cycle:

1. run the pipeline
2. open `snapshot_manifest.json` first
3. use it to jump into the summary, review queue, reporting snapshot, brief pack, editorial plan, and markdown report

This keeps each run inspectable without adding packaging, a UI, or another storage system.
