# Reviewed Truth

## Purpose

The transform layer already preserves source truth and flags ambiguity.

This reviewed-truth layer adds one missing piece: a durable place for human decisions that should survive the next pipeline run.

It is intentionally simple:

- raw exports stay raw
- normalized records stay source-derived
- reviewed truth lives in one local JSON file
- downstream outputs use reviewed truth when it exists

## Where It Lives

- Local reviewed-truth file: `data/reviewed_truth/overrides.json`
- Starter template: `data/reviewed_truth/overrides.example.json`

The real reviewed-truth file should usually stay local and repo-owned, not hidden inside Airtable exports and not hard-coded into transforms.

JSON fits the current stage better than a heavier database-backed review table because:

- it is easy to inspect in git or local diffs
- it is easy to edit without a UI
- it keeps reviewed truth explicit and portable
- it does not introduce another runtime dependency just to store a small set of approved corrections

## What It Can Change

The first pass supports overrides against these targets:

- `organizations`
- `people`
- `affiliations`
- `programs`
- `cohorts`
- `participations`
- `mentor_profiles`
- `organization_content`
- `person_content`
- `review_rows`

That covers the practical cases we need right now:

- correct `org_type`
- mark a record as `internal`
- suppress a grouped or placeholder record from reviewed outputs
- designate a spokesperson
- confirm or deny content eligibility or content readiness
- confirm spotlight suitability when a human wants to override the derived threshold
- resolve cohort identity or participation status when a human has better context
- confirm or suppress semi-structured member-side person creation
- mark a record as `externally_publishable`, but only through reviewed truth
- suppress a resolved review flag

## What It Does Not Change

- It does not rewrite raw source files.
- It does not change how normalization infers source-derived truth.
- It does not auto-resolve review flags just because a record was patched.

If a human resolves a flag, the matching `review_rows` override should be explicit too. That keeps the logic inspectable.

## Rule Shape

Each override rule is a small JSON object:

```json
{
  "id": "fix-bayou-org-type",
  "target": "organizations",
  "match": {
    "source_record_id": "rec_member_004"
  },
  "set": {
    "org_type": "service_provider"
  },
  "reason": "Confirmed during manual review.",
  "reviewed_by": "ops_owner",
  "reviewed_at": "2026-03-31"
}
```

Supported rule behaviors:

- `match`: exact field match against the target record
- `set`: patch one or more fields on the reviewed copy
- `suppress: true`: remove the matched record from reviewed outputs
- empty `set` with no suppression: explicitly confirm the reviewed copy and stamp override metadata without changing fields

`externally_publishable` belongs only on content targets such as `organization_content` or `person_content`.
The derived content layer always leaves this field `False` by default.
The reviewed-truth loader now rejects `externally_publishable` on normalized targets such as `people` or `organizations`.

## How It Is Applied

The pipeline now runs in this order:

1. load raw exports
2. build normalized records and raw review flags
3. apply reviewed-truth overrides to normalized collections
4. build content intelligence from the reviewed collections
5. apply reviewed-truth overrides to content records
6. apply reviewed-truth overrides to review rows
7. build reporting from the reviewed collections and reviewed review queue

The raw normalized bundle is still preserved for traceability.

## Common Override Cases

These are the main cases the current layer is designed to handle:

1. Correct an organization type that the classifier could not safely infer.
2. Mark an internal OM record so it stays out of external ecosystem views.
3. Suppress a grouped or placeholder record that should not be treated as canonical.
4. Mark a person or affiliation as the approved spokesperson.
5. Confirm or deny a profile's content eligibility after manual review.
6. Confirm spotlight suitability when staff approves a stronger feature candidate than the heuristics would infer.
7. Resolve a cohort or participation status when the source text was weak.
8. Confirm or suppress a semi-structured member-side person after manual review.
9. Mark a record as externally publishable only after human approval.
10. Suppress a review flag that has been resolved intentionally.

## Semi-Structured Member-Side People

The people normalizer now has a narrow member-side path that can create a person from `Personnel` when the row has:

- one clear full name
- one unique non-generic email
- one resolved organization or cohort context

Reviewed truth handles the two human decisions that come after that:

- confirm the created person is canonical enough to keep
- suppress the person if the row still should not be trusted

A confirmation rule can be as small as:

```json
{
  "id": "confirm-morgan-member-person",
  "target": "people",
  "match": {
    "source_record_id": "rec_member_semi_001",
    "person_resolution_basis": "semi_structured_member_side"
  },
  "set": {},
  "reason": "Manual review confirmed this member-side person is real and should remain in reviewed truth."
}
```

That rule does not change fields. It simply marks the reviewed copy as human-confirmed through override metadata.

See `data/reviewed_truth/overrides.example.json` for concrete examples.

## Output Artifacts

The pipeline now writes:

- `normalized_bundle.json`: source-derived normalized records
- `reviewed_truth.json`: reviewed copies plus override application log
- `review_flags.json`: current review queue after any review-row suppressions
- downstream reporting files built from reviewed truth

## Practical Use

The intended loop is:

1. run the pipeline
2. inspect `review_flags.json`
3. add a small override rule when a human wants a durable decision
4. rerun the pipeline
5. confirm the reviewed outputs now reflect that decision

This is not a workflow engine. It is just a small durable layer for approved corrections.
