# Operating Principles

- Keep the operational Airtable and spreadsheet workflow intact.
- Treat this repo as a secondary intelligence layer, not a replacement system.
- Prefer one-way imports first. Write-back is out of scope until there is a very clear reason.
- Preserve raw source data and metadata before transforming anything.
- Normalize mixed records into explicit entities instead of carrying ambiguity forward.
- Flag unclear cases. Do not silently invent business rules.
- Keep code readable. Small startup support teams need maintainable scripts more than clever architecture.
- Favor traceability over perfection. It should always be possible to explain where a record came from.
- Keep enrichment separate from source-derived truth.
- Build only what supports real reporting, matching, segmentation, and storytelling needs right now.

