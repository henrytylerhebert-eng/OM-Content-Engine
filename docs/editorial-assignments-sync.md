# Editorial Assignments Airtable Sync

This sync is a one-way visibility layer from the local assignment tracker into Airtable.

The local file stays the source of truth:

- `data/processed/local_run/editorial_assignments.json`

Airtable is only the shared team view.

## Sync Contract

This layer must stay thin.

It is allowed to:

- read the local `editorial_assignments.json` output
- flatten existing assignment fields into Airtable
- upsert Airtable rows by `assignment_id`
- log what happened during the sync

It is not allowed to:

- recompute trust or readiness logic
- create a new approval workflow in Airtable
- replace the local assignment tracker
- treat Airtable as the source of truth
- infer missing values that are not already present in the local assignment output

## 1. Synced Fields

Table: `Editorial Assignments`

The table may contain the full local assignment shape, but routine sync updates only manage the machine-owned recommendation and evidence fields on existing Airtable rows:

- `recommended_action`
- `source_hook`
- `evidence_summary`
- `suggested_angle`
- `suggested_format`
- `readiness_level`
- `trust_basis`

Those are the only fields included in routine Airtable PATCH updates and in conflict detection against prior sync state.

The local assignment output still contains the broader row shape:

- `assignment_id`
- `entity_id`
- `org_name`
- `primary_person_name`
- `bucket`
- `brief_status`
- `readiness_level`
- `trust_basis`
- `public_ready`
- `suggested_angle`
- `suggested_format`
- `recommended_action`
- `owner`
- `target_cycle`
- `assignment_status`
- `priority`
- `blocking_notes`
- `next_step`
- `source_hook`
- `evidence_summary`

Use the same Airtable field names as the local assignment output.

Practical effect:

- create path: a missing Airtable row is still seeded from the local assignment output
- update path: only the machine-owned recommendation/evidence fields are patched
- human-managed execution fields such as `owner`, `assignment_status`, `priority`, `target_cycle`, `next_step`, and `blocking_notes` are left alone on routine reruns

Exact field mapping:

- `assignment_id` -> `assignment_id`
- `entity_id` -> `entity_id`
- `org_name` -> `org_name`
- `primary_person_name` -> `primary_person_name`
- `bucket` -> `bucket`
- `brief_status` -> `brief_status`
- `readiness_level` -> `readiness_level`
- `trust_basis` -> `trust_basis`
- `public_ready` -> `public_ready`
- `suggested_angle` -> `suggested_angle`
- `suggested_format` -> `suggested_format`
- `recommended_action` -> `recommended_action`
- `owner` -> `owner`
- `target_cycle` -> `target_cycle`
- `assignment_status` -> `assignment_status`
- `priority` -> `priority`
- `blocking_notes` -> `blocking_notes`
- `next_step` -> `next_step`
- `source_hook` -> `source_hook`
- `evidence_summary` -> `evidence_summary`

This keeps the Airtable row shape aligned with the local source-of-truth output and removes naming drift in live validation.

## 2. Required Airtable Table Shape

Recommended `Editorial Assignments` table shape:

- `assignment_id`
  - primary field
  - single line text
  - must be unique per assignment row
- `entity_id`
  - single line text
- `org_name`
  - single line text
- `primary_person_name`
  - single line text
- `bucket`
  - single select or single line text
- `brief_status`
  - single select or single line text
- `readiness_level`
  - single select or single line text
- `trust_basis`
  - single select or single line text
- `public_ready`
  - checkbox or text
- `suggested_angle`
  - single line text
- `suggested_format`
  - single line text
- `recommended_action`
  - single line text
- `owner`
  - collaborator, single select, or single line text
- `target_cycle`
  - single select or single line text
- `assignment_status`
  - single select or single line text
- `priority`
  - single select or single line text
- `blocking_notes`
  - long text
- `next_step`
  - single line text
- `source_hook`
  - long text
- `evidence_summary`
  - long text

Recommended `Data Source Sync Logs` table shape:

- `sync_name`
- `source_file_path`
- `started_at`
- `finished_at`
- `status`
- `created_count`
- `updated_count`
- `unchanged_count`
- `skipped_count`
- `error_count`
- `force_overwrite`
- `notes`

The log table is for run visibility only. It must not become a workflow queue.

## 3. Upsert Behavior

Upsert key:

- `assignment_id`

Expected behavior:

1. Read the local `editorial_assignments.json` file.
2. Run a lightweight preflight field check against the destination `Editorial Assignments` table before any row writes.
3. If required Airtable fields are missing, fail preflight cleanly, list the missing fields, refresh the local sync results artifact, and stop.
4. For each row, find the Airtable record with the same `assignment_id`.
5. If no Airtable record exists, create one.
6. If a record exists and its machine-managed sync fields still match the last known synced state, update only that sync-owned subset from the local output.
7. If a record exists and those sync-owned fields appear to have been changed manually in Airtable since the last sync, skip it unless explicit overwrite is allowed.

