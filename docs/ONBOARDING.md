# Granzion Lab — Onboarding

One-page guide to get running, understand the system, and find the right docs.

---

## 1. Get running (minutes)

- **[QUICKSTART.md](../QUICKSTART.md)** (repo root) — Zero-to-hero setup: Docker, `full_setup`, dashboard.
- **TL;DR**: `docker compose up -d` → `docker compose exec granzion-lab python scripts/full_setup.py` → run scenarios or open API at `http://localhost:8001/docs`.

---

## 2. Understand the system (architecture & roadmap)

**CTO briefs** (executive-level; read in order if presenting to leadership):

| Order | Document | Purpose |
|-------|----------|---------|
| 1 | [CTO-01 — Executive summary & current state](architecture-docs/CTO-01-EXECUTIVE-SUMMARY-AND-CURRENT-STATE.md) | What the lab is, what exists, taxonomy fit |
| 2 | [CTO-02 — Diagrams & implementation](architecture-docs/CTO-02-DIAGRAMS-EXPLAINED-AND-CURRENT-IMPLEMENTATION.md) | What each diagram means, where it lives in code |
| 3 | [CTO-03 — Gaps, improvements, roadmap](architecture-docs/CTO-03-GAPS-IMPROVEMENTS-AND-ROADMAP.md) | P0–P3 actions, verification, out-of-scope |

**Diagrams & workflow:**

- [ARCHITECTURE_DIAGRAM.md](architecture-docs/ARCHITECTURE_DIAGRAM.md) — Mermaid: architecture, identity, data flow.
- [WORKFLOW_DIAGRAM.md](architecture-docs/WORKFLOW_DIAGRAM.md) — Mermaid: setup, identity resolution, scenario execution, A2A.
- [WORKFLOW.md](architecture-docs/WORKFLOW.md) — End-to-end workflow in prose.
- [ARCHITECTURE.md](architecture-docs/ARCHITECTURE.md) — Layers, components, design principles.

**Component deep-dives:** [architecture-docs/README.md](architecture-docs/README.md) — 01-agents, 02-keycloak, 03-mcps, 04-data-layer, 05-scenarios, 06-a2a-and-identity.

---

## 3. Identity & Keycloak

- **[KEYCLOAK_STATE_AND_IDENTITY_TESTING.md](architecture-docs/KEYCLOAK_STATE_AND_IDENTITY_TESTING.md)** — Expected state after `full_setup` (realm, users, service accounts), how to get a token, **identity testing modes**:
  - **Bearer token** — Real user (e.g. Alice) via Keycloak JWT.
  - **Manual context** — Red team: pass `identity_context` in request body (user_id, agent_id, permissions).
  - **Guest** — No auth → lab assigns Guest identity (minimal permissions).
- **Health**: `GET /health/identity` — Keycloak reachable, realm exists, token obtainable.
- [keycloak-automation.md](keycloak-automation.md) — How Keycloak is automated and seeded.

---

## 4. Scenarios & threat coverage

- **[threat_coverage.md](threat_coverage.md)** — Which threats (1–54) are testable and which scenarios (S01–S16) cover them.
- **[scenario-creation-guide.md](scenario-creation-guide.md)** — How to add or modify attack scenarios.
- **Run scenarios**: `python run_scenario.py S01`, or `python run_all_scenarios.py`; see [QUICKSTART](../QUICKSTART.md).

---

## 5. Development & testing

- **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** — Local vs Docker, unit vs integration/scenario tests, Keycloak & identity testing, CI.
- **CI**: `.github/workflows/ci.yml` — Unit tests on every push/PR; integration + scenario success tests (S01–S16) with Docker.

---

## 6. Boundaries & evidence

- **[LAB_BOUNDARIES.md](LAB_BOUNDARIES.md)** — What is out of scope (e.g. full production security, full Rogue parity) and why.
- **[EVIDENCE_SCHEMA.md](EVIDENCE_SCHEMA.md)** — How red team evidence (actor, action, resource, timestamp) is structured and stored.

---

## Quick reference

| I want to… | Go to |
|------------|--------|
| Run the lab in 5 minutes | [QUICKSTART](../QUICKSTART.md) |
| Explain the lab to leadership | CTO-01 → CTO-02 → CTO-03 |
| See architecture/workflow diagrams | [ARCHITECTURE_DIAGRAM](architecture-docs/ARCHITECTURE_DIAGRAM.md), [WORKFLOW_DIAGRAM](architecture-docs/WORKFLOW_DIAGRAM.md) |
| Test as a specific user/agent (no Keycloak) | [KEYCLOAK_STATE_AND_IDENTITY_TESTING](architecture-docs/KEYCLOAK_STATE_AND_IDENTITY_TESTING.md) § Identity testing |
| See which scenarios cover which threats | [threat_coverage.md](threat_coverage.md) |
| Add or run scenarios | [scenario-creation-guide.md](scenario-creation-guide.md), [QUICKSTART](../QUICKSTART.md) |
| Develop or run tests locally | [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) |
| Know what we don’t do | [LAB_BOUNDARIES.md](LAB_BOUNDARIES.md) |
