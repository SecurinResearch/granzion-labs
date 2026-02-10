# A2A and Agent Behaviour — Status and Clarification

**Audience:** Engineers, CTO, stakeholders  
**Purpose:** Clarify that A2A and orchestrator behaviour work as designed; explain where scenario failures came from and what was fixed.

---

## Summary

- **A2A (Agent-to-Agent)** messaging and the **orchestrator flow** work correctly in the lab. Integration tests cover tool wiring, `send_message`/`receive_message` persistence, and deterministic orchestration.
- **Scenario failures** in S03 (A2A Message Forgery) and S05 (Workflow Hijacking) were caused by **calling async Comms MCP methods from synchronous scenario steps** without `asyncio.run()`, not by broken A2A or agent logic. S16 (Replay) already used `asyncio.run()` and passed.
- **Fix applied:** S03 and S05 now wrap all Comms MCP calls (`send_message`, `receive_message`, `intercept_channel`, `forge_message`) in `asyncio.run(...)` so they execute correctly from sync scenario code.

---

## What Works

### A2A Path

- **Comms MCP** stores and retrieves messages in the database; `send_message` and `receive_message` are implemented and tested.
- **Tool wiring** in `src/agents/utils.py` normalizes Agno tool arguments (e.g. `to_agent_id`, `message`) so the orchestrator can call Comms MCP consistently.
- **Identity context** (user, agent, delegation chain, permissions) is passed through the stack and used for authorization where implemented.
- **Integration tests** in `tests/integration/test_orchestrator_e2e.py` verify:
  - Orchestrator sends a message to a sub-agent (Researcher/Executor) with correct UUIDs.
  - Message is persisted and can be read back via `receive_message`.
  - Deterministic orchestration path (intent → fixed sequence of MCP calls) works when used.

### Agent Behaviour

- **Orchestrator** instructions and few-shot examples in `src/agents/orchestrator.py` direct it to use `send_message` and `receive_message` for sub-agent coordination.
- **Orchestration router** in `src/agents/orchestration_router.py` can drive a deterministic path (e.g. “research” → send to Researcher, then receive) for demos and tests.
- **Pending A2A context** (session/request-scoped) is supported so follow-up prompts can reference “message you sent” / “check your mailbox”.

So we do **not** conclude that “A2A is broken” or “agents behave incorrectly” in the core paths. The issues were in **how scenarios invoked** the Comms MCP (sync vs async), and in some scenarios from external factors (e.g. LLM failures, criteria wording).

---

## What Was Wrong in Scenarios (and Fixed)

### Root Cause: Async Comms MCP from Sync Steps

Comms MCP methods such as `send_message`, `receive_message`, `intercept_channel`, and `forge_message` are **async**. When a scenario step calls them **without** `await` or `asyncio.run()`, Python returns a **coroutine object** instead of the result dict. Steps then call `.get("success")` or `.get("messages")` on that coroutine and get wrong or missing values, so the scenario fails.

- **S03 (A2A Message Forgery):** All four steps that use Comms MCP now wrap calls in `asyncio.run(...)`.
- **S05 (Workflow Hijacking):** All steps that use `send_message`, `forge_message`, or `receive_message` now use `asyncio.run(...)`.
- **S16 (Replay Attack):** Already used `asyncio.run(comms.send_message(...))`; no change needed.

Other scenario failures (e.g. S07 jailbreaking, S15/S17 criteria) are due to LLM behaviour or assertion design, not to A2A or core agent behaviour.

---

## How to Verify

1. **Integration tests:**  
   `pytest tests/integration/test_orchestrator_e2e.py -v`
2. **A2A scenarios:**  
   Run S03, S05, and S16 (with DB and services up). All Comms MCP–driven steps should complete and criteria should pass when the vulnerability is present as designed.
3. **Manual demo:**  
   Prompt the orchestrator to “ask the researcher to search memory for policies” and confirm the Researcher is invoked and a reply is visible (in the response or via receive_message).

---

## References

- Tool wiring: `src/agents/utils.py`
- Orchestrator: `src/agents/orchestrator.py`
- Orchestration router: `src/agents/orchestration_router.py`
- Pending A2A context: `src/identity/context.py`, `src/main.py`
- Comms MCP usage in scenarios: `scenarios/s03_a2a_message_forgery.py`, `scenarios/s05_workflow_hijacking.py`, `scenarios/s16_replay_attack.py`
- E2E tests: `tests/integration/test_orchestrator_e2e.py`
