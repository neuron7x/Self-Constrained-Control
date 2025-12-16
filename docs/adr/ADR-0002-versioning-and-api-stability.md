# ADR-0002: Versioning and API stability

- **Status**: Accepted
- **Date**: 2025-12-16

## Context

The repository aims to evolve quickly while avoiding “information degradation”:
- silent behavior changes,
- undocumented interface drift,
- or conceptual regressions where prior reasoning becomes invalid.

## Decision

- The project uses **Semantic Versioning (SemVer)**.
- Public APIs are those explicitly documented in `docs/API.md`.
- A change is “breaking” if it:
  - changes a public function signature,
  - changes the meaning of an enum/action index,
  - changes safety-mode semantics,
  - changes metrics schema or snapshot compatibility.

## Policy

- **PATCH**: docs, internal refactors, tests, packaging, CI adjustments; no behavior changes.
- **MINOR**: new modules/features that are backward compatible.
- **MAJOR**: breaking changes; requires migration notes.

## Consequences

- Every breaking change requires:
  1) an ADR,
  2) changelog entry,
  3) updated requirements and traceability.

## Alternatives

- No versioning: rejected.
- Calendar versioning: rejected (doesn’t communicate breaking changes).
