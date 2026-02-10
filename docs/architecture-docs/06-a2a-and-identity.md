# Component: A2A and Identity

This document explains **Agent-to-Agent (A2A) communication** and **identity context** in Granzion Lab: how they work and how they support red teaming.

---

## 1. Identity Context

Every request and every agent/MCP call carries an **IdentityContext** (or defaults to Guest). This is the core of the “identity-first” design.

**Fields (conceptual)**:

- `user_id`: UUID of the human user (or Guest).
- `agent_id`: UUID of the agent currently acting (if any).
- `delegation_chain`: List of UUIDs from user through agents (e.g. [user, orchestrator, executor).
- `permissions`: Set of permission strings (e.g. read, write, delegate).
- `trust_level`: Numeric (e.g. 0–100); can decrease with delegation depth.
- `keycloak_token`: Raw JWT if present.

**Sources**:

- **Bearer token**: Parsed via Keycloak; user_id and roles/permissions come from the token.
- **Manual context**: JSON in request body (e.g. `identity_context` for testing).
- **Guest**: Fixed UUID and minimal permissions when no token or context is provided.

**Propagation**:

- Set in a context variable (`identity_context_var`) for the duration of the request.
- Passed into MCP tool wrappers so every tool execution is attributed to that identity.
- Stored in audit logs and message payloads (e.g. delegation_chain in A2A messages).

Implementation: `src/identity/context.py` (IdentityContext, from_token, from_dict), and usage in `main.py` and `src/agents/utils.py`.

---

## 2. Agent Cards (A2A Discovery)

**Purpose**: In A2A, agents discover each other via a standard endpoint. The lab implements the **Agent Card** as a JSON document describing an agent (id, name, version, capabilities, public_key, issuer, etc.).

**Storage**: PostgreSQL `agent_cards` table (and optionally served from there or from a static path).

**Endpoint**: `GET /a2a/agents/{identity_id}/.well-known/agent-card.json` returns the card for that agent (or a default if none exists). This mimics the A2A discovery pattern (e.g. `.well-known/agent-card.json`).

**Issuance and verification**:

- **Agent Card MCP**: `issue_card`, `verify_card`, `revoke_card`.
- **Intentional weaknesses**: No strong cryptographic verification of signatures; no mandatory revocation check. So “verify_card” can accept forged or revoked cards — enabling identity and trust threats (IT-07, IT-08).

---

## 3. A2A Messaging (Comms MCP)

**Model**: Inbox/outbox. Agents send messages to other agents by ID; messages are stored in the DB. Optionally, if the target agent is **registered** in-process (e.g. in CommsMCPServer), the server can **deliver** the message by invoking the agent’s `arun()` with the message content — simulating live A2A.

**Tools**:

- `send_message(to_agent_id, message, ...)`: Enqueue a message. Payload can include delegation_chain so the receiver “sees” who delegated.
- `receive_message()`: Dequeue messages for the current agent (mailbox).
- `broadcast(message)`: Send to all agents (no encryption).
- `clear_mailbox(agent_id)`: Delete messages (no auth — intentional).

**Red team surface**:

- **Forgery**: Call `send_message` with a forged `from_agent_id` or payload (C-03, message manipulation).
- **Replay**: Re-send captured messages (no replay protection).
- **Interception**: Messages in DB are readable; broadcast is plaintext.
- **Trust boundary confusion**: Receiver may trust delegation_chain in the message without verifying (orchestration/identity).

---

## 4. Delegation

**Model**: User delegates to an agent; that agent can delegate to another. Stored as **delegations** in PostgreSQL (from_identity_id, to_identity_id, permissions, optional expires_at) and exposed in the **graph** (PuppyGraph) for path queries.

**Intentional weaknesses**:

- **No depth limit**: Arbitrarily long chains (Orchestrator instructions say so; code doesn’t enforce).
- **No expiry enforcement**: Delegations can remain valid indefinitely.
- **Permission escalation**: Delegator can grant permissions they don’t have (in lab logic).
- **Graph recon**: `explore_graph` with Gremlin allows full enumeration of identities and delegations.

So A2A and identity together give a single, coherent attack surface for **Identity & Trust**, **Orchestration**, and **Communication** categories.

---

## 5. Flow Summary

1. **User** (or Guest) is identified → **IdentityContext** created.
2. **User** calls an agent (e.g. Orchestrator) → context passed into agent and tools.
3. **Orchestrator** may call `verify_card` (weak), then `send_message` to Researcher/Executor with delegation_chain in payload.
4. **Researcher/Executor** (when run) may call `receive_message`, see payload and chain; they can trust it or abuse it (intentional).
5. **All actions** are logged with identity context (audit_logs, messages table) so red teamers can observe “who did what.”

---

## 6. References

- Identity context: `src/identity/context.py`, `src/identity/delegation.py`
- Keycloak: `src/identity/keycloak_client.py`; see [02-keycloak.md](02-keycloak.md)
- Agent Cards: `src/mcps/agent_card_mcp.py`, `src/database/models.py` (AgentCard)
- Comms: `src/mcps/comms_mcp.py`
- API: `main.py` (e.g. `/a2a/agents/{id}/.well-known/agent-card.json`, `/agents/{id}/run`)
