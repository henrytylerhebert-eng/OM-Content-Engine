# Portfolio Post-Pilot Review Framework

Use this template after the limited Airtable pilot to decide what should change, what should stay stable, and what should still be deferred.

This review is for product and architecture decisions.
It is not a generic retrospective.

## A. Review questions

### Operator usability

- Could operators understand one company from `Companies` and then drill into `Evidence Items`, `Domain Scores`, and `Capital Readiness` without outside translation?
- Did operators actually use the 5 core working tables as intended, or did they treat one of the derived tables as a primary surface?
- Which tables did operators actually use first?
- Which tables did they ignore, avoid, or treat as redundant?
- Where did operators hesitate before taking action?
- Which questions could they answer quickly?
  - Which companies are strongest right now?
  - Which companies are stuck and why?
  - What evidence is improving?
  - What support should OM route next?
  - Which companies are ready for which capital path?

### Field clarity

- Which fields did operators understand immediately?
- Which fields did operators rename mentally while using Airtable?
- Which fields did operators never open or mention?
- Which fields felt too technical, too vague, or too duplicative?
- Which fields need a clearer label versus a deeper model change?

### Schema drift

- What helper columns did operators add in Airtable?
- What comments, notes, or manual patches did operators keep outside the exported contract?
- Which exported fields were consistently ignored and replaced with manual workarounds?
- Did any tables become de facto authoring tables even though they were supposed to be read-only?

### Object overlap

- Did `Capital Readiness`, `Support Routing`, `Action Items`, `Milestones`, and recommendations feel meaningfully distinct?
- Did operators know which table to trust for “what happens next”?
- Did recommendations work as a secondary repo-side summary, or did operators expect them to behave like a primary operating table?
- Did `Action Items` add useful operational clarity, or mostly restate what already existed in scores, support routing, and milestones?
- Should any of these remain separate, be collapsed, or become hidden views?

### Score semantics clarity

- Did operators share a common meaning for `raw_score 1-5`?
- Did operators understand when a score should remain blank?
- Did `confidence` help decision-making or add ambiguity?
- Did `evidence_level 0-7` feel usable or overly granular?

### Readiness semantics clarity

- Did operators understand the difference between `needs_review`, `emerging`, and stronger readiness language?
- Did `Capital Readiness` feel appropriately cautious, or still too final?
- Did founder-facing and internal-facing readiness rows feel meaningfully different?

### Identity model

- Was `Organization` a good enough anchor for the pilot?
- Did operators need a clearer portfolio-specific identity object with fields like display name, owner, program status, cohort, or watchlist state?
- Did the current company row feel like a thin summary over `Organization`, or like a missing `PortfolioCompany`?
- Which missing company-level operating fields showed up repeatedly enough to justify a true `PortfolioCompany` record?

### Contract change threshold

- Which contract changes are justified by repeated operator friction?
- Which changes are only cosmetic and should wait?
- Which frustrations came from Airtable view design rather than schema shape?

### What should not be touched yet

- Which areas are still too early to redesign because the pilot evidence is too thin?
- Which issues should be solved with Airtable views or operator guidance rather than schema change?
- Which problems should stay deferred until a later sync or workflow phase?

## B. Success metrics

Use these signals to judge whether the pilot contract is holding.

### Operator comprehension

- Operators can explain the role of each of the 5 core working tables without help.
- Operators can correctly describe the difference between reviewed evidence and draft interpretation.
- Operators can identify the next support route and likely capital path for a company without checking repo internals.

### Workflow usability

- Operators can review one company end to end in a reasonable amount of time.
- Operators do not need to open the repo to understand normal Airtable rows.
- Operators do not create large shadow spreadsheets or parallel note systems to compensate.

### Contract stability

- Explicit company names remain stable across reruns.
- The same exported fields remain useful across at least 3 companies.
- Derived tables do not require manual cleanup to look trustworthy.

### Semantic clarity

- Operators use score language consistently.
- Operators use readiness language consistently.
- Operators do not confuse draft operational output with source truth.

## C. Failure signals

Treat these as evidence that the contract should change.

- Operators repeatedly ask what a field means.
- Operators keep using comments or helper columns to restate the same missing concept.
- Operators edit read-only derived rows as if they were primary records.
- Operators ignore the intended 5-core/3-derived split and work mainly from derived tables.
- Operators cannot tell which table owns support routing or milestones.
- Operators interpret draft capital-readiness rows as approved recommendations.
- `raw_score`, `confidence`, or `readiness_status` mean different things to different people.
- `Companies` becomes a cluttered summary row that no one trusts.
- `Support Routing`, `Milestones`, or recommendations feel like duplicate outputs rather than useful decision surfaces.
- The team keeps saying “the repo says one thing, Airtable says another.”

## D. Contract decisions to revisit

Use this section to log decisions after the pilot.

### Candidate decisions

- Keep or simplify the 8-table contract
- Hide, rename, or remove specific fields
- Keep `Support Routing`, `Milestones`, and recommendations separate or collapse some of them
- Keep recommendations as a repo-side summary artifact or surface them more directly later
- Tighten score semantics
- Tighten readiness semantics
- Introduce a true `PortfolioCompany` object or keep using `Organization`
- Promote or demote founder-facing rows in Airtable
- Keep id-based tables or move toward linked-record structure

### Decision standard

Only change the contract when at least one of these is true:

- the same problem appears across multiple pilot companies
- multiple operators hit the same confusion point
- the confusion changes a real decision, not just wording preference
- the fix cannot be handled cleanly with Airtable views, filters, or field hiding

Do not change the contract just because:

- a field looks inelegant in the repo
- a future sync model might want a different shape
- a single pilot company exposed an edge case

## E. Recommended post-pilot decision sequence

1. Review operator behavior before reviewing code or schema elegance.
2. Confirm whether operators actually used the 5 core tables as primary working surfaces and treated the 3 derived tables as read-only views.
3. Review whether the frozen pilot score semantics and readiness semantics held up before changing object shape.
4. Decide whether `Support Routing`, `Milestones`, and recommendations should stay separate.
5. Decide whether `Organization` is still sufficient or whether `PortfolioCompany` is now justified.
6. Make only the smallest contract changes that resolve repeated pilot friction.
7. Keep sync, write-back, UI, and investor-facing decisions deferred unless the pilot clearly proves they are blocking.

### What should not be touched yet

Do not touch these immediately after the pilot unless the pilot proves they are blocking:

- full Airtable sync
- write-back automation
- dashboard UI
- investor-facing outputs
- predictive or automated capital logic
- broad recommendation expansion

The post-pilot goal is to tighten the operating contract, not to expand the product surface.
