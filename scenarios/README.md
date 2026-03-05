# Attack Scenarios

This directory contains all attack scenario definitions for the Granzion Lab.

## Scenario Structure

Each scenario is defined in a Python file with the following structure:

```python
from src.scenarios import AttackScenario, AttackStep, Criterion

scenario = AttackScenario(
    id="S01",
    name="Identity Confusion via Delegation Chain",
    category="Identity & Trust",
    difficulty="Medium",
    description="Exploit delegation chain manipulation...",
    threat_ids=["IT-01", "IT-03", "IT-04", "O-03"],
    
    setup=setup_function,
    attack_steps=[...],
    success_criteria=[...],
    
    state_before=capture_before_state,
    state_after=capture_after_state,
    observable_changes=["delegation_chain", "permissions", "audit_log"],
    
    agents_involved=["Orchestrator", "Executor"],
    mcps_involved=["Identity", "Data"],
    estimated_duration=30
)
```

## Available Scenarios

### Identity & Trust (Category 4)
- **S01**: Identity Confusion via Delegation Chain

### Memory (Category 3)
- **S02**: Memory Poisoning via RAG Injection

### Communication (Category 6)
- **S03**: A2A Message Forgery

### Tool (Category 2)
- **S04**: Tool Parameter Injection

### Orchestration (Category 5)
- **S05**: Orchestration Workflow Hijacking

### Memory (Category 3)
- **S06**: Context Window Stuffing

### Instruction (Category 1)
- **S07**: Jailbreaking via LiteLLM

### Infrastructure (Category 8)
- **S08**: Unauthorized Infrastructure Actions

### Visibility (Category 9)
- **S09**: Audit Log Manipulation

### Memory (Category 3)
- **S10**: Cross-Agent Memory Access

### Autonomy (Category 7)
- **S11**: Goal Manipulation

### Identity & Trust (Category 4)
- **S12**: Credential Theft

### Infrastructure (Category 8)
- **S13**: Privilege Escalation via Infrastructure

### Infrastructure (Category 8)
- **S14**: Container Escape

### Visibility (Category 9)
- **S15**: Detection Evasion

### Communication (Category 6)
- **S16**: Replay Attack (A2A message replay)

### Orchestration (Category 5) — Agent-driven
- **S17**: Agent-Driven Orchestration (Research Flow) — *prompt → API → agent → assert state*

## Agent-driven vs direct MCP/DB

- **Agent-driven**: Scenario sends a prompt to an agent via the API (`POST /agents/{id}/run`), then asserts on DB/audit/messages. Proves the vulnerability is exploitable *through the agent*.
- **Direct MCP/DB**: Scenario calls MCPs or DB directly. Proves the vulnerability exists; does not prove an agent would do the same when prompted.

See [threat_coverage.md](../docs/threat_coverage.md) for the full scenario–type table.

## Creating New Scenarios

See the [Scenario Creation Guide](../docs/scenario-creation-guide.md) for detailed instructions on creating new attack scenarios.
