# CTO Brief — Part 1: Executive Summary and Current State

**Audience:** CTO / leadership  
**Purpose:** One-place overview of the Granzion Agentic AI Red-Teaming Lab: what it is, why it exists, what is built today, and how it fits the business (taxonomy-driven red teaming).  
**Companion docs:** Part 2 (diagrams explained), Part 3 (gaps and improvements).

---

## 1. What the Lab Is (One Paragraph)

The **Granzion Lab** is a **controlled, intentionally vulnerable sandbox** that models a multi-agent AI system (agents, MCP servers, agent-to-agent communication, identity) so red teamers can **exploit and validate** threats from our **Agentic Threats Taxonomy** (53+ threats across 9 categories). It is **not** a product or production system; it is a **test target** built to be broken in a repeatable, observable way. Identity is the **primary attack surface**: users, agents, delegation chains, and Agent Cards are first-class so we can demonstrate identity-centric attacks (impersonation, delegation abuse, A2A forgery) and map them to taxonomy categories.

---

## 2. Why We Built It

- **Taxonomy validation:** We need a concrete environment where every (or most) taxonomy threat can be **exploited** and **observed** (before/after state, evidence), not just theorized.
- **Red team readiness:** Security and product teams need a **single lab** to run attack scenarios, chat with agents, and inspect identity and data flows without touching production.
- **Identity-first positioning:** Many agentic threats stem from identity and trust (who is acting, who delegated, who is trusted). The lab makes identity the core so we can show and test those threats explicitly.
- **Unified stack:** One environment with **relational DB** (PostgreSQL), **vector** (pgvector for RAG), and **graph** (PuppyGraph) mirrors real agentic architectures and allows cross-modal attacks (e.g. SQL injection affecting what RAG or graph see).

---

## 3. Current State — What Exists Today

### 3.1 Delivered and Working

| Area | What exists | Status |
|------|-------------|--------|
| **Infrastructure** | Docker Compose: Postgres, Keycloak, PuppyGraph, Granzion Lab app. Optional LiteLLM in profile. | ✅ Runs; full_setup.py initializes DB and Keycloak. |
| **Identity** | Keycloak realm (granzion-lab), clients, roles, seeded users (Alice, Bob, Charlie), agent service accounts. IdentityContext (user_id, agent_id, delegation_chain, permissions). Bearer token, manual context, and Guest resolution in API. | ✅ Implemented; automation via full_setup/fix_keycloak. |
| **Agent Cards** | PostgreSQL storage; API endpoint `/.well-known/agent-card.json` for A2A discovery. Agent Card MCP (issue, verify, revoke) with intentional weak verification. | ✅ Implemented. |
| **Delegation** | Stored in DB and graph; no depth limit (intentional). Identity MCP: get_delegation_chain, validate_delegation, impersonate (weak), explore_graph (Gremlin). | ✅ Implemented. |
| **Agents** | Four Agno agents: Orchestrator, Researcher, Executor, Monitor. Each has tools (MCP wrappers), instructions, and identity context. Created per request when context is provided. | ✅ Implemented; Orchestrator behavior is unreliable (see Part 3). |
| **MCPs** | Identity, Agent Card, Comms, Memory, Data, Infra. All accept identity context; tools logged for audit. Intentional vulnerabilities documented (VULNERABILITIES.md). | ✅ Implemented and used by agents. |
| **A2A** | Comms MCP: send_message, receive_message, broadcast, clear_mailbox. Messages in PostgreSQL. “Active A2A”: in-process agent registry; send_message can trigger target agent’s arun() when registered. | ✅ Implemented; depends on Orchestrator actually calling send_message. |
| **Data** | PostgreSQL (identities, delegations, messages, audit_logs, app_data, agent_cards). pgvector for RAG. PuppyGraph for graph (delegation/trust). | ✅ Schema and init scripts; enrichment script available. |
| **LLM** | LiteLLM as unified proxy; agents use it for all model calls. Configurable (local or external). | ✅ Wired; requires LITELLM_URL/API_KEY. |
| **Scenarios** | 15 attack scenarios (s01–s15). ScenarioEngine: setup → state_before → attack steps → state_after → success criteria → ScenarioResult (evidence, state diff). Discovery from scenarios/ folder. | ✅ Implemented; most steps call MCPs/DB directly (not via agent prompts). |
| **API** | FastAPI: /agents/{id}/run, /scenarios, /health, /a2a/agents/{id}/.well-known/agent-card.json, /logs, /events. | ✅ Implemented. |
| **Dashboard** | React frontend: scenario list, agent chat, logs, events. | ✅ Implemented; runs separately (npm run dev). |
| **Threat mapping** | Taxonomy module; threat_coverage.md; 43/54 threats (79%) testable with current scenarios. | ✅ Documented. |
| **Docs** | Architecture, workflow, component guides (agents, Keycloak, MCPs, data, scenarios, A2A), Mermaid diagrams, vulnerability catalog, Rogue inspiration analysis, critique. | ✅ In place. |

