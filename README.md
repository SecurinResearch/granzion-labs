# Granzion Agentic AI Red-Teaming Lab

> [!IMPORTANT]
> **🚀 [QUICK START GUIDE](QUICKSTART.md)** - Follow this for a zero-to-hero setup in minutes.

A controlled, intentionally vulnerable sandbox environment designed to validate detection and exploitation of **over 40 threats across 8 core categories** in the Granzion Agentic Threats Taxonomy.

## 🛠️ The Mission

This lab exists to systematically break agentic systems through **identity-centric attacks**. It adopts a "Dark Ops" mental model, focusing on the exploitation of delegation chains, agent-to-agent (A2A) trust boundaries, and Model Context Protocol (MCP) vulnerabilities.

## 🏗️ Architecture

- **4 Specialized Agents**: Orchestrator, Researcher, Executor, Monitor.
- **6 High-Impact MCP Servers**: Identity, Agent Card, Memory (RAG), Data (SQL), Comms (A2A), and Infra.
- **Unified Data Layer**: PostgreSQL + pgvector (Vector) + PuppyGraph (Graph).
- **Security Hardened**: Identity-first checks & Guest/Anonymous access restrictions across ALL core MCP tools.
- **Agno A2A Identity**: Standardized `AgentCard` discovery and handshake protocol.
- **High-Fidelity Dashboard**: React-based "Dark Ops" console for real-time attack monitoring.

## 🚀 Quick Start

Ensure you have **Docker** and **npm** installed, then follow the [QUICKSTART.md](QUICKSTART.md) for the automated setup.

```bash
# 1. Start Infrastructure
docker compose build
docker compose up -d

# 2. Complete Lab Initialization (Database, Keycloak, A2A Cards)
docker compose exec granzion-lab python scripts/full_setup.py

# 3. Seed RAG Memory (Critical for Researcher Agent)
docker compose exec granzion-lab python scripts/debug_rag.py

# 4. Launch Dashboard
cd frontend && npm install && npm run dev
```

## 🎮 Interface Layer

- **Granzion Dashboard**: `http://localhost:5173` (React-powered SCADA-style monitoring)
- **Interactive Console**: Direct agent prompting bypassing orchestrator filters.
- **API Documentation**: `http://localhost:8001/docs` (FastAPI Swagger)
- **Identity Manager**: `http://localhost:8080` (Keycloak Admin)

## 🛡️ Threat & Vulnerability Catalog

The lab covers the critical A2A threat landscape:

- **Identity Confusion**: Delegation depth bypasses and card signature forgery.
- **Memory Poisoning**: RAG context stuffing and vector similarity manipulation.
- **A2A Forgery**: Unmasked message interception and sender impersonation.
- **Privilege Escalation**: Tool parameter injection and container escape.

Full details in [VULNERABILITIES.md](docs/VULNERABILITIES.md) and [threat-taxonomy.md](docs/threat-taxonomy.md).

## 📚 Documentation Reference

- **[ONBOARDING.md](docs/ONBOARDING.md)**: Single-page onboarding — Setup, identity testing, scenarios, and architecture links.
- **[architecture.md](docs/architecture.md)**: System design and identity-first principles.
- **[agents.md](docs/agents.md)**: Agent capabilities, goals, and known flaws.
- **[SEED_DATA.md](docs/SEED_DATA.md)**: Reference for initial users, delegations, and cards.
- **[DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)**: Extending the lab with new agents and MCPs.

---

⚠️ **WARNING**: This lab contains intentionally vulnerable code. **Do NOT deploy to production.** Use only for approved security research and education.
