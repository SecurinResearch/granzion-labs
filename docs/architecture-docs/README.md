# Architecture & Documentation

This folder contains the **canonical architecture**, **workflow**, **component guides**, and **analysis** for the Granzion Agentic AI Red-Teaming Lab.

## Contents

| Document | Purpose |
|----------|---------|
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Project architecture: layers, components, design principles, deployment. |
| **[WORKFLOW.md](WORKFLOW.md)** | End-to-end workflow: setup, scenario execution, agent chat, identity and data flow. Easy to use when explaining the lab to others. |
| **[01-agents.md](01-agents.md)** | Agents (Orchestrator, Researcher, Executor, Monitor): roles, tools, vulnerabilities. |
| **[02-keycloak.md](02-keycloak.md)** | Keycloak: automation, roles, users, service accounts, red team relevance. |
| **[03-mcps.md](03-mcps.md)** | MCP servers: Identity, Agent Card, Comms, Memory, Data, Infra; tools and threats. |
| **[04-data-layer.md](04-data-layer.md)** | Data layer: PostgreSQL, pgvector, PuppyGraph; unified schema and cross-modal testing. |
| **[05-scenarios.md](05-scenarios.md)** | Scenario framework and catalog: structure, engine, discovery, adding new scenarios. |
| **[06-a2a-and-identity.md](06-a2a-and-identity.md)** | A2A and identity: IdentityContext, Agent Cards, Comms MCP, delegation. |
| **[ROGUE_INSPIRATION_ANALYSIS.md](ROGUE_INSPIRATION_ANALYSIS.md)** | Whether and how the lab took inspiration from the Rogue repo. |
| **[RED_TEAM_TAXONOMY_FIT_AND_CRITIQUE.md](RED_TEAM_TAXONOMY_FIT_AND_CRITIQUE.md)** | How the lab fits red teaming for the Agentic Threats Taxonomy, plus critique and prioritized improvements (including orchestrator issues). |
| **[ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md)** | Mermaid diagrams: full architecture (identity-first), layered view, identity/delegation detail, component–identity relationship, data flow sequence. |
| **[WORKFLOW_DIAGRAM.md](WORKFLOW_DIAGRAM.md)** | Mermaid diagrams: lab setup, identity resolution, scenario execution, agent chat, end-to-end identity flow, A2A message flow, workflow summary. |
- **New to the lab?** Start with [WORKFLOW.md](WORKFLOW.md), then [ARCHITECTURE.md](ARCHITECTURE.md).
- **Implementing or debugging?** Use the component docs (01–06) and the main [../VULNERABILITIES.md](../VULNERABILITIES.md).
- **Explaining to stakeholders?** Use [ARCHITECTURE.md](ARCHITECTURE.md) and [WORKFLOW.md](WORKFLOW.md).
- **Planning improvements?** Use [RED_TEAM_TAXONOMY_FIT_AND_CRITIQUE.md](RED_TEAM_TAXONOMY_FIT_AND_CRITIQUE.md).