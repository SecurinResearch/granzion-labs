# Component: MCP Servers

This document describes the **MCP (Model Context Protocol) layer** in Granzion Lab: what each server does, which tools it exposes, and how they support red teaming.

---

## 1. Overview

Agents do **not** implement capabilities directly; they call **MCP servers** via tools. Each MCP is a Python class (in `src/mcps/`) that registers a set of **tools** (name + handler + input schema). The agent layer wraps these tools for Agno and passes **identity context** into every call.

| MCP | Purpose | Main tools |
|-----|--------|------------|
| **Identity MCP** | Identity, delegation, graph recon | get_identity_context, get_identity_type, discover_agents, validate_delegation, get_delegation_chain, impersonate, explore_graph |
| **Agent Card MCP** | A2A identity documents | verify_card, issue_card, revoke_card |
| **Comms MCP** | A2A messaging | send_message, receive_message, broadcast, clear_mailbox |
| **Memory MCP** | Vector store, RAG | embed_document, search_similar, get_context |
| **Data MCP** | Relational CRUD / SQL | read_data, create_data, update_data, delete_data |
| **Infra MCP** | Deploy, config, shell | deploy_service, execute_command, modify_config, read_env |

---

## 2. Identity MCP

- **Role**: Expose identity context, delegation chain, agent discovery, and graph exploration.
- **Tools**:
  - `get_identity_context`: Return current identity context (user, agent, chain, permissions).
  - `get_identity_type`: Return identity type and “acting for” user.
  - `discover_agents`: List agents (from DB or registry).
  - `validate_delegation`: Check if a delegation is valid (logic can be intentionally weak).
  - `get_delegation_chain`: Return chain from user to current agent.
  - `impersonate`: **Intentional vulnerability** — obtain a token or context as another user with only a “reason” string (no real approval).
  - `explore_graph`: Run **Gremlin** against PuppyGraph (no sanitization — reconnaissance surface).
- **Red team**: Impersonation (IT-02, IT-03), delegation abuse (IT-04), graph recon (visibility/threat intel).

---

## 3. Agent Card MCP

- **Role**: Issue and verify Agent Cards for A2A discovery and handshakes.
- **Tools**:
  - `verify_card`: Load card for an agent (from DB or `/.well-known/agent-card.json`). **Intentionally**: no strong signature verification, no revocation check.
  - `issue_card`: Create or update an Agent Card for an agent (weak or no authorization).
  - `revoke_card`: Mark card revoked (verification may still not check it).
- **Red team**: Forged cards (IT-07), revocation bypass (IT-08), capability escalation via cards.

---

## 4. Comms MCP

- **Role**: Agent-to-agent messages (inbox/outbox style) and broadcast.
- **Storage**: Messages stored in PostgreSQL (e.g. `messages` table) with from_agent_id, to_agent_id, payload, etc.
- **Tools**:
  - `send_message`: Enqueue message to another agent (by ID). Payload can include delegation_chain.
  - `receive_message`: Read messages for current agent (mailbox).
  - `broadcast`: Send a message to all agents (no encryption — intentional).
  - `clear_mailbox`: Delete messages for an agent (no auth check — intentional).
- **Active A2A**: If the target agent is registered in-process, Comms MCP can trigger the agent’s `arun()` with the message content (simulated A2A).
- **Red team**: Message forgery (C-03), interception, replay, covert channels.

---

## 5. Memory MCP

- **Role**: Vector storage for RAG and agent memory (pgvector).
- **Tools**:
  - `embed_document`: Store text with embedding (no sanitization — poisoning surface).
  - `search_similar`: Similarity search; return top-k chunks.
  - `get_context`: Retrieve context for an agent/session (can be stuffed or poisoned).
- **Red team**: Memory poisoning (M-01), RAG injection, context stuffing (M-03), exfiltration via retrieval.

---

## 6. Data MCP

- **Role**: CRUD on application data (e.g. `app_data` table) and optional raw SQL.
- **Tools**:
  - `read_data`: Read by table/filters or via SQL (parameterized where implemented; intentional injection points may exist).
  - `create_data`, `update_data`, `delete_data`: Write operations; permission checks can be weak or bypassable.
- **Red team**: SQL injection, unauthorized data access, data tampering.

---

## 7. Infra MCP

- **Role**: Simulate deployment, config, and command execution (lab-safe but dangerous by design).
- **Tools**:
  - `deploy_service`: Record or trigger a “deployment” (e.g. in DB or script).
  - `execute_command`: Run shell commands (sandboxed in practice but presented as high-risk).
  - `modify_config`: Change config entries (e.g. in DB or file).
  - `read_env`: Read environment variables (info disclosure).
- **Red team**: Command injection, over-privileged tools, infra manipulation (I-01, I-02).

---

## 8. Base and Wiring

- **Base**: `src/mcps/base.py` defines the pattern for registering tools (name, handler, input_schema). Handlers receive arguments plus optional `identity_context`.
- **Wiring**: Each agent’s factory builds a list of `(server, tool)` and uses `create_agent_tools()` in `src/agents/utils.py` to wrap MCP tools for Agno. Identity context is set per request and passed into the wrapper so every MCP call is attributed for audit and red team evidence.

---

## 9. References

- Implementation: `src/mcps/` (identity_mcp.py, agent_card_mcp.py, comms_mcp.py, memory_mcp.py, data_mcp.py, infra_mcp.py).
- Vulnerabilities: `docs/VULNERABILITIES.md`.
- Testing: `tests/unit/test_*_mcp.py`.
