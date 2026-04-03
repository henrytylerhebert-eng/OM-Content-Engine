# Editorial Operator Runbook

Use this when running the normal weekly editorial cycle from the repo root.

## 1. Run The Cycle

```bash
python3 -m src.reporting.weekly_run
python3 -m src.reporting.editorial_assignments_airtable_sync --run-dir data/processed/local_run
```

If you use a virtualenv, activate it first in the same terminal.

## 2. Open These Files First

Open in this order:

1. `data/processed/local_run/snapshot_manifest.json`
2. `data/processed/local_run/editorial_queue_summary.md`
3. `data/processed/local_run/editorial_plan.md`
4. `data/processed/local_run/editorial_assignments.md`
5. `data/processed/local_run/content_brief_candidates.md`

If the sync ran, also open:

6. `data/processed/local_run/editorial_assignments_sync_results.md`

## 3. How To Read The Outputs

### `snapshot_manifest.json`

Open this first to confirm the run completed and the output paths are current.

Use it to check:

- run directory
- source files used
- which artifacts were written

### `editorial_queue_summary.md`

Start here.

Use it to see:

- what needs action first
- which `recommended_next_step` buckets are active
- which rows are blocked by review or missing assets

Act on:

- `resolve_review_flag` first
- then `gather_asset`
- then `draft_brief`

### `editorial_plan.md`

Use this to understand why an item is in the weekly queue and which bucket it came from.

Look for:

- `use_now`
- `needs_review`
- `hold`

If a row is in `hold`, do not force it into active drafting work.

### `editorial_assignments.md`

Use this as the execution tracker.

Update:

- `owner`
- `assignment_status`
- `target_cycle`
- human `next_step`

Keep `blocking_notes` short and operational.

### `content_brief_candidates.md`

Use this only for internal drafting handoff.

It is the compact pack for rows that are ready enough for briefing work now.

It is not a publishing approval list.

## 4. What To Do In Airtable After Sync

Open the `Editorial Assignments` table.

Work in this order:

1. Filter to active rows for the current cycle.
2. Start with rows where `recommended_next_step` is `resolve_review_flag`.
3. Then work `gather_asset`.
4. Then move `draft_brief` rows into active drafting.
5. Update human fields as work moves:
   - `owner`
   - `assignment_status`
   - `next_step`
   - `target_cycle`

Treat Airtable as the working surface, not the source of truth.

## 5. Field Meanings

### `recommended_next_step`

Machine-managed.

Use it as the default action recommendation for the row.

### `next_step`

Human-managed.

Use it for the operator’s actual current step after review.

### `brief_status`

Planning boundary.

Use it to tell whether the row is safe for internal planning work or should stay held back.

### `readiness_level`

Readiness signal from the pipeline.

Higher readiness means less operator cleanup before drafting.

### `public_ready`

External-use boundary.

`false` does not block internal planning work, but it does mean the row should not be treated as ready for outward-facing use.

## 6. If Sync Preflight Fails

Do not guess.

Read the terminal message and then open:

- `data/processed/local_run/editorial_assignments_sync_results.json`
- `data/processed/local_run/editorial_assignments_sync_results.md`

Fix the named problem, then rerun sync.

Common preflight issues:

- missing `AIRTABLE_TOKEN`
- missing `AIRTABLE_BASE_ID`
- missing Airtable table
- missing Airtable field

If fields are missing, add the named Airtable field(s) and rerun sync.

## 7. How To Interpret Sync Row Outcomes

### `updated`

The sync changed machine-managed Airtable fields.

Action:

- no manual fix needed
- review only if the changed row looks surprising

### `unchanged`

The row already matched the local sync-managed values.

Action:

- this is the normal steady state

### `skipped`

The sync protected an Airtable row from overwrite.

Action:

- inspect the reason in the sync results
- keep Airtable edits if they are intentional
- only overwrite deliberately

### `failed`

The row could not be processed cleanly.

Action:

- inspect the reason in the sync results
- fix the data or Airtable issue before rerunning

## 8. Weekly Operator Rule

Use local outputs to decide what the assignment is.

Use Airtable to coordinate who is doing the work and what is moving now.
