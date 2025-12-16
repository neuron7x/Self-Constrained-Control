# Glossary

This glossary fixes terminology to reduce semantic drift as the repository evolves.

## Core concepts

- **Action**: a discrete command requested by the operator (e.g., `move_arm`, `plan_route`, `stop`).
- **Intent**: a discrete label decoded from neural activity intended to match an action.
- **Control loop**: the per-cycle pipeline **sense → decode → plan → budget → act → observe**.
- **Safety mode**: actuator policy level controlling which actions are permitted.
- **Budget**: an abstract resource token used to bound compute and prevent uncontrolled work.
- **SLA (latency)**: a time threshold per module used to detect and penalize chronic overruns.
- **Anomaly (latency)**: a statistically unusual latency sample detected by z-score.
- **Circuit breaker**: reliability primitive that blocks calls after repeated failures.
- **Watchdog**: progress monitor that terminates execution if the loop stalls.

## Bio-simulation terms (in this repo)

- **Population rate**: a vector of firing rates (Hz) per channel. In this repo it is simulated.
- **Channel**: an index in the rate vector (default 1024) representing an abstract recording unit.
- **Metabolic coupling**: a mapping from simulated activity to an energy proxy used to influence budgets.
- **Neuromodulation**: a simplified reward/stress modulation hook; not a biological claim.

## Units and conventions

- **Battery**: percentage, `[0, 100]`.
- **User energy**: percentage, `[0, 100]` (a simulation proxy).
- **Latency**: seconds in code, sometimes displayed in milliseconds.
- **Rates**: Hz, bounded to a configured range.

## Normative keywords

The words **MUST**, **SHALL**, **SHOULD**, **MAY** follow RFC 2119-style intent:
- **MUST/SHALL**: mandatory for correctness/safety.
- **SHOULD**: recommended unless a documented exception exists.
- **MAY**: optional.
