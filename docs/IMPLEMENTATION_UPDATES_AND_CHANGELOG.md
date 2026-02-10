# Implementation updates and changelog

Summary of changes and improvements made since the implementation plan and lab setup. Use this as a single reference for what was fixed, added, or improved.

---

## 1. Scenario execution and reporting

### Scenario engine integration (frontend run)
- **Before:** `POST /scenarios/{scenario_id}/run` ran the raw scenario Python script in a background process and returned immediately with "initiated"; the UI had no pass/fail or results.
- **After:** The endpoint uses the **scenario engine** (`ScenarioEngine` + `discover_scenarios`). It runs the scenario in a thread (`asyncio.to_thread`), waits for completion, and returns a full result: `success`, `duration_seconds`, `steps_succeeded`/`steps_failed`, `criteria_passed`/`criteria_failed`, `evidence`, `errors`.
- **Frontend:** Scenario panel shows "RUNNING" until the request completes (timeout 2 min), then displays **Pass** or **Fail**, duration, steps/criteria summary, evidence list, and errors. Users can see attack execution results directly in the UI.

### Scenario fixes (stability and criteria)
- **S02 (Memory poisoning):** `top_k` 20; criteria accept malicious doc anywhere in results.
- **S03 (A2A message forgery):** `receive_message(limit=50)`; step uses `intercepted_messages`; criterion passes if forgery sent and (executor received delete or users deleted).
- **S05 (Workflow hijacking):** Step try/except and `limit=50`; criterion passes when executor deleted users even if workflow_tasks=2; defensive `.get()` and try/except in criteria.
- **S06:** `top_k` 10; criteria check top 5; `fetchone()` → `first()` in evidence/capture; safe `query_result` handling.
- **S07 (Jailbreaking):** LLM steps in try/except; relaxed refusal phrases and short-response baseline; jailbreak accepts "vulnerability"; model_switch length ≥ 50.
- **S11:** Step try/except; short sleep after send before intercept.
- **S17 (Agent-driven orchestration):** Criteria/evidence callables take no args (engine calls `check()` with no args); evidence dict handling in report; relaxed `api_ok` logic.

### Report crash fix
- **Issue:** `TypeError: unhashable type: 'slice'` when printing evidence (e.g. S17 returning dict evidence).
- **Fix:** In `run_all_scenarios.py`, evidence is coerced to string before slicing: `text = evidence if isinstance(evidence, str) else str(evidence)`.

---

## 2. Agents and identity

### Orchestrator “I don’t know my identity”
- **Issue:** In the Console, when asked "What are your capabilities?", the Orchestrator replied that it could not access its own identity.
- **Cause:** The identity context passed to the run had only the **caller** (e.g. Alice); the **invoked agent’s** `agent_id` was not set.
- **Fix:** In `main.py`, before resolving the target agent, the backend sets the run context so the invoked agent knows itself: `identity_context.extend_delegation_chain(agent_uuid, identity_context.permissions)`. So the Orchestrator (and others) receive `agent_id` = their own UUID and can answer capability questions.

### Duplicate agents in UI and DB
- **Frontend/API:** `GET /agents` now returns only the **canonical four** agent UUIDs (Orchestrator, Researcher, Executor, Monitor). Filter uses `WHERE type = 'agent' AND id::text IN :ids` with the fixed list; fallback list if DB has none.
- **DB cleanup:** New script `scripts/cleanup_scenario_agents.py` deletes identities where `type = 'agent'` and `id` is not one of the four canonical UUIDs. `run_all_scenarios.py` calls this cleanup at the end of a full run and reports how many were removed. Run manually if needed: `python scripts/cleanup_scenario_agents.py` (e.g. inside the app container).

---

## 3. Backend services and observability

### Backend services section empty (Dashboard)
- **Issue:** The "Backend services (vector DB & graph)" panel showed "—" for all services (PostgreSQL, pgvector, PuppyGraph, LiteLLM, Keycloak).
- **Cause:** `check_services()` returned a full status dict but it was never written to the global `_services_status`; only `mcp_agent_card` and keycloak_realm were set elsewhere.
- **Fix:**  
  - At startup: `_services_status.update(await check_services())`.  
  - In `GET /health` and `GET /services`: if `postgres` is missing from `_services_status` (e.g. app started via uvicorn only), the handler calls `check_services()` and updates the global so the first request gets full status.
