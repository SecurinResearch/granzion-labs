# Granzion Lab — Workflow Explanation

This document explains **how the lab works** from a user/operator perspective: setup, running agents, running scenarios, and how data and identity flow. Use it to onboard new team members or explain the lab to stakeholders.

---

## 1. One-Sentence Summary

**Operators use the Dashboard or API to run attack scenarios against a deliberately vulnerable multi-agent system (agents + MCPs + Keycloak + PostgreSQL/pgvector/PuppyGraph); each scenario proves one or more taxonomy threats by showing observable state changes.**

---

## 2. Workflows at a Glance

| Workflow | Who | What happens |
|----------|-----|----------------|
| **Lab setup** | Dev/Ops | Start Docker, run full_setup, optionally enrich data. |
| **Run a scenario** | Red teamer | Pick scenario → engine runs setup → steps → state capture → criteria check → evidence. |
| **Chat with an agent** | Red teamer / Tester | Send prompt to an agent (e.g. Orchestrator) with identity context → agent uses MCPs and LLM → response returned. |
| **Identity flow** | System | Every request carries user/agent/delegation; MCPs and DB record who did what. |

---

## 3. Lab Setup Workflow

1. **Clone and configure**
   - Clone repo, `cd granzion-lab`, copy `.env.example` to `.env`.
   - Set at least `LITELLM_URL` and `LITELLM_API_KEY` (or use local LiteLLM with profile).

2. **Start infrastructure**
   - `docker compose up -d` (optionally `--profile local-litellm` for LiteLLM).
   - Waits for Postgres (and Keycloak, PuppyGraph) to be up.

3. **Initialize lab**
   - `docker compose exec granzion-lab python scripts/full_setup.py`
   - Creates/updates DB schema, Keycloak realm/clients/roles/users, agent identities, Agent Cards.
   - Ensures identities and delegations exist for scenarios and agents.

4. **Optional: enrich data**
   - `docker compose exec granzion-lab python scripts/enrich_lab_data.py`
   - Adds more app_data, sample RAG content, etc., for richer red team tests.

5. **Access**
   - Dashboard: `http://localhost:5173` (after `npm run dev` in `frontend/`).
   - API: `http://localhost:8001` (docs at `/docs`).
   - Keycloak Admin: `http://localhost:8080`.
   - PuppyGraph UI: `http://localhost:8081`.

---

## 4. Scenario Execution Workflow

Scenarios are the **main red team path**: predefined attacks that demonstrate taxonomy threats.

1. **Select scenario**
   - From Dashboard “Scenarios” or API `GET /scenarios`.
   - Example IDs: `s01`, `s02`, … `s15` (Identity Confusion, Memory Poisoning, A2A Forgery, etc.).

2. **Run scenario**
   - Dashboard: click “Run” for a scenario; or API: `POST /scenarios/{id}/run` (or equivalent run endpoint).
   - Backend uses `ScenarioEngine` in `src/scenarios/engine.py`.

3. **Engine steps (in order)**
   - **Setup**: Create test users/agents/delegations/data (e.g. Alice, Orchestrator, Executor, a test record).
   - **Capture state before**: Call `state_before()` (e.g. audit log count, delegation count, specific record).
   - **Attack steps**: Execute each `AttackStep` (e.g. “impersonate Bob”, “create delegation”, “inject into memory”). Steps call MCPs, DB, or identity APIs.
   - **Capture state after**: Call `state_after()`.
   - **Success criteria**: For each `Criterion`, run `check()` and `evidence()`. Scenario **succeeds** only if all criteria pass.
   - **Result**: `ScenarioResult` with initial_state, final_state, state_diff, step results, criterion results, evidence, errors.

4. **Outcome**
   - Dashboard or API shows: success/failure, before/after state, evidence lines, and which step/criterion failed if any.
   - Red teamer uses this to validate that a threat is exploitable and observable.

---

## 5. Agent Chat Workflow

Used to drive an agent (e.g. Orchestrator) with natural language and see how it uses tools and identity.

1. **Request**
   - `POST /agents/{agent_id}/run` with body `{ "prompt": "..." }`.
   - Optional: `Authorization: Bearer <token>` or body `identity_context` for identity-first testing.

2. **Identity resolution (backend)**
   - If Bearer token: parse via Keycloak, build `IdentityContext` (user_id, permissions, etc.).
   - Else if `identity_context` in body: use it (ensure identity exists in DB).
   - Else: **Guest** context (fixed UUID, minimal permissions).

3. **Agent run**
   - Resolve agent by id (orchestrator, researcher, executor, monitor or UUID).
   - Create **fresh** agent instance with the resolved identity context (for Zero-Trust style testing).
   - Set `identity_context_var` (context variable); call `agent.arun(prompt)`; clear context.
   - Agent uses LiteLLM for reasoning and MCP tools (Comms, Identity, Agent Card, Memory, Data, Infra) with the same identity context.

4. **Response**
   - API returns agent response text, agent_id, status, and identity (for inspection).

---

## 6. Identity Flow (System-Wide)

- **Source**: Keycloak (JWT) or manual/guest context.
- **Structure**: `IdentityContext`: user_id, agent_id, delegation_chain, permissions, trust_level, keycloak_token (if any).
- **Propagation**: Stored in a context variable per request; passed into MCP tool wrappers so every MCP call is attributed.
- **Persistence**: Audit logs and messages store user_id, agent_id, delegation_chain (or equivalents) so “who did what” is observable for red team evidence.
- **A2A**: When Orchestrator sends a message to Researcher/Executor, message payload can include delegation_chain; receiver can trust or abuse it (intentionally weak for testing).

---

## 7. Data Flow (Simplified)

- **User/Dashboard** → API → **Agent** (Agno) → **MCP tools** → **PostgreSQL / pgvector / PuppyGraph**.
- **LiteLLM** is used by the agent for every LLM call (no direct provider calls from the app).
- **State capture** in scenarios reads from DB/graph (and optionally memory) to build before/after snapshots and diffs.

---

## 8. How This Supports Red Teaming for the Taxonomy

- **Scenarios** map to threat IDs and categories (see `threat_coverage.md` and scenario files).
- **Observable state** (before/after, criteria, evidence) shows that a threat was exploitable, not just that the app “errored”.
- **Identity-first** design means many attacks go through identity (impersonation, delegation abuse, weak Agent Cards, etc.).
- **Unified data** (relational + vector + graph) allows tests for SQL injection, RAG poisoning, and graph reconnaissance in one lab.

---

## 9. Quick Reference

| I want to… | Do this |
|------------|--------|
| Run the lab | `docker compose up -d` then `full_setup.py` |
| Run one scenario | Dashboard → Scenarios → Run, or call scenario run API |
| Chat with Orchestrator | `POST /agents/orchestrator/run` with `{"prompt":"..."}` |
| See what’s vulnerable | Read `docs/VULNERABILITIES.md` and `docs/threat_coverage.md` |
| Add a new scenario | Add `scenarios/sXX_name.py` following `scenarios/base.py` and discovery; register in discovery. |

For deeper technical detail, see [ARCHITECTURE.md](ARCHITECTURE.md) and the component docs in this folder.
