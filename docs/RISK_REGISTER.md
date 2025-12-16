# Risk Register

This register lists *credible* risks with mitigations. It is not exhaustive.

## Scale

- **Likelihood**: 1 (rare) → 5 (likely)
- **Impact**: 1 (minor) → 5 (severe)
- **Score** = L×I

## Risks

| ID | Risk | Likelihood | Impact | Score | Mitigation | Residual |
|---|---|---:|---:|---:|---|---|
| R-001 | Misinterpretation as a real medical device or real a neurotech company integration | 3 | 5 | 15 | Explicit scope boundary in README + docs; license; no clinical claims | Medium |
| R-002 | Unsafe real-world actuation if user replaces actuator stub without safety review | 2 | 5 | 10 | Strict-mode gate stays mandatory; require ADR + hazard analysis for hardware backend | Medium |
| R-003 | Budget policy leads to starvation or unstable allocations under adversarial workloads | 3 | 3 | 9 | Treat budgets as guardrails; telemetry; unit tests; configurable policies | Medium |
| R-004 | Stochastic simulation causes flaky tests/CI | 2 | 3 | 6 | Fix seeds in tests; keep stochasticity out of deterministic unit tests | Low |
| R-005 | Performance regressions from naive vector ops or logging | 3 | 2 | 6 | Benchmarks informational; optional profiling script; keep logging levels configurable | Low |
| R-006 | Serialization risks (pickle) if used with untrusted inputs | 2 | 4 | 8 | Document: snapshots are for local debugging only; do not load untrusted pickles; consider safer format later | Medium |
| R-007 | Dependency supply-chain vulnerabilities | 3 | 4 | 12 | Pinned tooling; dependabot recommended; minimal extras; CI scan optional | Medium |

## Risk ownership and process

- Any risk with **score ≥ 10** MUST be mentioned in the README Safety section.
- Hardware integration requires:
  1) a new ADR,
  2) hazard analysis (FMEA/HARA),
  3) explicit safety requirements and traceability.
