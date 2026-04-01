# Merge And Rollout Checklist

Use this when landing the current weekly operator and Airtable sync slices into `dev` and validating one real operating cycle.

## Current Branch State

Already landed in `dev`:

- `feature/weekly-operator-command`
- `feature/editorial-assignments-airtable-sync`
- `fix/editorial-assignments-airtable-field-mapping`
- `fix/editorial-assignments-airtable-sync-diagnostics`

Not yet landed in `dev`:

- `fix/editorial-assignments-sync-log-observability`
- `fix/weekly-operator-usability`

Current dependency read:

- `dev` is already usable for a real weekly cycle.
- `fix/editorial-assignments-sync-log-observability` is an observability-only follow-up.
- `fix/weekly-operator-usability` is an operator-summary-only follow-up.
- Those two follow-ups are independent of each other and should stay as separate commits.

## Recommended Merge Order

If you are rolling out from the current stable baseline:

1. Use `dev` as the first real-cycle branch.
2. Merge `fix/editorial-assignments-sync-log-observability` next, once its changes are committed cleanly.
3. Merge `fix/weekly-operator-usability` after that, once its changes are committed cleanly.

Why this order:

- `dev` already contains the core weekly run and Airtable sync path.
- sync-log observability is the safer first follow-up because it improves run visibility in Airtable without changing operator decisions
- weekly operator usability is independent, but lower-risk as a second merge because it changes only the printed summary

## Branch Hygiene Rules

Before merging either follow-up branch:

- make sure the branch is clean
- keep each branch to one logical change
- do not mix sync-log observability and operator-summary usability into one commit
- prefer `--ff-only` merges if the branch has not diverged

## Verification After Each Merge

After merging any of the branches above into `dev`:

```bash
git checkout dev
python3 -m pytest
```

After merging the weekly operator summary follow-up:

```bash
python3 -m src.reporting.weekly_run
```

After merging the sync-log observability follow-up, and only if Airtable env vars are set:

```bash
python3 -m src.reporting.editorial_assignments_airtable_sync --run-dir data/processed/local_run
```

## First Real Weekly Cycle

Run this from `dev`:

```bash
python3 -m pytest
python3 -m src.reporting.weekly_run
```

Open first:

- `data/processed/local_run/snapshot_manifest.json`
- `data/processed/local_run/editorial_plan.md`
- `data/processed/local_run/editorial_assignments.md`

Then:

1. confirm the snapshot wrote successfully
2. confirm `use_now`, `needs_review`, and `hold` counts look plausible
3. assign 1 to 3 rows in `editorial_assignments.md`
4. move at least one row to `in_progress`

## Airtable Sync Validation

With real Airtable credentials configured:

```bash
python3 -m src.reporting.editorial_assignments_airtable_sync --run-dir data/processed/local_run
python3 -m src.reporting.editorial_assignments_airtable_sync --run-dir data/processed/local_run
```

Manual Airtable checks:

- `Editorial Assignments` rows appear in the correct base
- key assignment fields land in the intended columns
- `Data Source Sync Logs` gets one new row per sync run
- each log row includes:
  - `run_dir`
  - `status`
  - `created_count`
  - `updated_count`
  - `unchanged_count`
  - `skipped_count`
  - `started_at`
  - `finished_at`
  - `error_message`

## Rollout Success Criteria

The rollout is successful when:

- `python3 -m pytest` passes on `dev`
- `python3 -m src.reporting.weekly_run` completes and writes `data/processed/local_run`
- the first Airtable sync creates or updates rows without schema errors
- the second Airtable sync does not create duplicate assignment rows
- `Data Source Sync Logs` records one row per sync run
- the operator can open the manifest, plan, and assignments files and take the next weekly action without guessing
