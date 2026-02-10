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
| **[CTO-01-EXECUTIVE-SUMMARY-AND-CURRENT-STATE.md](CTO-01-EXECUTIVE-SUMMARY-AND-CURRENT-STATE.md)** | CTO brief Part 1: What the lab is, why we built it, what exists today (delivered vs gaps), how it fits the taxonomy. |
| **[CTO-02-DIAGRAMS-EXPLAINED-AND-CURRENT-IMPLEMENTATION.md](CTO-02-DIAGRAMS-EXPLAINED-AND-CURRENT-IMPLEMENTATION.md)** | CTO brief Part 2: Crystal-clear explanation of every architecture and workflow diagram; what each element means, where it lives in code, current vs ideal. |
| **[CTO-03-GAPS-IMPROVEMENTS-AND-ROADMAP.md](CTO-03-GAPS-IMPROVEMENTS-AND-ROADMAP.md)** | CTO brief Part 3: Full list of gaps and improvements (P0–P3), concrete actions, verification, effort; out-of-scope; suggested roadmap and one-page summary. |

## Quick links

- **New to the lab?** Start with [WORKFLOW.md](WORKFLOW.md), then [ARCHITECTURE.md](ARCHITECTURE.md).
- **Implementing or debugging?** Use the component docs (01–06) and the main [../specs/](specs) and [../VULNERABILITIES.md](../VULNERABILITIES.md).
- **Explaining to stakeholders?** Use [ARCHITECTURE.md](ARCHITECTURE.md) and [WORKFLOW.md](WORKFLOW.md).
- **Planning improvements?** Use [RED_TEAM_TAXONOMY_FIT_AND_CRITIQUE.md](RED_TEAM_TAXONOMY_FIT_AND_CRITIQUE.md).
- **Presenting to CTO / leadership?** Use the three CTO briefs in order: [CTO-01](CTO-01-EXECUTIVE-SUMMARY-AND-CURRENT-STATE.md) (executive summary and current state) → [CTO-02](CTO-02-DIAGRAMS-EXPLAINED-AND-CURRENT-IMPLEMENTATION.md) (diagrams explained) → [CTO-03](CTO-03-GAPS-IMPROVEMENTS-AND-ROADMAP.md) (gaps, improvements, roadmap).