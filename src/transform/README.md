# Transform Layer

This layer converts landed raw rows into explicit domain records.

Important first-pass behavior:

- preserve source metadata
- split mixed rows into separate records
- keep assumptions visible
- flag ambiguous cases instead of forcing a quiet classification

In Phase 1, some normalized outputs may still have unresolved foreign keys. That is acceptable while the pipeline is still proving the shape of the data.

