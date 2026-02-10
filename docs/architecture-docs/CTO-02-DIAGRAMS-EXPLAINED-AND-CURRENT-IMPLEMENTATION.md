# CTO Brief — Part 2: Diagrams Explained and Current Implementation

**Audience:** CTO / leadership  
**Purpose:** Crystal-clear explanation of every architecture and workflow diagram: what each element means, how it maps to the current codebase, and where reality matches or diverges from the diagram.  
**Companion docs:** Part 1 (executive summary), Part 3 (gaps and improvements).  
**Diagram sources:** ARCHITECTURE_DIAGRAM.md, WORKFLOW_DIAGRAM.md.

---

## How to Use This Document

- Each **section** corresponds to one diagram (or a logical group).
- For each we give: **what the diagram shows**, **what each part means in plain language**, **where it lives in the codebase**, and **current vs ideal** (what works, what doesn’t, what’s missing).
- Identity is called out wherever it appears, since it is the main theme of the lab.

---

# Part A: Architecture Diagrams

---

## A1. Full Architecture (Identity-First) Diagram

**What it shows:** Top-to-bottom flow: Red Team Interface → Identity Layer → Agents → MCPs → Data → LLM. Identity is the central layer between “who is calling” and “what runs.”

### Element-by-element explanation

| Diagram element | Meaning | Current implementation | Notes |
|-----------------|--------|------------------------|-------|
| **Red Team / Operator Interface** | How operators interact with the lab. | **Dashboard (React):** `frontend/`, scenario list, agent chat, logs, events. **Scenario Hub:** Part of Dashboard + API `GET/POST /scenarios`. **API (FastAPI):** `src/main.py`, `/agents/{id}/run`, health, A2A discovery, logs, events. **TUI (optional):** Not implemented; design only. | TUI is the only missing piece in this box. |
| **Arrow: Bearer token / manual context / Guest** | Every request carries an identity input. | In `main.py` run_agent: (1) If `Authorization: Bearer <token>`, parse via Keycloak → IdentityContext. (2) Else if body has `identity_context`, use it (and ensure identity in DB). (3) Else Guest (fixed UUID, minimal permissions). | Implemented as drawn. |
| **Identity Layer** | Where identity is defined and resolved. | **Keycloak:** Docker service; realm `granzion-lab`, clients, users (Alice, Bob, Charlie), service accounts; `src/identity/keycloak_client.py`, `keycloak_init.py`; automation in `full_setup.py` / `fix_keycloak.py`. **Agent Cards:** Table `agent_cards`; API `GET /a2a/agents/{id}/.well-known/agent-card.json`; Agent Card MCP. **Delegation:** Tables `identities`, `delegations`; Identity MCP (get_delegation_chain, etc.); PuppyGraph for graph view. **IdentityContext:** `src/identity/context.py` (user_id, agent_id, delegation_chain, permissions, trust_level, keycloak_token). | All present; Keycloak health/token verification could be stronger (see Part 3). |
| **Arrow: IdentityContext on every request** | Resolved identity is passed into the agent layer. | When creating an agent for `/agents/{id}/run`, we call e.g. `create_orchestrator_agent(identity_context=identity_context)` and set `identity_context_var` before `agent.arun(prompt)`. | Implemented. |
| **Agent Layer** | Four Agno agents. | **Orchestrator, Researcher, Executor, Monitor:** `src/agents/orchestrator.py`, `researcher.py`, `executor.py`, `monitor.py`. Each is an Agno `Agent` with model (LiteLLM), tools (MCP wrappers), instructions. The lines between Orchestrator and Res/Exec/Mon in the diagram mean “orchestrator coordinates them”; in code this happens only when Orchestrator calls Comms MCP send_message to their UUIDs — and that flow is unreliable today. | Agents exist; Orchestrator → sub-agent coordination is the main gap. |
| **Arrow: tools + identity_context** | Agents call MCPs with identity attached. | `src/agents/utils.py`: `create_mcp_tool_wrapper(..., identity_context)`; every tool invocation passes identity into the MCP handler. MCPs can log and use it. | Implemented. |
| **MCP Layer** | Six MCP servers. | Identity MCP, Agent Card MCP, Comms MCP, Memory MCP, Data MCP, Infra MCP in `src/mcps/`. Each registers tools; agents get wrappers for a subset per agent. | Implemented. |
| **Data Layer** | Persistence. | PostgreSQL (schema in `db/init/`, models in `src/database/`). pgvector for embeddings (Memory MCP, Researcher). PuppyGraph (config in `config/puppygraph/`; Identity MCP `explore_graph`). | Implemented. |
| **LLM Layer** | Model access. | LiteLLM; agents use `get_llm_model()` from `src/agents/model_factory.py` (points to settings.LITELLM_URL). | Implemented. |

