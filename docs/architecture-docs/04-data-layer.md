# Component: Data Layer

This document describes the **data layer** in Granzion Lab: PostgreSQL, pgvector, and PuppyGraph, and how they support red teaming.

---

## 1. Overview

The lab uses a **unified data story** with one primary database (PostgreSQL) and two extensions/layers:

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Relational** | PostgreSQL | Identities, delegations, agent cards, messages, audit logs, app_data |
| **Vector** | pgvector | Embeddings for RAG / memory (Memory MCP, Researcher) |
| **Graph** | PuppyGraph | Delegation chains, trust relationships; Gremlin queries (Identity MCP) |

Using one DB (plus PuppyGraph’s integration) keeps setup simple and allows **cross-modal** attacks (e.g. SQL injection affecting what the graph or RAG see).

---

## 2. PostgreSQL

- **Role**: Primary store for all structured data.
- **Init**: Scripts in `db/init/` run in order (e.g. `00_init_keycloak_db.sql`, `01_init_extensions.sql`, `02_create_schema.sql`, `03_seed_data.sql`, `04_realistic_seed_data.sql`).
- **Schema (conceptual)**:
  - **identities**: Users, agents, services (id, name, type, permissions, etc.).
  - **delegations**: Who delegated to whom, with which permissions (optional expiry).
  - **agent_cards**: A2A cards (agent_id, version, capabilities, public_key, issuer_id, is_verified, is_revoked, card_metadata).
  - **messages**: A2A messages (from_agent_id, to_agent_id, payload, timestamps).
  - **audit_logs**: Action logs with identity context (user_id, agent_id, action, resource, etc.).
  - **app_data**: Generic key-value or JSON rows (table_name, data) for application data used in scenarios and agents.
  - **Embeddings / memory**: Tables used by pgvector for document chunks and embeddings (see Memory MCP and Researcher).
- **Keycloak**: Can use a separate database (e.g. `keycloak`) on the same Postgres instance for realm/client/user storage.
- **Access**: The app uses SQLAlchemy (sync engine, sessions) in `src/database/` (connection.py, models.py, queries.py). MCPs and scenarios use these to read/write.

---

## 3. pgvector

- **Role**: Vector similarity search for RAG and agent memory.
- **Setup**: Extension enabled in `db/init/` (e.g. `CREATE EXTENSION vector`). Tables store document chunks and embedding vectors.
- **Usage**: Memory MCP calls embedding generation (e.g. via a small model or external API) and stores/retrieves via pgvector. Researcher agent uses Memory MCP for “search memory” and “embed document.”
- **Red team**: Poisoning (inject malicious or misleading documents), context stuffing (retrieve too much), exfiltration (retrieve sensitive stored content). No embedding or retrieval sanitization (intentional).

---

## 4. PuppyGraph

- **Role**: Graph view over data (e.g. identities as vertices, delegations as edges). Used for “explore trust,” “find delegation paths,” and similar.
- **Access**: Identity MCP’s `explore_graph` tool sends **Gremlin** queries to PuppyGraph. Schema is defined in `config/puppygraph/schema.json` (or equivalent).
- **Red team**: Unrestricted Gremlin allows full graph reconnaissance (map all identities and delegations, find privilege paths). No query sanitization (intentional). Documented as IT-05 / visibility in VULNERABILITIES.md.

---

## 5. Unified Schema and Cross-Modal Testing

- **Unified schema**: Same identities and delegations that live in PostgreSQL are exposed to the graph layer so that:
  - Relational queries (SQL) and graph queries (Gremlin) can be used to test different attack surfaces.
  - One vulnerability (e.g. SQL injection in Data MCP) could affect data that both SQL and graph views rely on.
- **Seed data**: `03_seed_data.sql` and `04_realistic_seed_data.sql` (and optionally `scripts/enrich_lab_data.py`) populate identities, delegations, app_data, and optionally RAG content so scenarios and agents have realistic targets.

---

## 6. References

- Schema and init: `db/init/`, `src/database/models.py`
- Connection and queries: `src/database/connection.py`, `src/database/queries.py`, `src/database/graph.py`
- PuppyGraph config: `config/puppygraph/`
- Enrichment: `scripts/enrich_lab_data.py`, `docs/SEED_DATA.md`
