# Architecture

## Purpose

OM Content Engine is a secondary intelligence system for Opportunity Machine.

It exists to make messy operational data more usable without forcing staff to change the workflow they already use. The current Airtable and spreadsheet setup remains the operating source. This repo ingests exports from that source, preserves them, and reshapes them into cleaner records for analysis, segmentation, and later automation.

## Core Constraints

- Protect the operational source
- Keep imports one-way in Phase 1
- Expect messy source data
- Do not require heavy manual re-entry
- Avoid enterprise complexity

## First-Pass Architecture

```text
Airtable exports / CSV syncs
        |
        v
data/raw/ landed files + source metadata
        |
        v
src/ingest/ import helpers
        |
        v
src/transform/ normalization logic
        |
        v
data/processed/ normalized outputs
        |
        v
src/enrich/ derived tags, readiness flags, and segments
        |
        v
src/reporting/ summaries and downstream export views
```

## Layers

### Raw Source Layer

This layer stores landed exports exactly as they arrived, plus metadata:

- source table name
- source record id when available
- import timestamp
- file path
- row hash

This layer should be append-friendly and easy to inspect.

### Transformed Layer

This layer converts mixed operational rows into explicit domain entities:

- organizations
- people
- affiliations
- programs
- cohorts
- participation
- mentor profiles
- interactions
- content intelligence seeds

Transformation code should preserve traceability back to source records and should flag ambiguity instead of quietly inventing a rule.

### Enrichment Layer

This layer adds derived fields that are useful but not operational truth:

- audience tags
- content readiness flags
- spotlight priority
- local mentor matching hints
- campaign segmentation helpers

Enrichment should never overwrite raw or normalized source facts.

## Why Python + SQLModel

Python is the practical choice here because it fits export processing, normalization, and analytics work without much friction. SQLModel keeps schema definitions readable and close to ordinary Python code. It also leaves room to start with SQLite locally and move to Postgres later if the system grows.

## Database Position

The scaffold does not lock the project into a production database yet.

The first pass assumes:

- SQLite is fine for local development and early iteration
- the schema should stay Postgres-friendly
- the real value right now is clean structure and reliable transforms, not database sophistication

## Phase 1 Boundaries

Phase 1 includes:

- raw ingest helpers
- normalized schema definitions
- starter transformation modules
- manual enrichment support
- basic reporting helpers

Phase 1 does not include:

- UI
- authentication
- write-back sync
- workflow automation
- marketing tool integration

## Future Integration Direction

### Canva

The system should eventually expose profile and story records that are already filtered and structured for content production. Canva should consume prepared outputs, not raw operational tables.

### Loomly

The system should eventually expose audience segments, message pillars, and spotlight-ready records that can support campaign planning and post creation. Loomly should sit downstream of normalized and enriched data.