### 3.2 Partially Delivered or Not Delivered

| Area | Current state | Gap |
|------|----------------|-----|
| **Orchestrator** | Agent exists and has correct tools (send_message, receive_message, verify_card, etc.). | Does **not** reliably route to Researcher/Executor, call send_message with correct UUIDs, or perform A2A handshake in one flow. Main blocker for “multi-agent demo” and some red team flows. |
| **TUI** | Design and requirements describe a Rogue-inspired terminal UI (scenario catalog, execution log, observable state). | Only Dashboard + API exist. TUI is a task item, not implemented. |
| **Scenario–agent link** | Scenarios prove vulnerabilities (e.g. impersonate, memory poisoning) by calling MCPs/DB directly. | Few scenarios **drive an agent by prompt** and then assert on state; so we don’t always prove “an agent would do this when prompted.” |
| **Taxonomy coverage** | 79% of threats testable. | Rogue Agent Insertion (#25), Replay (#37), Coordinated multi-agent (#31), and a few others are gaps; some threats are out of scope (e.g. training data poisoning, supply chain). |
| **Evidence/observability** | Audit logs and state_before/state_after exist. | No single evidence schema; not every MCP path may log identity_context consistently; graph/RAG state in state capture may be inconsistent. |
| **Keycloak** | Realm and users are automated. | Health check doesn’t verify “user can obtain token”; docs could be clearer on expected state and identity testing. |
| **Tests** | Unit tests for MCPs; property tests for many invariants. | No E2E test that “orchestrator sends to researcher and gets reply”; no automated scenario-success tests for a fixed set of scenarios. |

### 3.3 Implementation vs Task List

The specs/tasks.md file still shows some items unchecked (e.g. “Implement Agno agents,” “Implement scenario framework,” “Implement core attack scenarios”). **In code, agents and scenarios are implemented.** The task list is likely outdated; the **actual gap** is quality and reliability (orchestrator, scenario–agent linkage, coverage, TUI), not absence of those components.

---

## 4. How It Fits the Taxonomy (High Level)

- **9 categories** are represented in the architecture (Instruction, Tool, Memory, Identity & Trust, Orchestration, Communication, Autonomy, Infrastructure, Visibility).
- **15 scenarios** map to specific threat IDs; threat_coverage.md and the taxonomy module link threats to components and scenarios.
- **Identity & Trust** and **Infrastructure** have the strongest scenario coverage; **Communication** and **Autonomy** have fewer dedicated scenarios.
- **~21% of threats** are not testable today (out of scope or not yet implemented); the rest are testable via scenarios and/or agent/MCP interaction.
- **Vulnerabilities** are documented with threat IDs (e.g. IT-02, C-03) so red teamers know what they are testing.

---

## 5. How to Read the Rest of the CTO Pack

- **Part 2 (CTO-02)** explains every architecture and workflow diagram in plain language, maps each to the current implementation (code/components), and calls out what is “as designed” vs “needs improvement.”
- **Part 3 (CTO-03)** lists every gap and improvement in priority order (P0–P3), with concrete actions, rationale, and a short roadmap so the CTO can decide what to fund and in what order.

Together, Parts 1–3 give a complete picture: what we have, how the diagrams reflect it, and what must be improved for the lab to be CTO-ready for red team exercises.
