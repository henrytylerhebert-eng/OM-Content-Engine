# Content Briefs

This export is the small internal brief pack built from `content_candidates.json`.

It is for drafting, review, and planning.
It is not a publishing feed.

## Where It Is Written

Each pipeline run now writes:

- `content_briefs.json`
- `content_briefs.md`

into the run directory, such as `data/processed/local_run/`.

## How It Differs From Content Candidates

`content_candidates.json` answers:

- what is worth considering
- how trusted it is
- whether it is planning-safe or public-ready

`content_briefs.*` answers:

- what the story is about
- why it matters
- what evidence supports it
- what not to overclaim
- what format is the best current fit

## Brief Status Meanings

- `planning_safe_only`: useful for internal planning, but still heuristic
- `reviewed_for_internal_use`: reviewed truth already strengthens the record for internal use
- `public_ready`: explicitly safe for public-facing use under current rules
- `hold_for_review`: keep the brief internal and cautious until trust gaps are resolved

## Operating Rule

`planning_safe` helps a record enter the brief pack.

It does not mean:

- approved for publishing
- approved for scheduling
- ready for external automation

`public_ready` stays stricter and only follows the existing reviewed-truth rules.

## Weekly Planning Use

- Scan `content_briefs.md` in planning meetings.
- Use `content_briefs.json` when you want the same pack in structured form.
- Treat `guardrails` and `unresolved_review_notes` as part of the brief, not as optional footnotes.
