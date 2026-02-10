# Component: Scenarios

This document describes the **scenario framework** and **scenario catalog** in Granzion Lab: how scenarios are defined, executed, and used for red teaming.

---

## 1. Overview

**Scenarios** are predefined attack flows that demonstrate specific threats from the Agentic Threats Taxonomy. Each scenario:

- Has **metadata**: id (e.g. s01), name, category, difficulty, threat_ids, agents_involved, mcps_involved, estimated_duration.
- Defines **setup**: Prepare test users, agents, delegations, and data.
- Defines **attack steps**: A list of actions (e.g. “impersonate Bob,” “inject into memory,” “forge A2A message”).
- Defines **success criteria**: Checks that must pass for the attack to be considered successful, with evidence strings.
- Defines **state capture**: `state_before()` and `state_after()` to record observable system state; optional `observable_changes` and `state_diff` for reporting.

Execution is **deterministic** and **observable**: the engine runs setup → capture before → run steps → capture after → verify criteria → return result (with evidence and state diff).

---

## 2. Scenario Structure (Code)

- **Base types**: `src/scenarios/base.py` defines:
  - `ScenarioCategory` (Instruction, Tool, Memory, Identity & Trust, Orchestration, Communication, Autonomy, Infrastructure, Visibility).
  - `AttackStep`: description, action (callable), expected_outcome, failure_message; status, result, error; `execute()` runs the action and sets status.
  - `Criterion`: description, check (callable), evidence (callable); `verify()` runs check and evidence.
  - `AttackScenario`: id, name, category, difficulty, description, threat_ids, setup, attack_steps, success_criteria, state_before, state_after, observable_changes, agents_involved, mcps_involved, estimated_duration; runtime fields (execution_id, status, initial_state, final_state, success).
  - `ScenarioResult`: scenario_id, execution_id, success, timestamps, duration, initial_state, final_state, state_diff, step results, criterion results, evidence, errors.
- **Engine**: `src/scenarios/engine.py` — `ScenarioEngine.execute_scenario(scenario)` runs the sequence above and returns a `ScenarioResult`.
- **Discovery**: `src/scenarios/discovery.py` — `discover_scenarios()` loads scenario modules from the `scenarios/` folder (e.g. `s01_identity_confusion.py`, …) and returns a list of `AttackScenario`; `get_scenario_by_id()` finds one by id (e.g. s01).

---

## 3. Scenario Catalog (Summary)

| ID | Name | Category | Main threats |
|----|------|----------|--------------|
| s01 | Identity Confusion | Identity & Trust | Delegation abuse, impersonation |
| s02 | Memory Poisoning | Memory | RAG/vector poisoning |
| s03 | A2A Message Forgery | Communication | Message forgery, trust boundaries |
| s04 | Tool Parameter Injection | Tool | Parameter injection |
| s05 | Workflow Hijacking | Orchestration | Task delegation corruption |
| s06 | Context Window Stuffing | Memory | Session/context manipulation |
| s07 | Jailbreaking (LiteLLM) | Instruction | Jailbreaks, safety bypass |
| s08 | Unauthorized Infrastructure | Infrastructure | Unauthorized deploy/exec |
| s09 | Audit Log Manipulation | Visibility | Log tampering, untraceability |
| s10 | Cross-Agent Memory | Memory | Cross-session contamination |
| s11 | Goal Manipulation | Autonomy / Orchestration | Goal hijack |
| s12 | Credential Theft | Identity & Trust / Tool | Credential exfil |
| s13 | Privilege Escalation (Infra) | Tool / Identity | Over-privileged tools |
| s14 | Container Escape | Infrastructure | Runtime/container boundary |
| s15 | Detection Evasion | Visibility / Autonomy | Evading monitoring |

Exact threat IDs and steps are in each file under `scenarios/` and in `docs/threat_coverage.md`.

---

## 4. Execution Flow (Recap)

1. **Select**: User or API selects scenario by id (e.g. s01).
2. **Load**: Engine discovers or loads the scenario module and gets the `AttackScenario` instance.
3. **Setup**: `scenario.setup()` creates test identities, delegations, records (in DB).
4. **Before**: `scenario.state_before()` returns a dict (e.g. counts, key records).
5. **Steps**: For each `AttackStep`, `step.execute()` runs `step.action()`; status and result are stored.
6. **After**: `scenario.state_after()` returns a dict.
7. **Criteria**: For each `Criterion`, `criterion.verify()` runs `check()` and `evidence()`; all must pass for scenario success.
8. **Result**: Engine builds `ScenarioResult` (state diff, step results, criterion results, evidence, errors) and returns it to the API/Dashboard.

---

## 5. Rogue-Inspired Structure

The design is **Rogue-inspired** in the sense of:

- **Scenario-driven**: Attacks are organized as named scenarios with clear steps.
- **Observable outcomes**: Before/after state and criteria provide concrete evidence, not just “it failed.”
- **Catalog**: A list of scenarios (eventually selectable from a TUI or Dashboard) with category and difficulty.

The lab does **not** use Rogue’s codebase; it adopts the mental model (attacker selects scenario, runs it, sees outcomes).

---

## 6. Adding a New Scenario

1. Add a Python file under `scenarios/` named e.g. `s16_my_attack.py`.
2. Implement:
   - `setup_*` and step functions that use DB, MCPs, or API.
   - `state_before` / `state_after` callables.
   - A list of `AttackStep` and `Criterion` instances.
   - An `AttackScenario` instance with all required fields (id, name, category, threat_ids, etc.).
3. Ensure the scenario is discoverable (discovery scans `s*.py` and loads the scenario object).
4. Document threat IDs and mapping in `docs/threat_coverage.md` and `docs/VULNERABILITIES.md` if new vulnerabilities are used.

See `docs/scenario-creation-guide.md` for detailed steps.

---

## 7. References

- Base and engine: `src/scenarios/base.py`, `src/scenarios/engine.py`, `src/scenarios/discovery.py`, `src/scenarios/state.py`
- Catalog: `scenarios/s01_*.py` … `s15_*.py`
- Coverage: `docs/threat_coverage.md`
- Creation guide: `docs/scenario-creation-guide.md`
