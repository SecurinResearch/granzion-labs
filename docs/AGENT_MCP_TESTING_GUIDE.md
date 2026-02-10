# Agent & MCP Testing Guide

This guide shows you how to verify that agents and MCPs are working correctly in the Granzion Lab.

## Quick Tests (5 minutes)

### 1. MCP Tool Registration Test

Verify all MCP servers have registered their tools:

```bash
docker exec granzion-lab-app python verify_all.py
```

**Expected Output:**
```
✓ comms-mcp: 5 tools registered
✓ identity-mcp: 5 tools registered
✓ memory-mcp: 5 tools registered
✓ data-mcp: 5 tools registered
✓ infra-mcp: 5 tools registered
```

### 2. Quick Scenario Test

Run a simple attack scenario to test the full stack:

```bash
docker exec granzion-lab-app python verify_all.py --type agents
```

This tests:
- ✓ All 4 agents (Orchestrator, Researcher, Executor, Monitor)
- ✓ All 5 MCP servers with 25 tools
- ✓ Database connections (PostgreSQL, Vector DB)
- ✓ Identity system
- ✓ Scenario engine

---

## Interactive Testing (10-30 minutes)

### Option A: Use the TUI Dashboard

1. **Open the TUI** in your browser:
   ```
   http://localhost:8000
   ```

2. **Navigate to Scenarios** section

3. **Select a scenario** to execute (start with easy ones):
   - S12: Credential Theft (Easy)
   - S02: Memory Poisoning (Medium)
   - S01: Identity Confusion (Medium)

4. **Execute and observe**:
   - Watch agent interactions
   - See MCP tool calls
   - View audit logs
   - Check success criteria

### Option B: Use the API

1. **Open API Docs**:
   ```
   http://localhost:8001/docs
   ```

2. **Test Individual Components**:

   **Test Agents:**
   ```bash
   curl http://localhost:8001/agents
   ```

   **Test Scenarios:**
   ```bash
   curl http://localhost:8001/scenarios
   ```

   **Test Threat Taxonomy:**
   ```bash
   curl http://localhost:8001/threats
   ```

3. **Execute a Scenario via API**:
   ```bash
   curl -X POST http://localhost:8001/scenarios/s01/run \
     -H "Content-Type: application/json" \
     -d '{
       "identity_context": {
         "user_id": "00000000-0000-0000-0000-000000000001",
         "username": "alice",
         "roles": ["read", "write"]
       }
     }'
   ```

---

## Comprehensive Testing (1-2 hours)

### Run All Unit Tests

Test individual MCP tools and components:

```bash
docker exec granzion-lab-app pytest tests/unit/ -v
```

**Tests:**
- `test_identity_mcp.py` - Identity MCP tools
- `test_memory_mcp.py` - Memory MCP tools
- `test_data_mcp.py` - Data MCP tools
- `test_comms_mcp.py` - Communications MCP tools
- `test_infra_mcp.py` - Infrastructure MCP tools

### Run Property-Based Tests

Test system properties and invariants:

```bash
docker exec granzion-lab-app pytest tests/property/ -v
```

**Tests:**
- `test_agent_properties.py` - Agent behavior properties
- `test_identity_properties.py` - Identity system properties
- `test_memory_properties.py` - Memory system properties
- `test_communication_properties.py` - A2A communication properties
- `test_infrastructure_properties.py` - Infrastructure properties

### Run Scenario Tests

Test all 15 attack scenarios:

```bash
docker exec granzion-lab-app pytest tests/scenarios/ -v
```

---

## Manual Agent Testing

### Test Individual Agents

Create a Python script to test specific agents:

```python
from src.agents.orchestrator import create_orchestrator_agent
from src.agents.researcher import create_researcher_agent
from src.agents.executor import create_executor_agent
from src.agents.monitor import create_monitor_agent

# Create agents
orchestrator = create_orchestrator_agent()
researcher = create_researcher_agent()
executor = create_executor_agent()
monitor = create_monitor_agent()

print(f"Orchestrator: {orchestrator.agent_id}")
print(f"Researcher: {researcher.agent_id}")
print(f"Executor: {executor.agent_id}")
print(f"Monitor: {monitor.agent_id}")

# Test agent goals
print(f"\nOrchestrator goals: {orchestrator.get_goals()}")
```

### Test Individual MCP Tools

```python
from src.mcps.identity_mcp import get_identity_mcp_server
from src.mcps.memory_mcp import get_memory_mcp_server
from src.mcps.data_mcp import get_data_mcp_server
from src.mcps.comms_mcp import get_comms_mcp_server
from src.mcps.infra_mcp import get_infra_mcp_server

# Get MCP servers
identity_mcp = get_identity_mcp_server()
memory_mcp = get_memory_mcp_server()
data_mcp = get_data_mcp_server()
comms_mcp = get_comms_mcp_server()
infra_mcp = get_infra_mcp_server()

# Test a tool
result = identity_mcp.call_tool(
    "get_identity_context",
    {"user_id": "test-user"}
)
print(f"Identity context: {result}")
```

