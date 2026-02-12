# Lab Boundaries and Out-of-Scope

This document states what the Granzion Lab **explicitly does not test** or support.

## Out-of-Scope Topics

| Topic | Reason |
|-------|--------|
| **Training / fine-tuning data poisoning (#12)** | Requires a model fine-tuning pipeline; out of scope for a runtime-only lab. |
| **Dormant autonomy (#42)** | Requires long-running async execution and delayed triggers; not modeled in the current agent lifecycle. |
| **Supply chain (#47)** | Concerns external dependencies (e.g. poisoned packages); not part of the current threat surface. |
| **Production-grade security** | The lab is intentionally vulnerable for red team exercises; no intention to harden for production. |
| **Full Rogue parity** | We took inspiration (scenario-driven, observable outcomes); we do not implement Rogue's evaluation engine or TUI. |
| **Full 54/54 threat coverage** | A subset of taxonomy threats are testable today; we close high-priority gaps and document the rest. |

## Reference

- Threat taxonomy and coverage: [threat_coverage.md](threat_coverage.md)