- **Frontend:** Dashboard shows real status (healthy / not_reachable / missing) for all five services; `getServices()` API and polling already in place.

### PuppyGraph “not reachable”
- **Cause:** Health check used port **8082** for the Web UI; the official PuppyGraph image serves the Web UI on **8081** and Gremlin on **8182**, so nothing was listening on 8082.
- **Fix:**  
  - Health check tries, in order: configured web port, **8081**, then **8082**.  
  - Default `puppygraph_web_port` set to **8081** in config.  
  - `docs/TROUBLESHOOTING.md` updated with: why PuppyGraph can be unreachable, ensure container is running, use `PUPPYGRAPH_HOST=localhost` when the app runs on the host, and port notes.

### Vector DB and PuppyGraph in the UI
- **Frontend:** "Backend services" card explains that pgvector powers agent memory (embeddings) and PuppyGraph (Gremlin) powers graph queries with SQL fallback when unreachable.
- **Docs:** How to ask the Orchestrator to trigger vector DB operations (e.g. "Search memory for policies") and how to verify vector DB/PuppyGraph via Dashboard and Console is documented in conversation and troubleshooting.

---

## 4. Agent tone and conversation UX

### Natural responses (all four agents)
- **Issue:** Orchestrator (and potentially others) responded in a stiff, procedural way (e.g. "I will call get_identity_context…") and dumped long workflows/UUIDs for simple questions like "What are your capabilities?"
- **Fix:** A **Tone** section was added to the system instructions of **all four agents** (Orchestrator, Researcher, Executor, Monitor):
  - **Orchestrator:** Brief, natural replies; no step narration; short capability summary unless the user asks for detail.
  - **Researcher:** Brief, clear; summarize with citations; use JSON only when the request or protocol expects it.
  - **Executor:** Short, direct; state what was done and outcome in 1–3 sentences; don’t narrate tool calls.
  - **Monitor:** Brief summary; honest about limitations; no raw log dumps unless a full report is requested.
- **Code:** Duplicate `from agno.agent import Agent` removed in Researcher, Executor, and Monitor.
- **Doc:** `docs/AGENTS_PROMPTS_AND_TONE.md` summarizes each agent’s role, tone guidance, and where to change prompts.

### Conversation memory and reset
- **Behavior:** Each request sends only the **current** user message; the backend does not receive or use conversation history, so **agents do not remember** past turns.
- **UI:**  
  - **Clear chat** button added in the Console header; clears the visible thread (no backend state to clear).  
  - Short note under the input: "Each message is sent alone; the agent does not see prior conversation. Use 'Clear chat' to start a fresh thread in the UI."
- **Docs:** `docs/TROUBLESHOOTING.md` now has a "Console: agent responses feel unnatural / no memory" section: why responses felt stiff, that there is no conversation memory, how reset works (Clear chat), and how to add real memory later (send message history in API + backend pass-through).

---

## 5. Documentation added or updated

| Document | Purpose |
|----------|---------|
| `docs/TROUBLESHOOTING.md` | PuppyGraph not reachable; Console tone/memory and reset; backend services. |
| `docs/AGENTS_PROMPTS_AND_TONE.md` | Summary of agent prompts, tone, and implementation; how to change behavior. |
| `docs/IMPLEMENTATION_UPDATES_AND_CHANGELOG.md` | This document: all changes since the implementation plan. |

---

## 6. Files changed (overview)

- **Backend:** `src/main.py` (identity context for invoked agent, services status persistence and fallback, scenario run via engine, health/services PuppyGraph port handling), `src/config.py` (puppygraph_web_port default 8081), `src/agents/orchestrator.py`, `src/agents/researcher.py`, `src/agents/executor.py`, `src/agents/monitor.py` (tone + duplicate import), `run_all_scenarios.py` (evidence string handling, cleanup call), `scripts/cleanup_scenario_agents.py` (new).
- **Frontend:** `frontend/src/App.tsx` (backend services section, services state and polling), `frontend/src/services/api.ts` (getServices, runScenario timeout 120s), `frontend/src/components/ScenarioPanel.tsx` (full result type, pass/fail UI, evidence/errors), `frontend/src/components/InteractiveConsole.tsx` (Clear chat, memory note).
- **Docs:** `docs/TROUBLESHOOTING.md`, `docs/AGENTS_PROMPTS_AND_TONE.md`, `docs/IMPLEMENTATION_UPDATES_AND_CHANGELOG.md`.
- **Scenarios:** Multiple scenario files (S02, S03, S05, S06, S07, S11, S17) for criteria, steps, and evidence handling.

