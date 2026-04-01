# Editorial Assignments

This layer turns `editorial_plan.*` into a small internal execution tracker.

It is for assigning owners, target cycles, and working status on items that are already in the weekly plan.

It is not a publishing system.

## Where It Is Written

Each standard pipeline run now writes:

- `editorial_assignments.json`
- `editorial_assignments.md`
- `editorial_assignments.csv`

into the run directory, such as `data/processed/local_run/`.

## What It Tracks

Each assignment row carries:

- who should own it
- what cycle it belongs to
- the current status
- the next operational step
- any short blocking notes

Default rows are created for `use_now` and `needs_review`.

`hold` items stay out by default so the tracker stays focused on actionable work.

## Weekly Use

1. Run the pipeline.
2. Open `editorial_plan.md` to choose what matters this cycle.
3. Open `editorial_assignments.md` to assign owners and track progress.
4. Update `owner`, `target_cycle`, and `assignment_status` locally as work moves.
5. Keep `blocking_notes` short and operational.

## Status Meanings

- `unassigned`: row exists but no clear owner yet
- `not_started`: accepted into the cycle but not yet moving
- `in_progress`: someone is actively working it
- `drafted`: draft exists internally
- `approved_internal`: cleared for internal next steps
- `shipped`: finished for the intended internal cycle
- `dropped`: removed from active execution

## Operating Rule

This tracker follows upstream trust decisions.

It does not change:

- readiness
- reviewed truth
- publication approval

An item can be assigned for internal work without being public-ready.
