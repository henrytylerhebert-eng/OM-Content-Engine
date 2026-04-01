# Editorial Planning

This pack turns `content_briefs.*` into one weekly internal planning view.

It is for deciding:

- what to use now
- what needs light review to unlock
- what should be held this cycle

It is not a publishing queue.

## Where It Is Written

Each standard pipeline run now writes:

- `editorial_plan.json`
- `editorial_plan.md`

into the run directory, such as `data/processed/local_run/`.

## Buckets

- `use_now`: ready for drafting this cycle because the brief is public-ready or already backed by reviewed truth with no blocking review burden
- `needs_review`: useful candidate, but still needs a quick confirmation, override, or review step before drafting
- `hold`: keep out of this cycle because trust is still too weak or the review burden is too heavy

Each brief appears in exactly one bucket.

## How To Use It Weekly

1. Run the pipeline.
2. Open `editorial_plan.md`.
3. Start with `Use Now` and assign 2 to 3 pieces.
4. Pull supporting detail from `content_briefs.md`.
5. Use `Needs Review` as the short unlock list for quick overrides or confirmations.
6. Leave `Hold` alone until the trust picture improves.

## Operating Rule

`use_now` means ready for drafting work inside OM.

It does not mean:

- approved for public publishing
- approved for scheduling
- safe for external automation

`public_ready` stays stricter and still depends on reviewed truth upstream.
