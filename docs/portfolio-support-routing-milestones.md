# Portfolio Support Routing And Milestones

## Purpose

Phase one needs a lightweight way to express:

- what support a company likely needs next
- what milestone it should likely hit next

These records are intentionally drafts.
They are not source truth, investor outputs, or automated decisions.

## New Draft Types

### `SupportRoutingDraft`

Internal-only draft that captures the next recommended support route for one company in one report period.

Typical examples:

- product onboarding support
- customer discovery support
- metrics instrumentation support
- capital narrative preparation support

### `MilestoneDraft`

Internal-only draft that captures the next milestone OM wants the company to reach before a stronger score or capital-readiness discussion.

Typical examples:

- validate onboarding changes with current pilots
- collect repeat-usage evidence
- confirm pricing willingness across active customers

## Boundary Rules

- both draft types are internal-only in phase one
- neither draft type is source truth
- neither draft type is a final decision
- neither draft type is investor-facing
- both must remain linked to discovery, evidence, and score context when possible

## `review_ready` Discipline

These drafts can stay `draft` with minimal structure.
They can only move to `review_ready` when they include:

- linked domain score ids
- linked discovery source ids or linked evidence ids
- a rationale field

When they are bundled into a portfolio snapshot, `review_ready` also requires:

- linked score drafts are not still `draft`
- linked evidence is actually `reviewed_evidence`

That keeps the system from presenting operational suggestions as stronger than the underlying evidence.

## Example Flow

The Acme example includes:

- one explicit `SupportRoutingDraft`
- one explicit `MilestoneDraft`

Those drafts flow through:

1. local raw company input
2. reviewed-truth override application
3. portfolio snapshot assembly
4. Airtable-aligned operational export

The export layer preserves them as internal draft projections.
