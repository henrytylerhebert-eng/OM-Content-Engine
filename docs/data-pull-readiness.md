# Data Pull Readiness

This runbook explains how to run the first real Airtable data pull into OM Content Engine.

The goal is to confirm that the read-only pipeline can pull real operational records, normalize them, and write inspectable planning and reporting outputs.

This is a safe first step toward LA.IO Overwatch.

---

## 1. Purpose

Use this guide when OM is ready to pull live Airtable data into the Content Engine for operator review.

The first pull should answer:

- Can the repo connect to Airtable?
- Can it read the expected tables?
- Can it normalize records without guessing through messy data?
- Can it produce content, reporting, and review outputs for staff inspection?
- What fields or records need cleanup before the next phase?

---

## 2. What This Pull Does

The live Airtable pull:

- reads Airtable records through the Airtable API
- imports the records into the raw source layer
- preserves Airtable record IDs when available
- normalizes people, organizations, cohorts, participation, and mentor records
- emits review flags for ambiguity instead of guessing
- applies local reviewed-truth overrides when present
- writes processed outputs into `data/processed/local_run/`
- prints a compact operator summary in the terminal

This pull is read-only.

---

## 3. What This Pull Does Not Do

The live Airtable pull does not:

- write back to Airtable
- overwrite Airtable records
- publish content
- schedule posts
- approve public use
- create a dashboard
- run media scraping
- run social monitoring
- create automations
- mark imported records as public-ready by default
- treat imported Airtable rows as reviewed truth

Airtable provides source records.

Reviewed local outputs control what becomes trusted enough for planning, reporting, or public use.

---

## 4. Required Environment Variables

Set these before running the Airtable pull:

```bash
export AIRTABLE_TOKEN="your_airtable_token"
export AIRTABLE_BASE_ID="your_airtable_base_id"
```

If either value is missing, the Airtable reader should fail clearly before pulling data.

---

## 5. Optional Table Override Variables

The default live Airtable table names are:

```text
Active Members
Mentors
Cohorts
```

If the Airtable base uses different table names, set overrides before running:

```bash
export AIRTABLE_ACTIVE_MEMBERS_TABLE="Active Members"
export AIRTABLE_MENTORS_TABLE="Mentors"
export AIRTABLE_COHORTS_TABLE="Cohorts"
```

Optional API override:

```bash
export AIRTABLE_API_URL="https://api.airtable.com/v0"
```

Use the exact Airtable table names.

---

## 6. First Live Airtable Command

From the repo root:

```bash
python3 -m src.reporting.weekly_run --source airtable
```

This is the preferred first command because it runs the operator cycle and prints the summary that staff need first.

Lower-level raw pipeline command:

```bash
python3 -m src.reporting.raw_pipeline --source airtable
```

Use the raw pipeline when debugging ingestion without the weekly operator summary.

---

## 7. Expected Output Files

A successful weekly run writes outputs into:

```text
data/processed/local_run/
```

Expected high-value files include:

- `snapshot_manifest.json`
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
- `editorial_assignments.json`
- `editorial_assignments.md`
- `reporting_snapshot.json`
- `ecosystem_summary.json`
- `ecosystem_report.md`

The exact set may expand as the pipeline grows.

---

## 8. First Files To Inspect

Open these first:

```text
snapshot_manifest.json
editorial_plan.md
editorial_assignments.md
review_flags.json
content_candidates.json
reporting_snapshot.json
ecosystem_summary.json
```

Read them in this order:

1. `snapshot_manifest.json` — confirms what was written.
2. `ecosystem_summary.json` — gives the high-level run picture.
3. `review_flags.json` — shows messy or ambiguous records that need staff review.
4. `content_candidates.json` — shows internal content-planning candidates.
5. `editorial_plan.md` — shows what to use now, review, or hold.
6. `editorial_assignments.md` — shows assignment-ready planning items.
7. `reporting_snapshot.json` — shows machine-readable reporting sections.

---

## 9. Common Failure Modes

### Missing credentials

Likely message:

```text
Missing AIRTABLE_TOKEN in the environment.
Missing AIRTABLE_BASE_ID in the environment.
```

Fix:

- confirm both env vars are set in the current shell
- rerun the command from the same shell

### Wrong base ID

Symptoms:

- Airtable API error
- table not found
- unauthorized response

Fix:

- confirm the base ID belongs to the correct Airtable base
- confirm the token has access to that base

### Wrong table name

Symptoms:

- Active Members not found
- Mentors not found
- Cohorts not found

Fix:

- check exact Airtable table names
- set table override variables
- rerun the command

### Token lacks access

Symptoms:

- unauthorized response
- permission error

Fix:

- update token scopes
- confirm base access
- confirm token is not expired or revoked

### Field shape mismatch

Symptoms:

- run completes but records appear sparse
- review flags spike
- expected people or organizations are missing

Fix:

- inspect `review_flags.json`
- compare source fields against current normalization expectations
- update mapping only after confirming the source field meaning

### Empty outputs

Symptoms:

- files exist but counts are zero
- run summary shows no candidates or assignments

Fix:

- confirm tables contain records
- confirm the token points at the production/intended base
- inspect `ecosystem_summary.json`
- inspect source row counts in the manifest

---

## 10. First-Pull Checklist

Before running:

- [ ] Pull latest `main`
- [ ] Install dependencies
- [ ] Confirm `AIRTABLE_TOKEN`
- [ ] Confirm `AIRTABLE_BASE_ID`
- [ ] Confirm table names: `Active Members`, `Mentors`, `Cohorts`
- [ ] Confirm this is a read-only run

Run:

- [ ] `python3 -m src.reporting.weekly_run --source airtable`

After running:

- [ ] Confirm terminal summary printed
- [ ] Confirm `data/processed/local_run/` exists
- [ ] Open `snapshot_manifest.json`
- [ ] Open `ecosystem_summary.json`
- [ ] Open `review_flags.json`
- [ ] Open `editorial_plan.md`
- [ ] Open `editorial_assignments.md`
- [ ] Note missing fields, sparse records, or table mismatches

Do not publish, sync, or automate anything from the first pull.

---

## 11. What To Paste Back Into ChatGPT After The Run

Paste this block after running the first pull:

```text
Command run:
python3 -m src.reporting.weekly_run --source airtable

Terminal summary:
[paste full terminal summary]

Files checked:
- snapshot_manifest.json: [checked / not checked]
- ecosystem_summary.json: [checked / not checked]
- review_flags.json: [checked / not checked]
- editorial_plan.md: [checked / not checked]
- editorial_assignments.md: [checked / not checked]

Questions or errors:
[paste any error or confusing output]
```

Also paste the top-level counts from `ecosystem_summary.json` and the first 5 to 10 review flags from `review_flags.json`.

Do not paste secrets, tokens, or private credentials.

---

## 12. Success Criteria

The first data pull is successful when:

- Airtable credentials are accepted
- required tables are read
- row counts appear in the output summary or manifest
- processed outputs are written
- review flags are generated for ambiguous records
- staff can inspect content candidates, editorial plans, and reporting snapshots
- no writes are made back to Airtable

A clean first pull does not mean the data is perfect.

A clean first pull means the pipe is open, the outputs are inspectable, and the next cleanup work is visible.
