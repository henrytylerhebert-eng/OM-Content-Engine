# Portfolio Pilot Mapping Pack

## A. Objective

Prepare a limited Airtable pilot for 3 to 5 real companies using the current one-way repo export model.

This pack is meant to answer one practical question:

Can the current phase-one contract represent a small, real OM operating set clearly enough for staff to use it without confusing raw truth, reviewed truth, and draft operating output?

This pack stays inside the current contract:

- `Companies`
- `Evidence Items`
- `Assumptions`
- `Domain Scores`
- `Capital Readiness`
- `Support Routing`
- `Action Items`
- `Milestones`

No new objects are proposed here.

## B. Recommended pilot company mix

Use 4 required companies plus 1 optional edge case.

Use this exact slot mix for the pilot:

1. `Pilot-01`: cleaner company
2. `Pilot-02`: messy company
3. `Pilot-03`: weak-evidence company
4. `Pilot-04`: stronger draft-progress company
5. `Pilot-05`: optional multi-path edge case

Run the pilot with the first 4 slots by default.
Only add `Pilot-05` if OM expects capital-path ambiguity often enough that it should shape the contract now.

### 1. Cleaner company

Profile:

- one company with a relatively coherent story
- a small number of discovery sources
- at least one reviewed evidence item
- at least one review-ready domain score
- one internal capital-readiness draft that is still clearly a draft

Why this matters:

- proves the happy path
- gives operators a baseline for how the system should feel when inputs are not chaotic

Selection guidance:

- choose a company with relatively coherent source material
- choose a company where at least one reviewed evidence item already exists
- choose a company that can show one review-ready score without stretching the evidence

### 2. Messy company

Profile:

- fragmented notes across multiple sources
- conflicting statements from founder and operator notes
- missing source anchors or weak provenance in some places
- several open review queue issues

Why this matters:

- pressure-tests whether the workflow can surface confusion instead of hiding it
- shows whether operators can still work the system when the company is “real world messy”

Selection guidance:

- choose a company with multiple partial notes or conflicting discovery records
- choose a company where at least one important source anchor is weak or inconsistent
- choose a company that will leave visible queue issues in the pilot

### 3. Weak-evidence company

Profile:

- strong narrative from the founder
- very little reviewed evidence
- low evidence levels
- mostly anecdotal or pattern-level inputs
- capital-readiness should remain weak and clearly tentative

Why this matters:

- tests whether the contract preserves honesty when the company sounds promising but evidence is thin
- exposes whether draft tables start looking falsely authoritative

Selection guidance:

- choose a company with a compelling founder narrative but little reviewed proof
- choose a company where scores should remain weak, blank, or clearly tentative
- choose a company where capital readiness should stay cautious

### 4. Stronger draft-progress company

Profile:

- multiple discovery sources
- multiple reviewed evidence items
- more than one review-ready score draft
- a stronger internal support-routing and milestone story
- capital-readiness still draft-only, but more legible than the others

Why this matters:

- tests whether the contract can express internal progress without crossing into “approved truth”
- gives OM a near-term operating example for support routing and readiness review

Selection guidance:

- choose a company with multiple reviewed evidence items
- choose a company that can support more than one review-ready score
- choose a company where explicit support-routing and milestone drafts are useful and concrete

### 5. Optional edge case: multi-path company

Profile:

- one company where the capital path is unclear or split
- for example: could fit grant-like, customer-funded, or venture-adjacent paths depending on evidence
- one company with evidence spread across multiple domains but weak capital-fit clarity

Why this matters:

- exposes whether `Capital Readiness`, `Support Routing`, and `Milestones` become confusing when the path is not singular
- worth adding only if OM expects this ambiguity often

Selection guidance:

- choose a company where the capital path is genuinely ambiguous, not just incomplete
- choose a company where the same evidence could point toward different near-term routes
- skip this slot if OM rarely sees this pattern today

## C. Required inputs per company

The minimum useful source input set per pilot company is:

### Required source inputs

