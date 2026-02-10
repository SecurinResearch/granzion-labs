# Granzion Lab — Project Architecture

This document describes the **target architecture** of the Granzion Agentic AI Red-Teaming Lab: how components fit together and how they support threat-driven red teaming against the Agentic Threats Taxonomy.

---

## 1. Purpose

The lab is a **controlled, intentionally vulnerable sandbox** that:

- Models a multi-agent system with **agents**, **MCP servers**, **A2A** (agent-to-agent) communication, and **identity** (Keycloak + Agent Cards).
- Uses **relational** (PostgreSQL), **vector** (pgvector), and **graph** (PuppyGraph) data to mirror real agentic stacks.
- Exposes **intentional vulnerabilities** so red teamers can validate detection and exploitation of threats from the **Granzion Agentic Threats Taxonomy** (53+ threats across 9 categories).

It is **not** a production system; it is built to be broken in a repeatable, observable way.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        RED TEAM / OPERATOR INTERFACE                              │
│  Dashboard (React) │ Scenario Hub │ API (FastAPI) │ Optional TUI                 │
└─────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        IDENTITY LAYER                                            │
│  Keycloak (users, agents, services) │ Agent Cards (A2A) │ Delegation chains     │
└─────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        AGENT LAYER (Agno)                                         │
│  Orchestrator │ Researcher │ Executor │ Monitor                                   │
│  (coordination, A2A) │ (RAG, memory) │ (actions, tools) │ (observability gaps)    │
└─────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        MCP LAYER                                                  │
│  Identity MCP │ Agent Card MCP │ Comms MCP │ Memory MCP │ Data MCP │ Infra MCP   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                                                 │
│  PostgreSQL (relational) │ pgvector (embeddings, RAG) │ PuppyGraph (graph)       │
└─────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        LLM LAYER                                                  │
│  LiteLLM (unified model proxy, routing, optional local/cloud)                     │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Layers in Detail

### 3.1 Red Team Interface

- **Dashboard (React)**: Scenario selection, agent chat, logs, events.
- **Scenario Hub**: List and run attack scenarios (s01–s15), view before/after state and evidence.
- **API (FastAPI)**: REST endpoints for agents (`/agents/{id}/run`), scenarios, health, A2A discovery (`/.well-known/agent-card.json`), logs, events.
- **Optional TUI**: Rogue-inspired terminal UI (planned; not fully implemented).

All interaction can carry **identity context** (Bearer token or manual/guest context) for identity-first testing.

### 3.2 Identity Layer

- **Keycloak**: OIDC IdP for users, agent service accounts, and clients. Realms, clients, roles, and seeded users (e.g. Alice, Bob, Charlie, Guest) are automated.
- **Agent Cards**: Stored in PostgreSQL; exposed at `/a2a/agents/{id}/.well-known/agent-card.json` for A2A discovery. Intentionally weak verification (no strong signature/revocation checks) to test identity threats.
- **Delegation**: User → Orchestrator → Researcher/Executor/Monitor. Stored in DB and graph; no depth limit (intentional).

**Identity context** flows with every request: `user_id`, `agent_id`, `delegation_chain`, `permissions`, `trust_level`.

### 3.3 Agent Layer (Agno)

| Agent        | Role                | Main tools / behavior                    | Intentional weaknesses              |
|-------------|---------------------|------------------------------------------|-------------------------------------|
| **Orchestrator** | Coordination, A2A   | Comms (send/receive/broadcast), Identity, Agent Card | No delegation depth limit; trusts messages; no rate limiting |
| **Researcher**   | RAG, memory, read   | Memory MCP, Data MCP (read), Comms       | No embedding validation; trusts RAG |
| **Executor**     | Actions, writes     | Data MCP, Infra MCP, Comms              | No param sanitization; command injection surface |
| **Monitor**      | Observability       | Data (audit read), Comms (broadcasts)    | Gaps in logging; blind to direct A2A |