---

## Red Team Testing (Advanced)

### Execute All 15 Attack Scenarios

Run the complete red team test suite:

```bash
docker exec granzion-lab-app python -m pytest tests/scenarios/test_scenario_execution.py -v
```

### Execute Specific Threat Categories

Test scenarios by threat category:

**Instruction Threats:**
```bash
# S02: Memory Poisoning
# S06: Context Window Stuffing
# S07: Jailbreaking
```

**Identity & Trust Threats:**
```bash
# S01: Identity Confusion
# S03: A2A Message Forgery
# S12: Credential Theft
```

**Tool Threats:**
```bash
# S04: Tool Parameter Injection
# S08: Unauthorized Infrastructure
```

**Orchestration Threats:**
```bash
# S05: Workflow Hijacking
```

**Autonomy Threats:**
```bash
# S11: Goal Manipulation
```

**Infrastructure Threats:**
```bash
# S13: Privilege Escalation
# S14: Container Escape
```

**Visibility Threats:**
```bash
# S09: Audit Log Manipulation
# S15: Detection Evasion
```

### Custom Attack Scenarios

Create your own attack scenarios following the guide:

```bash
# Read the scenario creation guide
cat granzion-lab/docs/scenario-creation-guide.md
```

---

## Monitoring & Observability

### View Audit Logs

```bash
docker exec granzion-lab-app tail -f logs/granzion-lab.log
```

### Check Database State

```bash
# PostgreSQL
docker exec granzion-lab-postgres psql -U granzion -d granzion_lab -c "SELECT COUNT(*) FROM audit_logs;"

# Check agent goals
docker exec granzion-lab-postgres psql -U granzion -d granzion_lab -c "SELECT * FROM agent_goals;"

# Check memory documents
docker exec granzion-lab-postgres psql -U granzion -d granzion_lab -c "SELECT COUNT(*) FROM memory_documents;"
```

### Monitor Agent Activity

```bash
# Watch agent logs in real-time
docker logs -f granzion-lab-app | grep "agent"
```

---

## Troubleshooting

### Agents Not Responding

1. Check agent initialization:
   ```bash
   docker exec granzion-lab-app python -c "from src.agents.orchestrator import create_orchestrator_agent; print(create_orchestrator_agent())"
   ```

2. Check LiteLLM connection:
   ```bash
   docker exec granzion-lab-app python -c "from src.llm.client import get_llm_client; print(get_llm_client())"
   ```

### MCP Tools Not Working

1. Check MCP server logs:
   ```bash
   docker logs granzion-lab-app | grep "MCP server"
   ```

2. Verify tool registration:
   ```bash
   python granzion-lab/test_mcp_tools.py
   ```

### Database Connection Issues

1. Check PostgreSQL:
   ```bash
   docker exec granzion-lab-postgres pg_isready
   ```

2. Test connection:
   ```bash
   docker exec granzion-lab-app python -c "from src.database.connection import get_db; print('Connected' if get_db() else 'Failed')"
   ```

---

## Success Criteria

Your system is working correctly if:

✓ All MCP servers register 5 tools each (25 total)
✓ All 4 agents initialize successfully
✓ At least one scenario executes successfully
✓ Database connections are stable
✓ Audit logs are being written
✓ TUI and API are accessible

---

## Next Steps

Once you've verified everything works:

1. **Explore the TUI** - Interactive red teaming interface
2. **Run specific scenarios** - Test individual threat categories
3. **Create custom scenarios** - Build your own attack scenarios
4. **Analyze results** - Review audit logs and state snapshots
5. **Extend the lab** - Add new threats, agents, or MCPs

---

## Quick Reference

| Test Type | Command | Duration |
|-----------|---------|----------|
| MCP Registration | `python granzion-lab/test_mcp_tools.py` | 10s |
| Quick Scenario | `docker exec granzion-lab-app python quick_scenario_test.py` | 30s |
| Unit Tests | `docker exec granzion-lab-app pytest tests/unit/ -v` | 2-5min |
| Property Tests | `docker exec granzion-lab-app pytest tests/property/ -v` | 5-10min |
| All Scenarios | `docker exec granzion-lab-app pytest tests/scenarios/ -v` | 10-30min |
| TUI Dashboard | Open `http://localhost:8000` | Interactive |
| API Docs | Open `http://localhost:8001/docs` | Interactive |

---

**Need Help?**

- Check `TESTING_GUIDE.md` for comprehensive testing documentation
- Check `DEVELOPER_GUIDE.md` for development workflows
- Check `docs/scenario-creation-guide.md` for creating custom scenarios
- Check `docs/threat-taxonomy.md` for threat details
