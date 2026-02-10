# Component: Agents

This document describes the **agent layer** in Granzion Lab: what each agent is, how it works, and how it ties into red teaming.

---

## 1. Overview

The lab uses **four Agno-based agents**:

| Agent | UUID (suffix) | Role | Main MCPs |
|-------|----------------|------|-----------|
| **Orchestrator** | …0101 | Coordinates workflows, A2A | Comms, Identity, Agent Card |
| **Researcher** | …0102 | RAG, memory, read-only data | Memory, Data, Comms |
| **Executor** | …0103 | Writes, infra, commands | Data, Infra, Comms |
| **Monitor** | …0104 | Observability (with gaps) | Data (audit), Comms (broadcasts) |

All agents:

- Use **LiteLLM** for LLM calls (via `model_factory` / `get_llm_model()`).
- Receive **identity context** when created (user_id, agent_id, delegation_chain, permissions).
- Call **MCP tools** through wrappers that inject identity context so every tool run is attributed.

---

## 2. How Agents Are Built

- **Factory per agent**: `create_orchestrator_agent()`, `create_researcher_agent()`, etc. in `src/agents/`.
- Each factory:
  - Optionally extends the provided **IdentityContext** with the agent’s UUID (for delegation chain).
  - Loads **goal** from goal manager (e.g. Orchestrator’s default goal).
  - Instantiates the needed **MCP servers** (Comms, Identity, Agent Card, Memory, Data, Infra).
  - Defines a **tool list** (which server + which tool name).
  - Uses **create_agent_tools()** (in `utils.py`) to wrap MCP tools for Agno.
  - Builds **instructions** (system prompt) including role, capabilities, and **intentional vulnerabilities**.
  - Returns an **Agno `Agent`** with `name`, `model`, `tools`, `instructions`.

- **Tool wrapper** (`create_mcp_tool_wrapper`): Takes an MCP server, tool name, and identity context; returns an async function Agno can call. The wrapper forwards arguments (including flattening Agno’s args/kwargs) and passes identity context into the MCP handler.

---

## 3. Orchestrator Agent

- **Purpose**: Coordinate multi-agent workflows and A2A communication.
- **Tools**: send_message, receive_message, broadcast, clear_mailbox (Comms); get_identity_context, get_identity_type, discover_agents, validate_delegation, get_delegation_chain, explore_graph (Identity); verify_card, issue_card (Agent Card).
- **Instructions**: Tell it to use Researcher for retrieval, Executor for actions, Monitor for alerts; use UUIDs; check mailbox when needed; verify cards before A2A (but verification is intentionally weak).
- **Intentional vulnerabilities**: No delegation depth limit; trusts A2A messages; no sender verification; broadcasts in plaintext; no rate limiting.
- **Known issues**: In practice, the orchestrator often does not reliably route to sub-agents or perform full A2A handshakes in a single chat turn; improvements are needed (see critique doc).

---

## 4. Researcher Agent

- **Purpose**: RAG-style retrieval and read-only data access.
- **Tools**: embed_document, search_similar, get_context (Memory); read_data (Data); send_message, receive_message (Comms).
- **Intentional vulnerabilities**: No embedding validation; trusts RAG results; no source verification; context window stuffing possible.
- **Threat coverage**: Memory poisoning, RAG injection, instruction injection via retrieved content.

---

## 5. Executor Agent

- **Purpose**: Perform writes, infra changes, and command execution.
- **Tools**: create_data, read_data, update_data, delete_data (Data); deploy_service, execute_command, modify_config, read_env (Infra); send_message, receive_message (Comms).
- **Intentional vulnerabilities**: No parameter sanitization (SQL/command injection); inherits caller permissions; no confirmation for destructive actions; no rollback.
- **Threat coverage**: Tool parameter injection, unauthorized tool use, infra manipulation.

---

## 6. Monitor Agent

- **Purpose**: Demonstrate visibility gaps (incomplete logging, blind spots).
- **Tools**: read_data (audit logs only); receive_message (broadcasts only).
- **Intentional vulnerabilities**: Doesn’t see direct A2A messages; polling delay; log manipulation possible; simple rule-based detection.
- **Threat coverage**: Observability gaps, log manipulation, detection evasion.

---

## 7. Lifecycle and Registration

- **Startup**: `initialize_agents()` in `main.py` creates one instance per agent (with no or default identity) and stores them in `_agents`. Each agent is registered in `CommsMCPServer.register_agent_instance(agent_id, agent)` so A2A can deliver messages to in-process agent instances.
- **Per request**: For `POST /agents/{id}/run`, the app typically creates a **new** agent instance with the request’s identity context and runs `arun(prompt)` once. This keeps identity and state isolated per call.

---

## 8. References

- Implementation: `src/agents/` (orchestrator.py, researcher.py, executor.py, monitor.py, model_factory.py, utils.py, goals.py).
- Design: `docs/agents.md`, `docs/specs/design.md`.
- Vulnerabilities: `docs/VULNERABILITIES.md`.
