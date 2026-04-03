# Portfolio Override Authoring

## Purpose

This helper gives phase-one operators a safer way to create and update portfolio reviewed-truth overrides without hand-editing JSON.

It keeps the system file-backed and internal-only.
It does not turn the repo into a workflow app.

## Command

Use:

```bash
python3 -m src.reporting.portfolio_override_tool --help
```

The helper writes to `data/reviewed_truth/portfolio_overrides.json` by default.
You can point it at the tracked example file with `--overrides-file`.

## Supported Authoring Actions

Phase one supports these operator-safe actions:

- `evidence-review`
- `domain-score-adjustment`
- `queue-resolution`
- `internal-draft-approval`

Each command creates or updates one patch-only rule in the override file.

## Example Commands

Promote one evidence item to reviewed evidence:

```bash
python3 -m src.reporting.portfolio_override_tool evidence-review \
  --overrides-file data/reviewed_truth/portfolio_example_overrides.json \
  --evidence-id evidence:acme_customer_signal \
  --reviewed-by portfolio_operator \
  --review-notes "Reviewed customer interview signal for the phase-one example."
```

Adjust one domain score after review:

```bash
python3 -m src.reporting.portfolio_override_tool domain-score-adjustment \
  --overrides-file data/reviewed_truth/portfolio_example_overrides.json \
  --score-id domain_score:org_acme_automation:customer_risk \
  --reviewed-by portfolio_operator \
  --raw-score 4 \
  --confidence moderate \
  --evidence-level 3 \
  --score-status review_ready \
  --review-notes "Adjusted from reviewed customer evidence."
```

Resolve a review queue item tied to one evidence id:

```bash
python3 -m src.reporting.portfolio_override_tool queue-resolution \
  --overrides-file data/reviewed_truth/portfolio_example_overrides.json \
  --linked-evidence-item-id evidence:acme_customer_signal \
  --reviewed-by portfolio_operator \
  --resolution-note "Evidence promotion completed."
```

Approve an internal-only draft:

```bash
python3 -m src.reporting.portfolio_override_tool internal-draft-approval \
  --overrides-file data/reviewed_truth/portfolio_example_overrides.json \
  --target internal_report_draft \
  --record-id internal_report:org_acme_automation:2026_q2 \
  --reviewed-by portfolio_operator \
  --review-notes "Approved for internal operating use."
```

## Safety Rules

- The helper writes patch-only overrides only.
- It does not support suppression.
- It does not support external approval states.
- It does not edit raw discovery input files.
- Re-running the same command with the same target record updates the same rule id by default.

## Why This Is The Right Phase-One Shape

This is the smallest useful operator workflow:

- raw inputs stay separate
- durable human decisions survive reruns
- override rules stay inspectable on disk
- the repo stays internal and reviewable

The next layer can build from this without committing to a UI too early.