This keeps Airtable useful for visibility without turning it into a second system of truth.

## 4. Null And Blank Handling

Blank handling should be conservative and explicit:

- blank local strings should sync as blank values when the update itself is safe
- missing local values should not be replaced with guessed defaults
- blank local values must not clear manual Airtable edits when the record is being skipped for conflict protection
- boolean-style fields such as `public_ready` should be written in one consistent format only
  - recommended: Airtable checkbox if available
  - acceptable fallback: explicit text values such as `true` / `false`

The sync layer should never infer content approval from an empty or missing value.

## 5. What Counts As A Safe Overwrite

The sync is conservative by default.

A safe overwrite is one of these:

- create missing Airtable rows
- update a row that still matches the last known local sync state
- update a row when the operator explicitly allows overwrite for that assignment
- update all rows only when the operator explicitly uses a global force-overwrite mode

The sync must not overwrite by default when:

- Airtable values differ from the last synced state
- the sync has no prior local state and the Airtable row already contains meaningful manual content
- duplicate Airtable records exist for the same `assignment_id`

Allowed explicit override controls:

- `--force-overwrite`
- `--allow-overwrite-id <assignment_id>`

## 6. What Counts As A Sync Failure

The sync should fail clearly when any of these happen:

- missing `AIRTABLE_TOKEN`
- missing `AIRTABLE_BASE_ID`
- missing local `editorial_assignments.json`
- invalid local JSON shape
- missing required Airtable table
- missing required Airtable fields
- duplicate Airtable rows for the same `assignment_id`
- Airtable API error
- local sync-state write failure
- local results-log write failure

Skips are not the same as failures.

A skipped row means the contract protected a manual edit or caught an ambiguity.

Preflight failures should be especially clear for operators. When required Airtable fields are missing, the error should name:

- the base id
- the destination table
- the missing field names
- the next action: `Add the missing Airtable field(s) and rerun sync.`

## 7. Operator-Facing Sync Results

Each sync should produce two summaries:

### Local results artifact

Write one local results file, for example:

- `data/processed/local_run/editorial_assignments_sync_results.json`

That file should summarize:

- source file path
- run directory
- target table name
- generated timestamp
- started / finished timestamps
- created count
- updated count
- unchanged count
- skipped count
- error count
- sync status when preflight fails
- error message when preflight fails
- missing Airtable fields when preflight fails
- explicit overwrite mode used or not
- aggregate summary details including:
  - `status_counts`
  - `rows_with_changed_machine_fields_count`
  - `overwrite_used_count`
  - `skipped_row_count`
  - `top_skip_failure_reasons`
  - `top_changed_rows`
- per-row result details including:
  - `assignment_id`
  - row `status`
  - compact `reason` and `reason_summary`
  - `airtable_record_id` when available
  - `changed_machine_fields`
  - `overwrite_used`

Per-row status values are:

- `created`
- `updated`
- `unchanged`
- `skipped`
- `failed`

Interpretation:

- updated rows show which sync-owned fields were patched
- skipped rows show which sync-owned fields differed when that can be determined
- unchanged rows still include a clean reason so the steady-state output is easy to inspect

Optionally write a small markdown companion next to the JSON file, for example:

- `data/processed/local_run/editorial_assignments_sync_results.md`

Use the markdown file only for quick scanning. The JSON file stays the source of truth.

If preflight fails before row sync begins, the local results artifact should still be refreshed so it does not leave stale success-looking output from a prior run.

Recommended markdown sections:

- generated / source overview
- aggregate counts
- top skip / failure reasons
- top changed rows
- updated rows
- skipped rows
- failed rows

### Airtable log row

Each sync appends one run log into:

- `Data Source Sync Logs`

The operator-facing summary should make it obvious:

- what source file was synced
- whether Airtable was only updated, not trusted
- how many rows were created, updated, unchanged, skipped, or failed
- which rows were updated, skipped, or failed and why

The sync should also keep one local sync-state file for conflict protection:

- `data/processed/airtable_sync/editorial_assignments_state.json`

## Command

Set:

- `AIRTABLE_TOKEN`
- `AIRTABLE_BASE_ID`

Optional:

- `AIRTABLE_EDITORIAL_ASSIGNMENTS_TABLE`
- `AIRTABLE_SYNC_LOGS_TABLE`
- `AIRTABLE_API_URL`

Run:

```bash
python3 -m src.reporting.editorial_assignments_airtable_sync
```

Common override examples:

```bash
python3 -m src.reporting.editorial_assignments_airtable_sync --allow-overwrite-id assignment:use_now:person_morgan_example_com
python3 -m src.reporting.editorial_assignments_airtable_sync --force-overwrite
```

## Operating Rule

Use Airtable to see assignments and coordinate team work.

Use the local JSON tracker to decide what the assignment actually is.

If Airtable and the local tracker disagree, the local tracker wins unless a human explicitly decides otherwise in the local system.