**Summary:** The diagram matches the implemented architecture. The only architectural element not implemented is the TUI. The main behavioral gap is Orchestrator not reliably using the “tools + identity_context” path to drive Researcher/Executor via A2A.

---

## A2. Layered View (Identity in the Middle)

**What it shows:** Same stack as A1 but as six numbered layers (1=Interface, 2=Identity, 3=Agents, 4=MCPs, 5=Data, 6=LLM). Identity is explicitly Layer 2; everything above uses it, everything below is used by agents via MCPs.

### What each layer means

- **L1 (Interface):** Entry points. Implemented as Dashboard + API; TUI not implemented.
- **L2 (Identity):** Keycloak (users, agents, services), Agent Cards (A2A discovery), Delegation (user → agent → agent), IdentityContext (user_id, agent_id, chain, permissions). All implemented; identity flows into L3 as described.
- **L3 (Agents):** Four agents; implemented. Orchestrator’s *behavior* (routing to L3 peers) is weak.
- **L4 (MCPs):** Six MCPs; implemented.
- **L5 (Data):** PostgreSQL, pgvector, PuppyGraph; implemented.
- **L6 (LLM):** LiteLLM; implemented.

**Current vs ideal:** Layers and data flow match code. Ideal would add: TUI in L1, reliable Orchestrator coordination in L3, and consistent evidence/audit schema across L4→L5.

---

## A3. Identity and Delegation Detail

**What it shows:** Where identity *comes from* (sources), what the *resolved object* contains (IdentityContext), and *where it is used* (consumers).

### Element-by-element

| Element | Meaning | Current implementation |
|---------|--------|------------------------|
| **Sources: JWT, Manual, Guest** | Three ways to supply identity. | JWT: Keycloak decode/introspect in main.py. Manual: `identity_context` in request body; `IdentityContext.from_dict`. Guest: fixed UUID and minimal permissions when neither above. |
| **Resolved: IdentityContext** | user_id, agent_id, delegation_chain, permissions, trust_level. | `src/identity/context.py`; built from token or dict or Guest. |
| **Consumers: API/run_agent, MCPs, Audit, A2A messages** | Identity is used for agent creation, tool calls, logging, and message payloads. | API uses it to create agent and set context var. MCPs receive it in tool wrappers. Audit: MCPs and some paths log to audit_logs; completeness varies. Messages: Comms MCP stores messages; payload can include delegation info; receiver can be triggered with delegated context. |

**Gap:** Not every MCP code path may log identity_context to audit in a consistent way; evidence schema is not standardized (see Part 3).

---

## A4. Component ↔ Identity Relationship

**What it shows:** Keycloak and PostgreSQL as the two “sources of truth” for identity data, and how agents and messages/audit tie to them.

### Flow in the diagram

- Keycloak: realm, users (Alice, Bob, Charlie), service accounts (sa-orchestrator, etc.), roles. These are used to *authenticate* and to build IdentityContext; they are not the only store — the lab also keeps **identities** in its own DB for consistency with delegations and agent cards.
- PostgreSQL (lab): identities, delegations, agent_cards, messages, audit_logs. Agents and MCPs read/write here. Delegations “feed” agents in the sense that when an agent runs, its identity_context may include a delegation_chain that was derived from these tables.
- Agents: Orchestrator, Researcher, Executor, Monitor produce messages (via Comms MCP) and audit entries (via MCP tool use). All of that is implemented.

**Current vs ideal:** The relationship is implemented. Ideal: explicit health check that Keycloak has expected realm/users and that at least one user can obtain a token; and that audit_logs consistently store identity fields (see Part 3).

---

## A5. Data Flow with Identity (Sequence)

**What it shows:** Step-by-step for a single “chat with agent” request: User → API → Keycloak → Identity → Agent → MCP → DB, with identity at each step.

### Step-by-step meaning and implementation

