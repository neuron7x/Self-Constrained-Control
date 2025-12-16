# ADR-0001: Project scope and safety boundaries

- **Status**: Accepted
- **Date**: 2025-12-16

## Context

The repository contains a concept-heavy description referencing N1 (placeholder), biophysical simulation, resource-aware planning, and humanoid actuation. Without clear boundaries, this can be misunderstood as:
- a real medical device,
- a reverse-engineered a neurotech company stack,
- a production robotics controller,
- or a clinically validated brain simulator.

That misunderstanding creates real safety and reputational risk.

## Decision

1) The repository SHALL be positioned as a **simulation and orchestration scaffold**.
2) Hardware/clinical claims are out of scope.
3) The actuator is a stub by default; any hardware integration MUST preserve safety gates.
4) All “external facts” about companies or devices are treated as *narrative context* and are not verified by this repo.

## Consequences

- README and docs must contain explicit disclaimers.
- Tests and CI validate software properties (gates, boundedness, observability), not clinical correctness.
- If hardware integration is added, it requires a new ADR + hazard analysis + safety requirements.

## Alternatives considered

- *No boundary*: rejected due to high ambiguity and risk.
- *Pretend full production hardware system*: rejected as unverifiable.

