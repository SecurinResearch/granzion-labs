# Rogue Inspiration Analysis

This document answers: **Did the Granzion Lab take inspiration from the Rogue repo, and if so, in what ways?**

---

## 1. Short Answer

**Yes.** The lab explicitly adopts Rogue’s **attacker-centric mental model** and **scenario-driven, observable-outcome** structure. It does **not** reuse Rogue’s codebase or runtime; inspiration is conceptual and UX-oriented.

---

## 2. Where the Lab Says It’s Rogue-Inspired

Direct references in the codebase:

- **Requirements** (`docs/specs/requirements.md`, `.kiro/specs/.../requirements.md`):  
  - “adopting Rogue’s attacker-centric mental model and usability patterns”  
  - “Requirement 6: Rogue-Inspired Usability” — scenario structure, UI/TUI for selecting attacks and observing outcomes.

- **Design** (`docs/specs/design.md`, `.kiro/specs/.../design.md`):  
  - “Rogue-Inspired UX: Scenario-driven interface with observable outcomes”  
  - “Scenario Selector UI (Rogue-inspired TUI)”  
  - Section “Rogue-Inspired Interaction Model”: attacker-centric flow, scenario catalog, execution log, observable state (before/after).  
  - “Each attack scenario follows a consistent structure inspired by Rogue” (AttackScenario, AttackStep, Criterion, state_before/state_after).

- **Scenario framework** (`src/scenarios/base.py`, `src/scenarios/__init__.py`):  
  - “Inspired by Rogue’s scenario-driven interface”  
  - “Scenarios follow a Rogue-inspired structure with observable state changes.”

- **Tasks** (`docs/specs/tasks.md`):  
  - “Implement Rogue-inspired TUI” (as a task item).

- **Threat coverage** (`docs/threat_coverage.md`):  
  - “Rogue Agent Insertion” as a threat name (taxonomy term); “onboarding scenario” for coverage.

So the **intent** to be Rogue-inspired is clearly documented in requirements, design, and scenario code.

---

## 3. What Rogue Actually Is (Reference)

From the Rogue repo (README and structure):

- **Product**: “Rogue — AI Agent Evaluator & Red Team Platform.” Two modes: **Automatic Evaluation** (business policies, compliance) and **Red Teaming** (adversarial attacks, 75+ vulnerabilities, 20 techniques, CVSS, OWASP/MITRE/NIST etc.).
- **Architecture**: Client–server. **Server** (Python): evaluation and red team logic. **TUI** (Go, Bubble Tea): terminal UI. **CLI**: non-interactive for CI/CD.
- **Protocols**: A2A (HTTP), MCP (SSE/STREAMABLE_HTTP), Python (direct `call_agent(messages)` entrypoint).
- **Flow**: User selects mode (evaluation vs red team), configures agent URL and LLM, runs evaluations or red team attacks; Rogue **probes the agent** and reports pass/fail or vulnerability findings.
- **Red team**: Catalog of attacks, scenarios, report generation (e.g. CSV in `.rogue` folder), TUI for selecting and running red team scans.

So Rogue is an **evaluator that runs against your agent**; it is not a vulnerable lab. Granzion Lab is a **vulnerable target** that you attack with your own scenarios and tools.

---

## 4. What the Lab Took from Rogue (Conceptual)

| Aspect | Rogue | Granzion Lab (inspiration) |
|--------|--------|----------------------------|
| **Mental model** | Attacker/evaluator selects attacks and sees results | Same: red team operator selects scenarios and observes outcomes |
| **Scenario structure** | Scenarios with steps and outcomes | AttackScenario with setup, attack_steps, success_criteria, state_before/state_after |
| **Observable outcomes** | Reports, pass/fail, evidence | Before/after state, criteria, evidence, state_diff |
| **UI** | TUI (Go) for catalog and execution | Design doc describes a Rogue-inspired TUI (catalog, details, execution log, observable state); implemented as Dashboard + API; full TUI not done |
| **Separation** | Rogue (tester) vs your agent (target) | “Target system” (vulnerable agents/MCPs) vs “Red team interface” (Dashboard, API, scenarios) |

What the lab **did not** take:

- Rogue’s code (no shared code).
- Rogue’s server/TUI/CLI stack (lab is FastAPI + React, optional TUI).
- Rogue’s evaluation engine or vulnerability catalog (lab has its own taxonomy and scenario implementations).
- Rogue’s protocol support as a runner (lab doesn’t use Rogue to run attacks; it runs its own scenario engine).

---

## 5. Summary Table

| Question | Answer |
|----------|--------|
| Is the lab “based on” Rogue? | No — different codebase and purpose (vulnerable lab vs evaluator). |
| Is the lab “inspired by” Rogue? | Yes — attacker-centric flow, scenario-driven attacks, observable state, and intended TUI style. |
| Where is this documented? | requirements.md, design.md, scenario base and __init__, tasks.md, threat_coverage.md. |
| What’s implemented vs planned? | Scenario framework + engine + catalog and Dashboard/API are implemented; “Rogue-inspired TUI” is in design and tasks but not fully implemented. |

---

## 6. Conclusion

The Granzion Lab **has taken inspiration from the Rogue repo** in the form of:

1. **Attacker-centric mental model** — separate “red team interface” from “target system.”
2. **Scenario-driven structure** — named scenarios with setup, steps, success criteria, and observable state (before/after, evidence).
3. **Documented intent** for a Rogue-style TUI (catalog, execution log, observable state); current delivery is mainly Dashboard + API.

It has **not** copied Rogue’s implementation: the lab is an identity-first, taxonomy-driven vulnerable sandbox with its own agents, MCPs, Keycloak, and data layer, and its own scenario catalog keyed to the Agentic Threats Taxonomy.
