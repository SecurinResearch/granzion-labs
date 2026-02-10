# Granzion Lab Agents

This document describes the 4 Agno agents implemented in Granzion Lab, their capabilities, tools, and intentional vulnerabilities.

## Overview

All agents are implemented using the [Agno framework](https://docs.agno.com/) and integrate with MCP servers for their capabilities. Each agent has specific intentional vulnerabilities that enable the 53 threats in the taxonomy to be exploited.

## Agent Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AGENT LAYER (Agno)                        │
│                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐ │
│  │  Orchestrator  │  │   Researcher   │  │   Executor   │ │
│  │     Agent      │  │     Agent      │  │    Agent     │ │
│  │                │  │                │  │              │ │
│  │  Coordinates   │  │  RAG + Memory  │  │ Tool Calling │ │
│  │  A2A flows     │  │  Retrieval     │  │   Actions    │ │
│  └────────────────┘  └────────────────┘  └──────────────┘ │
│          │                    │                    │        │
│          └────────────────────┴────────────────────┘        │
│                       A2A Communication                     │
│                              │                              │
│                              ▼                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                  Monitor Agent                        │  │
│  │  (Intentionally blind - demonstrates visibility gaps)│  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                        MCP Servers
```

## 1. Orchestrator Agent

**ID:** `00000000-0000-0000-0000-000000000101`  
**Type:** Orchestrator  
**Role:** Coordinates multi-agent workflows and manages A2A communication

### Capabilities
 
 - Send direct messages to other agents
 - Broadcast messages to all agents
 - Receive messages from other agents
 - **Standard A2A Handshake**: Verify remote agent identity via Agno Agent Cards
 - **Agent Identity Management**: Issue and rotate its own Agent Card
 
 ### MCP Tools
 
 - **Comms MCP:**
   - `send_message` / `receive_message` / `broadcast`
   - `clear_mailbox`: Reset conversation context or purge agent communications.
 
 - **Agent Card MCP:**
   - `issue_card`: Update its own A2A capabilities
   - `verify_card`: Handshake with another agent
   - `revoke_card`: Revoke trust in a compromised agent
 
 - **Identity MCP:**
   - `get_identity_context` / `get_identity_type` / `get_delegation_chain`
   - `explore_graph`: Deep graph reconnaissance via Gremlin queries.

### Intentional Vulnerabilities
 
 1. **No delegation depth limit** - Can create arbitrarily long delegation chains
 2. **Trusts A2A messages** - No sender identity verification
 3. **No Agent Card Signature Verification** - Accepts forged Agent Cards during handshakes
 4. **No revocation list checks** - Continues to trust revoked Agent Cards
 5. **Broadcasts without encryption** - All messages in plaintext
 
 ### Threats Covered
 
 - **Orchestration (Category 5):** Workflow manipulation, A2A confusion
 - **Communication (Category 6):** Message interception, routing attacks
 - **Identity & Trust (Category 4):** Delegation chain manipulation, A2A impersonation

## 2. Researcher Agent

**ID:** `00000000-0000-0000-0000-000000000102`  
**Type:** Researcher  
**Role:** Performs RAG-based information retrieval and manages memory

### Capabilities

- Embed documents into vector memory
- Search for similar documents using semantic search
- Retrieve context for agent queries
- Read data from database (read-only)
- Communicate with other agents

### MCP Tools

- **Memory MCP:**
  - `embed_document` - Store documents with embeddings
  - `search_similar` - Vector similarity search
  - `get_context` - Retrieve agent context

- **Data MCP:**
  - `read_data` - Read-only data access

- **Comms MCP:**
  - `send_message` - Send messages
  - `receive_message` - Receive messages

### Intentional Vulnerabilities

1. **No embedding validation** - Accepts malicious content without sanitization
2. **Trusts retrieved context** - Uses RAG results directly without verification
3. **No source verification** - Doesn't verify document provenance
4. **Similarity threshold bypass** - Can be tricked with boosted scores
5. **Context window stuffing** - No limit on retrieved context size

### Threats Covered

- **Memory (Category 3):** Memory poisoning, RAG manipulation, context injection
- **Instruction (Category 1):** Prompt injection via retrieved documents
- **Tool (Category 2):** RAG tool misuse

## 3. Executor Agent

**ID:** `00000000-0000-0000-0000-000000000103`  
**Type:** Executor  
**Role:** Executes actions via tools and performs infrastructure changes

### Capabilities

- Create, read, update, and delete data
- Deploy services and infrastructure
- Execute system commands
- Modify configurations
- Read environment variables
- Communicate with other agents

### MCP Tools

- **Data MCP:**
  - `create_data` - Create records
  - `read_data` - Read records
  - `update_data` - Update records
  - `delete_data` - Delete records

- **Infra MCP:**
  - `deploy_service` - Deploy services
  - `execute_command` - Execute shell commands
  - `modify_config` - Modify configurations
  - `read_env` - Read environment variables

- **Comms MCP:**
  - `send_message` - Send messages
  - `receive_message` - Receive messages

### Intentional Vulnerabilities

1. **No parameter sanitization** - Tool parameters not validated (SQL injection, command injection)
2. **Inherits full user permissions** - No permission downscoping
3. **No action confirmation** - Executes destructive actions immediately
4. **Command injection** - Allows arbitrary shell commands
5. **No rollback mechanism** - Changes are permanent

### Threats Covered

- **Tool (Category 2):** Tool parameter injection, unauthorized tool access
- **Infrastructure (Category 8):** Deployment manipulation, config tampering
- **Autonomy (Category 7):** Goal manipulation, unauthorized actions

## 4. Monitor Agent

**ID:** `00000000-0000-0000-0000-000000000104`  
**Type:** Monitor  
**Role:** Observes system activity with intentional gaps

### Capabilities

- Read audit logs from database (limited)
- Receive broadcast messages (not direct messages)
- Generate monitoring reports
- Detect simple rule-based anomalies

### MCP Tools

- **Data MCP:**
  - `read_data` - Read audit logs only (limited access)

- **Comms MCP:**
  - `receive_message` - Receive broadcasts only (not direct messages)

### Intentional Vulnerabilities

1. **Incomplete logging** - Only sees broadcasts, not direct A2A messages
2. **No real-time monitoring** - Polls logs periodically (30 second delay)
3. **Log manipulation possible** - Attackers can modify logs before Monitor reads them
4. **Simple rule-based detection** - Easily bypassed by sophisticated attacks
5. **Blind to identity context** - Doesn't see delegation chains or permission changes

### Threats Covered

- **Visibility (Category 9):** Observability gaps, log manipulation, blind spots
- **Communication (Category 6):** Unmonitored channels

## Implementation Details

### MCP Integration

Agents use direct Python integration with MCP servers (not CLI-based):

```python
from src.agents.utils import create_mcp_tool_wrapper

# Wrap MCP tool as Agno-compatible function
tool = create_mcp_tool_wrapper(
    mcp_server=comms_mcp,
    tool_name="send_message",
    identity_context=identity_ctx
)

# Pass to Agno agent
agent = Agent(
    name="Orchestrator",
    tools=[tool],
    ...
)
```

### Identity Context Flow

Every agent action carries identity context:

```python
identity_ctx = IdentityContext(
    user_id=user_id,
    agent_id=agent_id,
    delegation_chain=[user_id, agent_id],
    permissions={"read", "write"},
    trust_level=80,
)
```

### LiteLLM Integration

All agents use LiteLLM proxy for model access:

```python
agent = Agent(
    model=OpenAIChat(
        id=settings.DEFAULT_MODEL,
        api_key=settings.LITELLM_API_KEY,
        base_url=settings.LITELLM_URL,
    ),
    ...
)
```

## Testing

### Property Tests

- **Property 14:** Comprehensive agent behavior visibility
  - Validates that agent reasoning, tool calls, delegation chain, and identity context are all observable
  
- **Property 15:** Permission violation highlighting
  - Validates that permission violations are detected and both attempted and actual permissions are shown

### Unit Tests

Each agent has initialization tests, tool configuration tests, and vulnerability documentation tests.

## Usage

### Creating Agents

```python
from src.agents import (
    create_orchestrator_agent,
    create_researcher_agent,
    create_executor_agent,
    create_monitor_agent,
)

# Create all agents
orchestrator = create_orchestrator_agent()
researcher = create_researcher_agent()
executor = create_executor_agent()
monitor = create_monitor_agent()
```

### Getting Agent by ID

```python
from src.agents.utils import get_agent_by_id
from uuid import UUID

agent = get_agent_by_id(UUID("00000000-0000-0000-0000-000000000101"))
```

### Getting All Agents

```python
from src.agents.utils import get_all_agents

agents = get_all_agents()
# Returns: {"orchestrator": ..., "researcher": ..., "executor": ..., "monitor": ...}
```

## Next Steps

1. Implement scenario framework (Task 13)
2. Implement attack scenarios that exploit agent vulnerabilities (Tasks 14-15)
3. Implement TUI for scenario execution and agent behavior visualization (Task 19)
4. Test all agents with real attack scenarios (Task 23)

## References

- [Agno Documentation](https://docs.agno.com/)
- [Design Document](../design.md)
- [MCP Servers](../src/mcps/)
- [Property Tests](../tests/property/test_agent_properties.py)