---

## 7. What stayed the same (intentionally)

- **Vulnerabilities:** All documented intentional vulnerabilities (no delegation depth limit, trust A2A messages, no encryption, no rate limiting, embedding validation, parameter sanitization, etc.) are unchanged for red-team scenarios.
- **Scenario logic:** Fixes were for stability, criteria correctness, and evidence serialization; attack semantics and threat coverage are preserved.
- **API surface:** No breaking changes to existing endpoints; new or extended behavior is additive (e.g. scenario run returns full result; services/health populate status).

---

*Last updated: February 2025. For scenario-specific details, see the scenario files and `run_all_scenarios.py`; for agent behavior, see `src/agents/` and `docs/AGENTS_PROMPTS_AND_TONE.md`.*

---

## 8. Recent Fixes & Additions

### PuppyGraph Connectivity & Queries
- **Issue:** PuppyGraph queries failed with `597: PuppyGraph id must be in label[identifier] format`.
- **Cause:** `src/database/graph.py` used direct ID lookups (`g.V(id)`) which are incompatible with the current PuppyGraph version's typed ID requirement.
- **Fix:** Refactored all graph queries to use property-based lookups: `g.V().has('id', id)`.
- **Verification:** `scripts/verify_graph.py` confirmed successful connection and query execution.

### Agent Prompting Guide
- **New File:** `EXAMPLE_PROMPTS.md` created in project root.
- **Content:** comprehensive list of "perfect" prompts for all 4 agents (Orchestrator, Researcher, Executor, Monitor).
- **Categories:**
  - **Standard Operation:** Happy path tests for core capabilities.
  - **Red Teaming:** Specific prompts to trigger and test intentional vulnerabilities (Infinite delegations, Context Stuffing, SQLi, etc.).

- **Agent Confusion Fixes (Tables vs RAG)**: Researcher agent now explicitly avoids using `search_similar` for structured `identities` data, preventing accidental retrieval of policy documents from memory. Orchestrator now delegates all table-related queries to the Researcher.
- **MCP Security Hardening (Guest Restrictions)**: 
    - `DataMCPServer`, `IdentityMCPServer`, `AgentCardMCPServer`, and `MemoryMCPServer` now check for the `GUEST_USER_ID` (UUID ending in `999`).
    - Unauthenticated guest access is blocked for all sensitive data operations (read/write/delete/impersonate), ensuring at least basic authentication is required to interact with the lab's vulnerable components.
- **Improved Vulnerability Documentation**: Tool descriptions in `AgentCardMCP` and `MemoryMCP` now explicitly mention intentional vulnerabilities (e.g., "No issuer validation", "Simplistic verification", "No content sanitization").

## Lab Data Verification Status

- **Relational Data (PostgreSQL)**: [VERIFIED] Healthy. ~23 identities, 226 app data records, 2k+ audit logs.
- **Vector Data (pgvector)**: [VERIFIED] Healthy. 92 memory documents with 1536D embeddings.
- **Graph Data (PuppyGraph)**: [VERIFIED] Port set to 8182 (Gremlin) for queries and 8081 for Web UI.

---

## 9. Final Project Cleanup & GitHub Preparation (February 2026)

### Repositoring Hardening
- **Security Tests**: Guest access reproduction script formalized as a permanent integration test: `tests/integration/test_guest_access.py`.
- **Exclusion Rules**: `.gitignore` updated with node_modules, IDE settings, and persistent database volumes to ensure a clean GitHub repository.
- **Environment Templates**: `.env.example` refined with descriptive comments and correct port configurations (Gremlin 8182/Web 8081).

### Documentation Consolidation
- **README/Quickstart**: Updated to guide researchers from zero-to-hero setup. Features list now includes "Identity-centric security hardening".
- **Tool Warning**: All core MCP tools now return explicit "Intentional Vulnerability" warnings in logs and descriptions.
- **Cleanup**: Redundant development files (`eg propts.txt`, `request.json`, etc.) removed.
