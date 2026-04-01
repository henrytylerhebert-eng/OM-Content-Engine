# Ingest Layer

The ingest layer lands source exports without trying to clean them up first.

Phase 1 responsibilities:

- read Airtable-exported CSVs
- read synced CSV snapshots
- preserve source metadata
- make landed records easy to inspect and replay

Phase 1 does not try to solve dedupe, matching, or business logic at import time. That belongs in the transform layer.

