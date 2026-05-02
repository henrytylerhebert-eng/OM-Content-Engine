# OM Operating Systems Build

This document defines the GitHub project structure for tracking the connected build across LA.IO Overwatch, OM Content Engine, OM Venture OS, and OM Marketing OS.

GitHub Projects should be used to organize work, not to reorganize repo folders or collapse the systems into one codebase.

---

## Purpose

Track the connected operating-system build without duplicating system responsibilities or losing source-of-truth boundaries.

The project should help answer:

- What is planned?
- What is in progress?
- What is blocked?
- What has merged?
- Which repo owns the work?
- Which system layer does the work support?
- What depends on what?
- Which items are planning-only, read-only, runtime, or public-facing?

---

## Project Name

```text
OM Operating Systems Build
```

---

## Four-System Frame

### LA.IO Overwatch

Role: ecosystem intelligence, source monitoring, proof, verification, stakeholder map, ecosystem signals, and LA.IO / LED reporting truth.

### OM Venture OS

Role: founder journey, company evidence, assumptions, experiments, readiness, blockers, mentor support, and staff actions.

### OM Content Engine

Role: content planning, editorial assignments, content candidates, briefs, reporting snapshots, and operator handoff.

### OM Marketing OS

Role: Tyler's campaign and agent operating frame for recruitment, lead generation, partner development, content creation, distribution discipline, and reporting support.

---

## Recommended Project Fields

### System

- LA.IO Overwatch
- OM Content Engine
- OM Venture OS
- OM Marketing OS
- Cross-System

### Work Type

- Docs
- Source Contract
- Data Pull
- Airtable
- Agent Spec
- Runtime Code
- Tests
- Reporting
- Cleanup

### Status

- Backlog
- Ready
- In Progress
- Review
- Blocked
- Done

### Priority

- P0
- P1
- P2
- Later

### Risk

- Low
- Medium
- High

### Evidence Boundary

- Planning-only
- Read-only
- Human-review required
- Runtime behavior
- Public-facing

### Owner

- Tyler
- Codex
- Claude
- Destin
- Catherine / Teresa

---

## Recommended Views

### Command Center

Group by `System`.

Use this to see the whole build across repos.

### This Week

Filter:

```text
Status = Ready or In Progress
Priority = P0 or P1
```

Use this for execution.

### PR Review

Filter:

```text
Status = Review
```

Use this to avoid stale PR clutter.

### Agent Roadmap

Filter:

```text
Work Type = Agent Spec or Runtime Code
```

Use this for the OpenAI Agents SDK / agent build.

### Data Pull Readiness

Filter:

```text
Work Type = Data Pull or Source Contract or Airtable
```

Use this for Airtable, Overwatch, and Content Engine ingestion work.

---

## Starter Issues

These are the first issues that should exist in GitHub and be attached to the project.

1. Align README to four-system architecture
2. Add AGENTS.md repo operating instructions
3. Add LA.IO Overwatch source contract
4. Add Apollo ecosystem enrichment runbook
5. Add investor infrastructure runbook
6. Add Summer Builder 1.0 demo flow
7. Add OpenAI Agents SDK operator-layer architecture
8. Add Lead-Finding Agent spec
9. Add Content Signal Agent spec
10. Add dry-run Overwatch Operator scaffold

Some may already be complete. Mark completed items as `Done` once the matching docs or PRs exist.

---

## Starter Issue Template

Use this format when creating project issues:

```md
## Purpose

Explain the outcome this issue should produce.

## System

LA.IO Overwatch / OM Content Engine / OM Venture OS / OM Marketing OS / Cross-System

## Work Type

Docs / Source Contract / Data Pull / Airtable / Agent Spec / Runtime Code / Tests / Reporting / Cleanup

## Evidence Boundary

Planning-only / Read-only / Human-review required / Runtime behavior / Public-facing

## Acceptance Criteria

- [ ] Clear output exists
- [ ] Source-of-truth boundary is preserved
- [ ] [Unknown] handling is preserved where applicable
- [ ] No public-ready claim is inferred without review
- [ ] Tests run when code changes

## Notes

Add repo paths, PR links, or context here.
```

---

## Operating Rules

- Use GitHub Projects for coordination.
- Use repos for code and source-controlled docs.
- Do not move code just to make the project board feel cleaner.
- Do not duplicate Overwatch data structures inside OM Content Engine.
- Do not imply agents, scraping, publishing, Apollo runtime, Otter runtime, or Airtable write-back exist unless implemented.
- Keep planning-safe separate from public-ready.
- Preserve `[Unknown]` where source proof is missing.
- Keep human review central for public claims, outreach, reporting, and write-back behavior.

---

## Current Repo Scope

This document lives in OM Content Engine because that repo is currently acting as the planning and handoff layer for the four-system build.

It does not mean OM Content Engine owns the whole operating system.

OM Content Engine owns planning and handoff outputs.

The GitHub Project owns cross-system coordination.
