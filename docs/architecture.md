# Granzion Lab Architecture

## Overview

The Granzion Agentic AI Red-Teaming Lab is a controlled, intentionally vulnerable sandbox environment designed to validate detection and exploitation of all 53 threats across 9 categories in Granzion's Agentic Threats Taxonomy.

## Design Principles

1. **Identity-First**: Identity is the primary attack surface, not prompts
2. **Simplified Architecture**: 4 agents, 5 MCPs (reduced from 6 agents, 7 MCPs in v2.3)
3. **Observable Outcomes**: Concrete state changes, not vague failures
4. **Threat-Driven**: Every component maps to specific threats
5. **Local-First**: `git clone && docker compose up` must work

## Architecture Layers

### 1. Red Team Interface Layer
- **Dashboard (React)**: High-fidelity "Dark Ops" dashboard for real-time monitoring and interaction.
- **Interactive Console**: Direct agent prompting bypassing orchestrator filters.
- **Scenario Hub**: centralized control for attack scenario execution.
- **API**: FastAPI-based REST API for programmatic access (`/api/*`, `/a2a/*`).

### 2. Identity & Trust Layer (Keycloak + Agno A2A)
- **Keycloak**: Primary OIDC provider for users, agents, and services.
- **Agent Cards**: Standardized Agno A2A identity documents stored in PostgreSQL.
- **Discovery**: `/.well-known/agent-card.json` standard endpoint for agent discovery.
- **Delegation Management**: Full tracking of `acting_for` relationships and delegation depth.

### 3. Agent Layer (Agno)
- **Orchestrator Agent**: Coordinates multi-agent workflows, manages A2A handshakes.
- **Researcher Agent**: RAG-based retrieval, memory management.
- **Executor Agent**: Action execution, infrastructure manipulation.
- **Monitor Agent**: System observation (with intentional visibility gaps).

### 4. MCP Layer
- **Identity MCP**: Identity context, delegation, identity type analysis.
- **Agent Card MCP**: Issuance, verification, and revocation of A2A Agent Cards.
- **Memory MCP**: Vector storage, RAG, similarity search.
- **Data MCP**: CRUD operations, SQL execution.
- **Comms MCP**: A2A messaging, interception, and forgery.
- **Infra MCP**: Deployment, command execution, config management.

### 5. Data Layer
- **PostgreSQL**: Relational data (identities, delegations, audit logs, messages)
- **pgvector**: Vector embeddings for RAG
- **PuppyGraph**: Graph queries over PostgreSQL (delegation chains, trust relationships). Provides `explore_graph` tool for deep reconnaissance.
- **Unified Schema**: A shared schema across SQL, Vector, and Graph allows cross-modal vulnerability testing (e.g., SQL injection affecting Graph results).

### 6. Zero-Context (Anonymous) Mode
- **Guest Access**: Enables unauthenticated prompting to simulate external attackers.
- **Guest Identity**: Persistent UUID `00000000-0000-0000-0000-000000000999` with minimal `read:core` permissions.
- **Fallback Logic**: If no OIDC token is provided, the system defaults to the Guest context.

### 7. LLM Layer (LiteLLM)
- Unified proxy for all LLM access
- Model routing and fallbacks
- Token tracking and cost management

## Component Interactions

```
User → TUI/API → Agent → MCP → Database
                   ↓
              Identity Context
                   ↓
              LiteLLM → LLM Provider
```

## Identity Model

Every operation carries an `IdentityContext`:

```python
class IdentityContext:
    user_id: UUID              # Original human user
    agent_id: Optional[UUID]   # Current agent (if delegated)
    delegation_chain: List[UUID]  # Full chain from user to agent
    permissions: Set[str]      # Effective permissions
    keycloak_token: str        # JWT token
    trust_level: int           # 0-100, decreases with delegation depth
```

## Delegation Model

```
User (Alice)
  ├─ delegates to → Orchestrator Agent
  │                      ├─ delegates to → Researcher Agent
  │                      │                      └─ calls → Memory MCP
  │                      └─ delegates to → Executor Agent
  │                                             └─ calls → Data MCP
  └─ directly calls → Identity MCP
```

## Threat Coverage

All 53 threats across 9 categories are covered:

1. **Instruction** (5 threats): Prompt injection, jailbreaking, context manipulation
2. **Tool** (5 threats): Unauthorized access, parameter injection, privilege escalation
3. **Memory** (5 threats): Memory poisoning, RAG injection, context stuffing
4. **Identity & Trust** (6 threats): Identity confusion, impersonation, delegation abuse
5. **Orchestration** (5 threats): Workflow manipulation, task injection
6. **Communication** (5 threats): Message interception, forgery, A2A impersonation
7. **Autonomy** (5 threats): Goal manipulation, unauthorized actions
8. **Infrastructure** (6 threats): Deployment manipulation, config tampering, container escape
9. **Visibility** (5 threats): Log manipulation, observability gaps, detection evasion

## Intentional Vulnerabilities

All vulnerabilities are marked with `# VULNERABILITY:` comments and include:
- Threat ID mapping
- Explanation of the vulnerability
- Expected exploitation method

Example:
```python
# VULNERABILITY: IT-02 - Impersonation
# Allows any agent to impersonate any user without proper authorization
def impersonate(target_user_id: UUID, reason: str) -> str:
    # Intentionally weak: only requires a reason string
    token = keycloak.create_token(target_user_id)
    return token
```

## Testing Strategy

### Dual Testing Approach

1. **Unit Tests**: Verify specific examples and edge cases
2. **Property Tests**: Verify universal properties across all inputs (100+ iterations)

### 22 Correctness Properties

Properties validate that the system behaves correctly across all scenarios:
- Identity tracking (Properties 1-3)
- Data consistency (Property 4)
- LLM routing (Property 5)
- Threat coverage (Properties 6-7)
- Observability (Properties 8-10)
- Scenario execution (Properties 11-13)
- Agent behavior (Properties 14-15)
- Memory state (Property 16)
- Vulnerability persistence (Property 17)
- A2A communication (Property 18)
- Infrastructure impact (Property 19)
- Observability gaps (Property 20)
- Autonomy (Property 21)
- Communication compromise (Property 22)

## Deployment

### Local Deployment (Full Stack)
 
 ```bash
 # 1. Clone & Infra Setup
 git clone <repository-url>
 cd granzion-lab
 cp .env.example .env
 # Edit .env (LiteLLM key is mandatory)
 docker compose build
 docker compose up -d
 
 # 2. Complete Lab Initialization (Database, Keycloak, A2A Cards)
 docker compose exec granzion-lab python scripts/full_setup.py

 # 3. Enrichment (Optional but Recommended for Red Teaming)
 docker compose exec granzion-lab python scripts/enrich_lab_data.py
 
 # 3. Launch Dashboard
 cd frontend
 npm install
 npm run dev
 ```
 
 ### Services Started
 
 - **Granzion Dashboard**: `http://localhost:5173`
 - **Terminal UI**: `http://localhost:8000`
 - **FastAPI Backend / API Docs**: `http://localhost:8001/docs`
 - **Keycloak Admin**: `http://localhost:8080`
 - **LiteLLM Proxy**: `http://localhost:4000`
 - **PuppyGraph UI**: `http://localhost:8081`

## Data Flow

### Scenario Execution Flow
 
 1. User selects scenario from **Dashboard**
 2. **Dashboard** calls API to execute scenario
 3. API captures initial state (before)
 4. API executes attack steps sequentially
 5. Each step involves agent → MCP → database interactions
 6. API captures final state (after)
 7. API compares states and generates evidence
 8. **Dashboard** displays observable changes

### Identity Context Flow

1. User authenticates with Keycloak
2. User delegates to agent
3. Agent receives identity context with delegation chain
4. Agent calls MCP with identity context
5. MCP validates permissions
6. MCP executes operation
7. MCP logs action with identity context
8. Audit log records user_id, agent_id, delegation_chain

## Security Considerations

⚠️ **This lab contains intentionally vulnerable code.**

- Do NOT deploy to production
- Do NOT expose to the internet
- Do NOT use real credentials or sensitive data
- All vulnerabilities are documented and intentional
- Use only for security research and education

## Extension Points

The lab is designed to be extensible:

1. **New Agents**: Add new agent types in `src/agents/`
2. **New MCPs**: Add new MCP servers in `src/mcps/`
3. **New Scenarios**: Add scenario files in `scenarios/`
4. **New Threats**: Update threat taxonomy and add corresponding vulnerabilities
5. **New Properties**: Add property tests in `tests/property/`

## References

- [Threat Taxonomy](threat-taxonomy.md)
- [Scenario Creation Guide](scenario-creation-guide.md)
- [Keycloak Automation](keycloak-automation.md)