1. **User → API: POST /agents/orchestrator/run + Bearer token** — Implemented; Dashboard or any client can send this.
2. **API → Keycloak: introspect / decode JWT** — Implemented (keycloak_client / token parsing).
3. **Keycloak → API: user_id, roles** — Used to build IdentityContext.
4. **API → Identity: Build IdentityContext** — Implemented in main.py.
5. **API → Agent: create_orchestrator_agent(identity_context)** — Implemented; we create a fresh agent with that context.
6. **API → Agent: agent.arun(prompt)** — Implemented; identity_context_var is set around this call.
7. **Agent → MCP: tool call (identity_context in wrapper)** — Implemented via utils.create_mcp_tool_wrapper.
8. **MCP → DB: read/write (with user_id, agent_id in logs)** — Implemented where MCPs log; completeness of identity in every log line may vary.
9. **MCP → Agent: tool result** — Implemented.
10. **Agent → API: response** — Implemented.
11. **API → User: response + identity** — Implemented; response can include identity for inspection.

**Summary:** The sequence matches the implemented flow. The only caveat is audit completeness (identity in every relevant log entry).

---

# Part B: Workflow Diagrams

---

## B1. Lab Setup Workflow

**What it shows:** From “start” to “ready for red team”: clone, compose, full_setup (schema, Keycloak, users, agents, cards), optional enrich, then access.

### Step-by-step

| Step | Meaning | Current implementation |
|------|--------|------------------------|
| Clone, .env | Get repo and configure (e.g. LITELLM_URL, LITELLM_API_KEY). | Manual; .env.example provided. |
| docker compose up -d | Start Postgres, Keycloak, PuppyGraph, granzion-lab app. | docker-compose.yml; no LiteLLM in default profile (optional profile). |
| Wait | Services healthy. | Compose depends_on; app may retry Keycloak. |
| full_setup.py | One script to init DB and Keycloak and seed. | `scripts/full_setup.py` runs schema init, Keycloak realm/clients/roles/users, agent identities, seed_agent_cards. |
| Schema, Keycloak, Users, Agents, Cards | Sub-steps of full_setup. | As in full_setup; fix_keycloak or manual_keycloak_setup can be used if Keycloak is not ready on first run. |
| Enrich? | Optional extra data for scenarios. | `scripts/enrich_lab_data.py`; optional. |
| Access | Dashboard, API, Keycloak UI. | Dashboard: frontend (npm run dev). API: port 8001. Keycloak: 8080. |

**Current vs ideal:** Flow is implemented and documented. Ideal: single “golden path” doc (e.g. QUICKSTART) that states exact order and a health check that verifies “user can get token” after setup.

---

## B2. Identity Resolution (Every Request)

**What it shows:** Decision tree for every incoming request: Bearer? → parse Keycloak → IdentityContext. Else manual context in body? → from_dict, ensure in DB → IdentityContext. Else → Guest → IdentityContext. Then set context var, use in agent+MCPs, clear, return response with identity.

### Implementation

- Implemented in `main.py` in the `run_agent` endpoint (and any other endpoint that needs identity). Order: Bearer → manual → Guest. IdentityContext is built; identity_context_var is set before agent run and cleared after. Response can include identity for inspection.
- **Current vs ideal:** Matches diagram. Ideal: document this in a short “Identity testing” section (Bearer vs manual vs Guest) for red teamers.

---

## B3. Scenario Execution Workflow

**What it shows:** Red teamer selects scenario → engine loads by ID → setup → state_before → for each step execute (steps call MCPs/DB) → state_after → verify criteria → success/fail → report (before/after, evidence).

### Implementation

- **Select, Load:** Dashboard or API calls scenario run; `ScenarioEngine.execute_scenario(scenario_id)` in `src/scenarios/engine.py`; discovery in `src/scenarios/discovery.py` (loads from scenarios/ folder).
- **Setup:** Each scenario defines `setup()` (e.g. create test users, delegations, records); executed once at start.
- **state_before / state_after:** Scenario defines callables; engine calls them and stores in ScenarioResult (initial_state, final_state, state_diff).
- **Steps:** Each AttackStep has an `action()`; typically calls MCPs or DB directly (not via an agent prompt). Steps are executed in order.
- **Criteria:** Each Criterion has check() and evidence(); all must pass for scenario success.
- **Report:** ScenarioResult returned to API/Dashboard; includes step results, criterion results, evidence, errors.

**Current vs ideal:** Flow is implemented. Ideal: more scenarios that drive an *agent* by prompt and then assert on state (see Part 3); and standardized evidence schema so “evidence” is always structured (actor, action, resource, timestamp, identity).

---

## B4. Scenario Execution with Identity (Sequence)

**What it shows:** Same as B3 but as a sequence: Red teamer → API → Engine → Setup (DB) → Steps (MCP, DB) → state_after → criteria → ScenarioResult → API → Red teamer.

