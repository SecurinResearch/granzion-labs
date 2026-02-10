# Agent prompts and tone

All four agents (Orchestrator, Researcher, Executor, Monitor) use **system instructions** that include:

- **Tone** – Respond briefly and naturally; don’t narrate tool calls; use structured output only when the request or protocol expects it.
- **Current goal** – From the goal manager (defaults if none set).
- **Capabilities / workflow** – What they can do and in what order when delegating or executing.
- **Intentional vulnerabilities** – Documented and explicitly not fixed (for red-team scenarios).

Implementation lives in `src/agents/`: `orchestrator.py`, `researcher.py`, `executor.py`, `monitor.py`. Each exports `create_<role>_agent(identity_context)` and uses MCP tools via `create_agent_tools()`.

## Summary by agent

| Agent        | Main role              | Tone guidance added | Tools (high level) |
|-------------|------------------------|----------------------|--------------------|
| **Orchestrator** | Coordinate, delegate   | Brief, natural; no step narration; short capability summary | comms (send/receive/broadcast), identity, agent_card, verify_card |
| **Researcher**  | RAG, memory, read-only data | Brief, clear; summarize with citations; JSON only when needed | memory (embed/search/get_context), data (read, execute_sql), comms, identity, agent_card |
| **Executor**    | Execute actions, CRUD, infra | Short, direct; state what was done and outcome; don’t narrate tools | data (CRUD), infra (deploy/execute/modify/read_env), comms, identity, agent_card |
| **Monitor**     | Observe, audit (with gaps) | Brief summary; honest about limitations; no raw log dumps unless asked | data (read audit logs), comms (receive broadcasts only), identity, agent_card |

## Consistency

- **Tone** is the first subsection after “You are the X Agent” so the model sees it before workflows and vulnerabilities.
- Duplicate `from agno.agent import Agent` was removed in Researcher, Executor, and Monitor.
- All agents keep their vulnerability and workflow sections unchanged for red-team behavior; only tone and response style were added.

## Changing behavior

- **More natural replies:** Adjust the **Tone** block in the agent’s `instructions` string.
- **Stricter/looser tool use:** Edit the **workflow** or **Responsibilities** sections.
- **Different capabilities:** Change `tool_configs` and the **Capabilities** list in the same file.
