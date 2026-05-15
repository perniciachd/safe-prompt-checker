# Dependency Decisions

Per-dependency documentation for significant packages used in this project. Each file captures the *why* behind the choice, not just the *what*.

## Why this folder exists

When you (or anyone) returns to the codebase later, you'll wonder why a specific package was chosen over alternatives. Without docs, you re-research. With docs, you read your past self's reasoning in 30 seconds.

This is standard practice on senior engineering teams. Architecture Decision Records (ADRs) capture this at the architecture level. These dependency docs capture it at the package level.

## When to add a doc here

Every time a significant new dependency is added to `requirements.txt` or `package.json`, add a doc here.

**Significant means:** production code path, non-trivial functionality, has alternatives worth considering.

**Not significant (skip):** dev tools (pytest, ruff), well-known stdlib alternatives (requests, json), transitive dependencies.

## Index

| Package | Purpose | Added | File |
|---------|---------|-------|------|
| tenacity | Retry logic with exponential backoff | Sprint 1 Day 1 | [tenacity.md](tenacity.md) |
| structlog | Structured JSON logging | Sprint 1 Day 1 | [structlog.md](structlog.md) |

## Template

See [TEMPLATE.md](TEMPLATE.md) for the format to use when adding new dependency docs.

## Discipline rule

**Write the doc BEFORE you commit the dependency.** Not "I'll do it later." Five minutes now beats an hour of archaeology in six months.