Agents are created per request with identity context when possible; they call MCPs via wrapped tools. Orchestrator is intended to route work to Researcher/Executor and to use A2A (send_message, verify_card, etc.); current implementation has known gaps (see critique doc).

### 3.4 MCP Layer

- **Identity MCP**: Identity context, delegation chain, discover agents, impersonate (intentionally weak), explore_graph (Gremlin).
- **Agent Card MCP**: Issue/verify/revoke cards; verification and revocation checks are intentionally weak.
- **Comms MCP**: send_message, receive_message, broadcast, clear_mailbox; messages stored in DB; no encryption (intentional).
- **Memory MCP**: embed_document, search_similar, get_context (pgvector); no sanitization (poisoning surface).
- **Data MCP**: CRUD on app_data; read_data with optional SQL; intentional injection surface.
- **Infra MCP**: deploy_service, execute_command, modify_config, read_env; command execution surface.

All MCPs accept **identity context** and can log it for observability and red team evidence.

### 3.5 Data Layer

- **PostgreSQL**: Identities, delegations, agent_cards, messages, audit_logs, app_data, embeddings metadata. Single DB for app + Keycloak (separate DB possible).
- **pgvector**: Embeddings for RAG/memory; used by Memory MCP and Researcher.
- **PuppyGraph**: Graph over PostgreSQL (or linked storage); delegation/trust graph; `explore_graph` runs Gremlin (intentional reconnaissance surface).

Unified schema supports cross-modal tests (e.g. SQL injection affecting what graph or RAG see).

### 3.6 LLM Layer

- **LiteLLM**: Single proxy for all model calls (OpenAI, Anthropic, etc.). Configurable via `config/litellm_config.yaml`. Can run in Docker (profile) or point to external proxy. Provides a single place for model-related attacks (e.g. jailbreaking in s07).

---

## 4. Design Principles

1. **Identity-first**: Identity (users, agents, delegation, tokens, Agent Cards) is the primary attack surface; most threats are testable via identity confusion or abuse.
2. **Threat-driven**: Components and scenarios map to taxonomy categories (Instruction, Tool, Memory, Identity & Trust, Orchestration, Communication, Autonomy, Infrastructure, Visibility).
3. **Observable outcomes**: Scenarios capture state before/after and success criteria so red teamers see concrete evidence (e.g. delegation chain, audit log, RAG content).
4. **Simplified but complete**: Four agents, five MCPs, one relational + vector + graph data story to keep the lab understandable while covering the taxonomy.
5. **Local-first**: Docker Compose runs Postgres, Keycloak, PuppyGraph, app; LiteLLM optional; no required cloud.

---

## 5. Deployment Topology

- **postgres**: 5432
- **keycloak**: 8080
- **puppygraph**: 8182 (Gremlin), 8081 (UI)
- **granzion-lab**: 8000 (TUI/Web), 8001 (API)
- **litellm** (optional): 4000

Initialization: `db/init` SQL, then `scripts/full_setup.py` (DB schema, Keycloak realm/clients/roles/users, Agent Cards). Optional: `scripts/enrich_lab_data.py` for richer test data.

---

## 6. Extension Points

- **New agents**: Add in `src/agents/`, register in `main.py` and agent factory.
- **New MCPs**: Implement in `src/mcps/`, expose tools to the right agents.
- **New scenarios**: Add `sXX_*.py` in `scenarios/` with setup, steps, criteria, state capture.
- **New threats**: Extend `src/taxonomy/`, map to components and scenarios, document in VULNERABILITIES.md.

---

## 7. Related Docs

- [Workflow](WORKFLOW.md) — end-to-end flow for operators and scenarios
- [01-agents.md](01-agents.md) — agents in detail
- [02-keycloak.md](02-keycloak.md) — Keycloak and identity automation
- [03-mcps.md](03-mcps.md) — MCP servers and tools
- [04-data-layer.md](04-data-layer.md) — PostgreSQL, pgvector, PuppyGraph
- [05-scenarios.md](05-scenarios.md) — scenario framework and catalog
- [06-a2a-and-identity.md](06-a2a-and-identity.md) — A2A and identity context
