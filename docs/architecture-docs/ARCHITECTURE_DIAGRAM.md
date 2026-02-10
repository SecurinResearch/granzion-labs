# Architecture Diagram (Mermaid)

Use this Mermaid code in any Markdown viewer or [Mermaid Live Editor](https://mermaid.live) to render the Granzion Lab architecture. **Identity is shown as the central layer** through which all interaction flows.

---

## Full architecture (identity-first)

```mermaid
flowchart TB
    subgraph INTERFACE["🔲 Red Team / Operator Interface"]
        Dashboard["Dashboard (React)"]
        ScenarioHub["Scenario Hub"]
        API["API (FastAPI)"]
        TUI["TUI (optional)"]
    end

    subgraph IDENTITY["🛡️ IDENTITY LAYER (Primary Attack Surface)"]
        direction TB
        Keycloak["Keycloak (OIDC)"]
        AgentCards["Agent Cards (A2A)"]
        Delegation["Delegation Chains"]
        IdentityCtx["IdentityContext\n(user_id, agent_id,\ndelegation_chain, permissions, trust_level)"]
        
        Keycloak --> IdentityCtx
        AgentCards --> IdentityCtx
        Delegation --> IdentityCtx
    end

    subgraph AGENTS["🤖 Agent Layer (Agno)"]
        Orch["Orchestrator\n(coordination, A2A)"]
        Res["Researcher\n(RAG, memory)"]
        Exec["Executor\n(actions, tools)"]
        Mon["Monitor\n(observability gaps)"]
        Orch --- Res
        Orch --- Exec
        Orch --- Mon
    end

    subgraph MCP["🔧 MCP Layer"]
        IdMCP["Identity MCP"]
        CardMCP["Agent Card MCP"]
        CommsMCP["Comms MCP"]
        MemMCP["Memory MCP"]
        DataMCP["Data MCP"]
        InfraMCP["Infra MCP"]
    end

    subgraph DATA["💾 Data Layer"]
        PG["PostgreSQL\n(relational)"]
        PV["pgvector\n(embeddings, RAG)"]
        Puppy["PuppyGraph\n(graph)"]
    end

    subgraph LLM["🧠 LLM Layer"]
        LiteLLM["LiteLLM\n(unified proxy)"]
    end

    INTERFACE -->|"Bearer token / manual context / Guest"| IDENTITY
    IDENTITY -->|"IdentityContext on every request"| AGENTS
    AGENTS -->|"tools + identity_context"| MCP
    MCP --> DATA
    AGENTS -->|"model calls"| LLM
    LLM -->|"routing"| LiteLLM
```

---

## Layered view (identity in the middle)

```mermaid
flowchart TB
    subgraph L1["Layer 1: Red Team Interface"]
        A1[Dashboard] 
        A2[Scenario Hub] 
        A3[API]
    end

    subgraph L2["Layer 2: Identity (core)"]
        B1[Keycloak: Users, Agents, Services]
        B2[Agent Cards: A2A discovery]
        B3[Delegation: User → Agent → Agent]
        B4[IdentityContext: user_id, agent_id, chain, permissions]
    end

    subgraph L3["Layer 3: Agents (Agno)"]
        C1[Orchestrator]
        C2[Researcher]
        C3[Executor]
        C4[Monitor]
    end

    subgraph L4["Layer 4: MCPs"]
        D1[Identity MCP]
        D2[Agent Card MCP]
        D3[Comms MCP]
        D4[Memory MCP]
        D5[Data MCP]
        D6[Infra MCP]
    end

    subgraph L5["Layer 5: Data"]
        E1[PostgreSQL]
        E2[pgvector]
        E3[PuppyGraph]
    end

    subgraph L6["Layer 6: LLM"]
        F1[LiteLLM]
    end

    L1 -->|"token / context"| L2
    L2 -->|"IdentityContext"| L3
    L3 -->|"tools"| L4
    L4 --> L5
    L3 --> L6
```

---

## Identity and delegation detail

```mermaid
flowchart LR
    subgraph Sources["Identity sources"]
        JWT["Keycloak JWT"]
        Manual["Manual context (body)"]
        Guest["Guest (anonymous)"]
    end

    subgraph Resolved["IdentityContext"]
        U["user_id"]
        Ag["agent_id"]
        Chain["delegation_chain"]
        Perm["permissions"]
        Trust["trust_level"]
    end

    subgraph Consumers["Where identity flows"]
        API2["API / run_agent"]
        MCPs["All MCP tools"]
        Audit["Audit logs"]
        Msg["A2A messages"]
    end

    JWT --> Resolved
    Manual --> Resolved
    Guest --> Resolved
    Resolved --> API2
    Resolved --> MCPs
    MCPs --> Audit
    MCPs --> Msg
```

---

## Component ↔ Identity relationship

```mermaid
flowchart TB
    subgraph Keycloak["Keycloak"]
        Realm[granzion-lab realm]
        Users[Users: Alice, Bob, Charlie]
        SAs[Service accounts: sa-orchestrator, ...]
        Roles[Roles / permissions]
    end

    subgraph AppDB["PostgreSQL (lab)"]
        Identities[identities table]
        Delegations[delegations table]
        AgentCardsT[agent_cards table]
        Messages[messages table]
        AuditLog[audit_logs table]
    end

    subgraph Agents["Agents"]
        O[Orchestrator]
        R[Researcher]
        E[Executor]
        M[Monitor]
    end

    Realm --> Users
    Realm --> SAs
    SAs --> Identities
    Users --> Identities
    Identities --> Delegations
    Identities --> AgentCardsT
    Delegations --> O
    Delegations --> R
    O --> Messages
    R --> Messages
    E --> Messages
    O --> AuditLog
    R --> AuditLog
    E --> AuditLog
    M --> AuditLog
```

---

## Data flow with identity

```mermaid
sequenceDiagram
    participant User
    participant API
    participant Keycloak
    participant Identity
    participant Agent
    participant MCP
    participant DB

    User->>API: POST /agents/orchestrator/run + Bearer token
    API->>Keycloak: introspect / decode JWT
    Keycloak-->>API: user_id, roles
    API->>Identity: Build IdentityContext(user_id, permissions, ...)
    API->>Agent: create_orchestrator_agent(identity_context)
    API->>Agent: agent.arun(prompt)
    Agent->>MCP: tool call (identity_context in wrapper)
    MCP->>DB: read/write (with user_id, agent_id in logs)
    DB-->>MCP: result
    MCP-->>Agent: tool result
    Agent-->>API: response
    API-->>User: response + identity (for inspection)
```

Copy any of the code blocks above into a Mermaid-supported editor to view or export the diagrams.
