# Workflow Diagrams (Mermaid)

Use this Mermaid code in any Markdown viewer or [Mermaid Live Editor](https://mermaid.live) to render Granzion Lab workflows. **Identity is shown in each flow** where it applies.

---

## 1. Lab setup workflow

```mermaid
flowchart TB
    Start([Start]) --> Clone[Clone repo, copy .env]
    Clone --> Compose[docker compose up -d]
    Compose --> Wait[Wait: Postgres, Keycloak, PuppyGraph]
    Wait --> FullSetup[full_setup.py]
    FullSetup --> Schema[DB schema + extensions]
    FullSetup --> KeycloakSetup[Keycloak: realm, clients, roles]
    FullSetup --> Users[Seed users: Alice, Bob, Charlie]
    FullSetup --> Agents[Seed agent identities]
    FullSetup --> Cards[Seed Agent Cards]
    Schema --> KeycloakSetup
    KeycloakSetup --> Users
    Users --> Agents
    Agents --> Cards
    Cards --> Enrich{Enrich data?}
    Enrich -->|Yes| EnrichScript[enrich_lab_data.py]
    Enrich -->|No| Access
    EnrichScript --> Access[Access: Dashboard, API, Keycloak UI]
    Access --> End([Ready for red team])
```

---

## 2. Identity resolution (every request)

```mermaid
flowchart TB
    Req([Incoming request]) --> HasBearer{Bearer token?}
    HasBearer -->|Yes| ParseKC[Parse JWT via Keycloak]
    ParseKC --> BuildCtx[Build IdentityContext:\nuser_id, permissions, ...]
    HasBearer -->|No| HasBody{identity_context in body?}
    HasBody -->|Yes| FromBody[IdentityContext.from_dict]
    FromBody --> EnsureDB[Ensure identity exists in DB]
    EnsureDB --> BuildCtx
    HasBody -->|No| Guest[Guest context:\nfixed UUID, minimal permissions]
    Guest --> BuildCtx
    BuildCtx --> SetVar[Set identity_context_var]
    SetVar --> Use[Use in agent + MCPs]
    Use --> ClearVar[Clear context after request]
    ClearVar --> Out([Response with identity for inspection])
```

---

## 3. Scenario execution workflow

```mermaid
flowchart TB
    Select([Red teamer selects scenario]) --> Load[Engine loads scenario by ID]
    Load --> Setup[Setup: create test users, agents, delegations, data]
    Setup --> StateBefore[state_before: capture initial state]
    StateBefore --> Steps[For each AttackStep: step.execute]
    Steps --> StepDetail[Step calls MCPs / DB / identity APIs]
    StepDetail --> StateAfter[state_after: capture final state]
    StateAfter --> Criteria[For each Criterion: criterion.verify]
    Criteria --> AllPass{All criteria passed?}
    AllPass -->|Yes| Success[ScenarioResult: success, evidence]
    AllPass -->|No| Fail[ScenarioResult: failed, errors]
    Success --> Report[Dashboard/API: before/after, evidence]
    Fail --> Report
    Report --> End([Red teamer inspects outcome])
```

---

## 4. Scenario execution with identity

```mermaid
sequenceDiagram
    participant RT as Red teamer
    participant API
    participant Engine
    participant Setup
    participant Steps
    participant MCP
    participant DB

    RT->>API: Run scenario (e.g. s01)
    API->>Engine: execute_scenario(s01)
    Engine->>Setup: scenario.setup()
    Note over Setup: Create Alice, Bob, Orchestrator, Executor in DB
    Setup->>DB: identities, delegations
    Engine->>Engine: state_before()
    Engine->>Steps: step1.execute() ... stepN.execute()
    Steps->>MCP: e.g. identity_mcp.impersonate (with test context)
    MCP->>DB: audit_log, messages
    Steps->>DB: read/write for evidence
    Engine->>Engine: state_after()
    Engine->>Engine: criterion.verify() for each
    Engine->>API: ScenarioResult(initial_state, final_state, evidence)
    API->>RT: success/failure + observable state
```

---

## 5. Agent chat workflow (with identity)

```mermaid
flowchart TB
    User([User sends prompt]) --> Post[POST /agents/orchestrator/run]
    Post --> Resolve[Resolve identity]
    Resolve --> Ctx[IdentityContext available]
    Ctx --> CreateAgent[Create fresh agent with identity_context]
    CreateAgent --> Register[Register instance in Comms A2A bridge]
    Register --> SetCtx[Set identity_context_var]
    SetCtx --> Arun[agent.arun(prompt)]
    Arun --> LLM[Agent uses LiteLLM for reasoning]
    Arun --> Tools[Agent calls MCP tools]
    Tools --> MCPWithCtx[Each tool receives identity_context]
    MCPWithCtx --> DB[(DB / pgvector / graph)]
    DB --> ToolResult[Tool result]
    ToolResult --> Arun
    LLM --> Arun
    Arun --> Response[Response content]
    Response --> ClearCtx[Clear identity_context_var]
    ClearCtx --> Return[Return response + identity to caller]
    Return --> User
```

---

## 6. End-to-end identity flow

```mermaid
flowchart LR
    subgraph In["Input"]
        T[Bearer token]
        M[Manual context]
        G[Guest]
    end

    subgraph Resolve["Resolved identity"]
        IC[IdentityContext]
    end

    subgraph Propagation["Propagation"]
        AV[identity_context_var]
        Wrap[MCP tool wrappers]
        Agent[Agent instance]
    end

    subgraph Persistence["Persistence"]
        AL[audit_logs]
        MSG[messages]
        Del[delegations]
    end

    T --> IC
    M --> IC
    G --> IC
    IC --> AV
    IC --> Agent
    AV --> Wrap
    Wrap --> AL
    Wrap --> MSG
    Agent --> Del
```

---

## 7. A2A message flow (orchestrator → researcher)

```mermaid
sequenceDiagram
    participant User
    participant API
    participant Orch as Orchestrator Agent
    participant Comms as Comms MCP
    participant DB
    participant Res as Researcher Agent

    User->>API: Prompt: "Ask researcher to find X"
    API->>Orch: arun(prompt) with IdentityContext
    Orch->>Comms: send_message(to=Researcher, message=...)
    Comms->>DB: Insert Message
    Comms->>Comms: Is Researcher in _active_agents?
    alt Registered
        Comms->>Res: arun(A2A notification) with delegated context
        Res->>Res: Memory/Data MCP tools
        Res->>Comms: send_message(to=Orchestrator, reply)
        Comms->>DB: Insert reply Message
    end
    Comms-->>Orch: success
    Orch->>Orch: receive_message (optional)
    Orch-->>API: response
    API-->>User: response
```

---

## 8. High-level workflow summary

```mermaid
flowchart TB
    subgraph Operator["Operator actions"]
        A1[Setup lab]
        A2[Run scenario]
        A3[Chat with agent]
    end

    subgraph Identity["Identity (every path)"]
        I1[Keycloak / Guest / Manual]
        I2[IdentityContext]
        I3[Audit + messages]
    end

    subgraph System["System"]
        S1[Scenarios: setup → steps → criteria → evidence]
        S2[Agents: prompt → tools → MCP → DB]
        S3[State: before/after, logs]
    end

    A1 --> I1
    A2 --> I2
    A3 --> I2
    I1 --> I2
    I2 --> S1
    I2 --> S2
    S1 --> S3
    S2 --> I3
    S2 --> S3
```

Copy any of the code blocks above into a Mermaid-supported editor to view or export the diagrams.