- 1 company identifier and canonical display name
- 1 report period
- 2 to 4 discovery sources
- at least 2 explicit evidence targets
- at least 1 assumption
- at least 2 domain score drafts
- at least 1 internal capital-readiness draft
- 1 founder draft summary
- 1 internal draft summary

### Strongly recommended source inputs

- one source with a durable locator
  - Google Doc URL, transcript id, Airtable record id, or stable local path
- one operator-authored note
- one evidence item that is intentionally left unreviewed
- one clear `next_action`

For the pilot, the canonical display name should be provided explicitly in the input payload.
Do not rely on inferred company names from `organization_id` or source excerpts for real pilot companies.

### Override expectations

For the pilot, only companies with actual human review decisions should get reviewed-truth overrides.

That means:

- at least one company should include reviewed evidence and one manual score adjustment
- at least one company should have no overrides at all
- the messy company should likely have only partial overrides

### By pilot-company type

Cleaner company:

- 2 to 3 discovery sources
- 2 to 3 evidence items
- 1 reviewed evidence item
- 2 score drafts
- 1 internal capital-readiness draft

Messy company:

- 3 to 5 discovery sources
- 3 to 6 evidence items
- 0 to 1 reviewed evidence items
- multiple open queue issues
- at least one contradictory assumption or unresolved gap

Weak-evidence company:

- 2 discovery sources
- 2 evidence items
- 0 reviewed evidence items
- 2 domain scores with no raw score or weak score support
- 1 internal capital-readiness draft stuck in `needs_review`

Stronger draft-progress company:

- 3 to 4 discovery sources
- 4 to 6 evidence items
- 2 or more reviewed evidence items
- 3 or more domain scores
- 1 clear support-routing draft
- 1 clear milestone draft

Optional edge case:

- 2 to 4 discovery sources
- 2 or more capital-path possibilities
- at least one ambiguous capital-fit story

## D. Record mapping per table

This section describes how each pilot company should map into the current Airtable-oriented tables.

### `Companies`

Each pilot company should produce:

- exactly 1 row per report period

Use it to answer:

- how much reviewed evidence exists
- whether score drafts are starting to mature
- whether internal outputs are still draft
- whether the company appears stuck or ready for more support

The cleaner and stronger-progress companies should feel readable here.
The messy and weak-evidence companies should feel obviously incomplete here.

### `Evidence Items`

Each pilot company should produce:

- 2 to 6 rows

Use it to show:

- what evidence exists
- which domain it supports
- whether it is still raw/extracted vs reviewed
- what source anchors it came from

This table is the core truth-pressure table in the pilot.
If operators cannot trust or navigate this table, the pilot is not working.

### `Assumptions`

Each pilot company should produce:

- 1 to 3 rows

Use it to show:

- what OM still believes but has not fully proven
- what needs validation next

For the messy company, this table should surface unresolved contradictions.
For the weak-evidence company, it should make clear that the narrative is still assumption-heavy.

### `Domain Scores`

Each pilot company should produce:

- at least 2 rows
- ideally 2 to 4 rows for pilot readability

Use it to show:

- which domains are strong enough to discuss
- which domains are still weak or under-reviewed
- what gap matters most next

The stronger-progress company should show at least one review-ready score.
The weak-evidence company should show clearly weak or incomplete score support.

### `Capital Readiness`

Each pilot company should produce:

- 1 internal row
- optionally 1 founder row

Use it to show:

- the likely near-term capital path label
- what evidence is still missing
- whether the company is still in `needs_review` or `emerging`

This should remain sparse and cautious in the pilot.

### `Support Routing`

Each pilot company should produce:

- ideally 1 internal row when OM has created an explicit support-routing draft

Use it to show:

- the next support route OM should likely provide

This is only useful if the route is concrete enough to act on.
For the pilot, do not rely on fallback support-routing rows derived from capital-readiness or report text.
If the team cannot name a next support route cleanly, the table will feel performative.

### `Action Items`

Each pilot company should produce:

- 2 to 4 rows

Use it to show:

- what OM or the founder should do next

