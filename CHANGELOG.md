# Changelog

All notable changes to this project will be documented in this file.

## 0.1.0 (2025-12-16)

Initial public scaffold for **Self-Constrained-Control**:

- Core orchestration loop with explicit state, budgeting, safety modes, and persistence.
- Bio-inspired neural interface simulator (HH-style dynamics) with numerical stabilization helper (`vtrap`).
- Stability-aware planner module (RL + control-theory checks) and actuator stub.
- Runtime contracts and invariant IDs + traceability-oriented docs.
- CI, tests, linting, and repo hygiene files (security policy, contributing, code of conduct).
