# Next-Stage Audit

## Short Audit

The current scaffold is in a good place for a first pass. The repo has a clear shape, conservative normalization logic, practical docs, and passing tests. That is the right starting point for Opportunity Machine.

The biggest gaps are no longer architectural. They are operational:

- source mapping is still table-level, not column-level
- review flags exist, but they are not standardized into a review workflow
- interaction normalization is still missing for `Connections`, `Meeting Requests`, and `Feedback`
- sample fixtures are embedded in tests instead of reusable across the repo
- useful outputs for founder, mentor, and content-ready segmentation are still thin
- the schema can describe more than the current transform layer actually produces

The main risk right now is not overbuilding. It is letting the docs and schema outrun the concrete mapping rules. The next stage should tighten source assumptions, standardize review handling, and produce useful outputs from conservative transforms.

## Prioritized Task List

### P0

- Centralize review flags with severity and recommended action so ambiguous records can be routed into a review queue.
- Add reusable pilot-style fixtures for the named source tables so new transforms can be tested consistently.
- Add starter interaction normalization for `Connections`, `Meeting Requests`, and `Feedback`.
- Add founder, mentor, and content-ready segmentation helpers that consume normalized payloads as they exist today.

### P1

- Expand `docs/source-mapping.md` from table descriptions into a field checklist that can be validated against real exports.
- Add a simple review workflow doc so staff or operators know what to inspect first.
- Add tests for interaction normalization, review queue row generation, and segmentation outputs.

### P2

- Add row orchestration helpers that bundle organization, people, affiliation, participation, and interaction outputs per source table.
- Add safer matching hints for unresolved joins, especially for mentor employer orgs and cohort participation.
- Add export-ready reporting views for spotlight candidates and outreach segments.

## File Changes Added In This Pass

- `docs/review-workflow.md`
- `src/transform/review_flags.py`
- `src/transform/normalize_interactions.py`
- `src/reporting/segments.py`
- `tests/fixtures/pilot_rows.py`
- updates to `docs/source-mapping.md`
- updates to tests for fixtures, review flags, interactions, and segment outputs