- Setup creates identities/delegations in DB (e.g. Alice, Bob, Orchestrator, Executor). Steps may call e.g. identity_mcp.impersonate with a test context; MCP writes to audit_log/messages; steps may read/write DB for evidence. All of this is implemented.
- **Identity in scenarios:** Scenario steps use test identity data (e.g. create_delegation with specific from/to); they don’t always go through the “API with Bearer token” path — they invoke MCPs/DB directly with the scenario’s own context. So identity is present in the data and in MCP calls, but the diagram’s “identity” is implicit in the step logic rather than a separate participant.

---

## B5. Agent Chat Workflow (With Identity)

**What it shows:** User sends prompt → POST run → resolve identity → IdentityContext available → create fresh agent with context → register in Comms A2A bridge → set context var → agent.arun(prompt) → agent uses LiteLLM and MCP tools (with identity) → DB → tool result → response → clear context → return to user.

### Implementation

- All steps implemented in main.py: resolve identity (B2), create agent with identity_context, register in CommsMCPServer._active_agents for that request’s agent instance, set identity_context_var, arun(prompt), tools get identity via wrapper, clear context, return response and identity.
- **Current vs ideal:** Implemented. Ideal: Orchestrator actually using its tools (send_message, receive_message) so that “agent uses MCP tools” includes real A2A in the same request or next.

---

## B6. End-to-End Identity Flow

**What it shows:** Inputs (Bearer, manual, Guest) → IdentityContext → propagation (context var, MCP wrappers, agent) → persistence (audit_logs, messages, delegations).

- Implemented: identity flows from the three sources into IdentityContext; then into context var and agent creation and MCP wrappers; MCPs and agents write to audit_logs, messages, and (indirectly) delegations. **Gap:** audit and evidence schema not fully standardized (Part 3).

---

## B7. A2A Message Flow (Orchestrator → Researcher)

**What it shows:** User asks Orchestrator to “ask researcher to find X.” Orchestrator gets prompt and IdentityContext; calls Comms send_message(to=Researcher, message=...); Comms writes to DB; if Researcher is in _active_agents, Comms calls Researcher.arun(A2A notification) with delegated context; Researcher uses Memory/Data MCP and may send_message back to Orchestrator; Orchestrator may call receive_message; then responds to user.

### Current vs diagram

- **Implemented:** Comms MCP stores messages; has _active_agents registry; when target is registered, Comms can call target_agent.arun(a2a_prompt) with delegated context in a background task. Researcher (and others) can call send_message back.
- **Gap:** The diagram assumes **Orchestrator reliably calls send_message** with the correct Researcher UUID and a clear message. In practice the Orchestrator (LLM) often does not do this in one turn, or does it with wrong format/ID. So the “Orch → Comms → Res” path exists in code but is not reliably triggered by a natural-language user prompt. **This is the main behavioral gap** for A2A: the plumbing is there; the orchestrator’s use of it is not reliable.

---

## B8. High-Level Workflow Summary

**What it shows:** Operator actions (setup lab, run scenario, chat with agent) all tie into Identity (Keycloak/Guest/Manual → IdentityContext → audit + messages), and the system does two main things: scenarios (setup → steps → criteria → evidence) and agents (prompt → tools → MCP → DB), both producing state (before/after, logs).

- This is an accurate high-level summary of the lab. Identity is in every path; scenarios and agent chat are the two main use flows; observability is state and logs. Implemented as summarized; improvements needed are reliability (orchestrator), coverage (scenarios + taxonomy), evidence schema, and TUI (see Part 3).

---

# Summary Table: Diagram vs Reality

| Diagram | Matches implementation? | Main gap(s) |
|---------|-------------------------|-------------|
| A1 Full architecture | Yes | TUI missing; Orchestrator behavior weak. |
| A2 Layered view | Yes | Same as A1. |
| A3 Identity detail | Yes | Audit/evidence consistency. |
| A4 Component–identity | Yes | Keycloak health/token check. |
| A5 Data flow sequence | Yes | Audit completeness. |
| B1 Lab setup | Yes | Golden-path doc + health check. |
| B2 Identity resolution | Yes | Document for red teamers. |
| B3 Scenario execution | Yes | Agent-driven scenarios; evidence schema. |
| B4 Scenario + identity | Yes | Same as B3. |
| B5 Agent chat | Yes | Orchestrator actually using A2A. |
| B6 Identity flow | Yes | Evidence/audit schema. |
| B7 A2A flow | **Partial** | Orchestrator must reliably call send_message. |
| B8 Summary | Yes | Same as above. |

Part 3 (CTO-03) turns these gaps into a prioritized list of improvements and a short roadmap for the CTO.
