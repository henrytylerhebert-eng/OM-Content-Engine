# Phased Roadmap

## Phase 1

Focus: make the data easier to trust and inspect.

- land Airtable exports and CSV snapshots without changing staff workflow
- preserve raw source metadata
- define normalized schema
- add conservative transformation logic
- support manual enrichment where needed
- produce useful filtered summaries and test coverage

Success looks like:

- raw records are traceable
- mixed rows can be split into explicit entities
- basic founder, mentor, cohort, and content-readiness questions are easier to answer

## Phase 2

Focus: reduce repeat manual work.

- automate imports or sync jobs
- improve matching and deduping
- expand relationship logic
- add stronger content-readiness and audience tagging
- create repeatable reporting views

Success looks like:

- regular imports require little manual cleanup
- common reporting and segmentation workflows are scriptable
- relationship history is easier to inspect

## Phase 3

Focus: prepare downstream automation.

- expose stable export views for Codex workflows
- produce content-ready records for Canva support
- produce audience and campaign-ready records for Loomly support
- tighten scoring and segmentation logic

Success looks like:

- downstream tools consume prepared outputs instead of raw operational data
- storytelling and campaign workflows reuse the same normalized records

