# Owner Checklist

Use this as the recurring weekly or monthly operating loop.

## Before Run

- Export fresh CSVs for `Active Members`, `Mentors`, and `Cohorts`.
- Put them in `data/raw/`.
- Check whether `data/reviewed_truth/overrides.json` needs any local updates before the run.
- Make sure you are working from the repo root.

## Run

- Run `python3 -m src.reporting.raw_pipeline`.
- Open the new run folder in `data/processed/local_run/`.
- Open `snapshot_manifest.json` first to confirm the source files and artifact list.

## Post-Run Review

- Check `ecosystem_summary.json` for top-line counts and obvious surprises.
- Check `review_flags.json` for unresolved ambiguity and sparse records.
- Check `reporting_snapshot.json` and `ecosystem_report.md` for planning outputs.
- Check `reviewed_truth.json` if you expected overrides to apply.

## Override And Review Resolution

- Fix Airtable if the source record itself is wrong.
- Add or update `data/reviewed_truth/overrides.json` if the decision should persist locally across runs.
- Rerun the pipeline after override changes.
- Confirm that the reviewed output changed in `reviewed_truth.json`, `content_intelligence.json`, or `reporting_snapshot.json`.

## Planning And Reporting Use

- Use `internally_usable`, `content_ready`, and `spotlight_ready` for internal planning.
- Use people provenance sections to distinguish structured people, semi-structured auto-created people, mentor-derived people, and review-needed candidates.
- Use `review_burden_by_flag` and missing-asset sections to decide what needs cleanup before deeper use.

## Do Not Treat As Public-Ready

- Do not treat `internally_usable` as public-ready.
- Do not treat `content_ready` as publication approval.
- Do not treat `spotlight_ready` as public approval.
- Only treat `externally_publishable` as safe for public-facing use, and only when it came from reviewed truth.