This table is useful only if the actions are specific and not repetitive with `Domain Scores` and `Milestones`.

### `Milestones`

Each pilot company should produce:

- ideally 1 to 2 rows when OM has created explicit milestone drafts

Use it to show:

- what the next proof point or operational checkpoint is

For the pilot, do not rely on fallback milestone rows derived from capital-readiness or founder-report text.
This table will be most useful for the stronger-progress and messy companies.

## E. Predicted operator pain points

These are the most likely friction points in a real pilot.

### 1. `Companies` will feel half-summary, half-metadata

Operators will likely use `Companies` as the main entry view, but several current fields are repo-oriented rather than operator-oriented.
The row currently mixes counts, draft metadata, and routing status in one place.

### 2. Provenance is technically good but operationally clumsy

`Evidence Items` carries rich provenance, but operators may not want five different source columns exposed at once.
They likely want one “source link” and one “source type” first.

### 3. `Capital Readiness`, `Support Routing`, and `Milestones` overlap

Operators may ask:

- why is support routing in both `Capital Readiness` and `Support Routing`?
- why is next milestone in both `Capital Readiness` and `Milestones`?
- which one should we actually update or trust?

### 4. `Action Items` risks becoming a noisy derivative table

Because `Action Items` is currently derived from existing drafts, operators may see it as duplicate work rather than a useful decision surface.

### 5. Score meaning may not be obvious

If the team has not fully locked the meaning of `raw_score 1-5`, operators may hesitate or apply their own interpretation.
That will degrade the pilot quickly.

### 6. Draft-state language may be too subtle in Airtable

The repo preserves boundaries well, but once rows are in Airtable, staff may read them as “real enough.”
That is especially risky for `Capital Readiness`, `Support Routing`, and `Milestones`.

## F. Contract weaknesses exposed by the pilot

### Too thin

- `Companies` does not yet carry enough explicit operator-facing company context beyond counts and summary status.
- company naming is still too dependent on inference if upstream inputs are not explicit

### Too verbose

- provenance fields in `Evidence Items`
- draft/review/source-status fields in derived tables
- report-draft metadata in `Companies`

### Too fragmented

- support intent is split across `Capital Readiness`, `Support Routing`, `Internal Report`, and `Action Items`
- milestone intent is split across `Capital Readiness`, `Milestones`, and founder/internal drafts

### Bends but does not fully break

- the pilot can still run as-is
- but operators will likely compress several tables mentally into a smaller working set

That is the main signal to watch.

## G. Recommended adjustments before running the pilot

Stay inside the current contract, but make these practical adjustments before the pilot:

### 1. Use a trimmed Airtable field set

Do not expose every export field in the pilot base.
Start with the minimum viable fields only.

### 2. Require explicit company names

Do not rely on inferred company names for real pilot rows.

### 3. Treat 3 tables as read-only derived views

For the pilot:

- `Support Routing`
- `Action Items`
- `Milestones`

should be clearly labeled as derived draft outputs, not source-authoring tables.

### 4. Keep the main operating workflow on 5 tables

Operators should mainly work in:

- `Companies`
- `Evidence Items`
- `Assumptions`
- `Domain Scores`
- `Capital Readiness`

### 5. Pre-brief operators on boundary language

Tell them explicitly:

- evidence is closest to truth
- reviewed-truth decisions are separate
- scores and readiness are still draft operating views
- support routing and milestones are derived draft outputs

## H. Next best move

Use this exact pilot mix:

1. `Pilot-01`: cleaner company
2. `Pilot-02`: messy company
3. `Pilot-03`: weak-evidence company
4. `Pilot-04`: stronger draft-progress company
5. `Pilot-05`: optional multi-path edge case only if OM expects that ambiguity often

Then run a manual Airtable pilot with those companies and observe:

- which tables operators actually use first
- which fields they ignore
- which fields they mentally rename
- where they duplicate work across tables
- whether `Support Routing`, `Action Items`, and `Milestones` feel useful or redundant

That is the next useful learning step.
More contract complexity before that would be guesswork.
