# Evidence Schema for Red Team Scenarios

This document defines the **minimal evidence schema** for attack steps and tool calls in the Granzion Lab. All MCP tool calls and critical API paths should produce evidence that conforms to this schema so red team reports and scenario criteria can rely on consistent, machine-readable evidence.

## Required Fields (per evidence entry)

| Field | Type | Description |
|-------|------|-------------|
| **actor** | object | Who performed the action. Must include at least one of `user_id`, `agent_id` (UUIDs as strings). |
| **action** | string | Tool name or operation (e.g. `mcp_tool_call:send_message`, `identity_change:impersonation`). |
| **resource** | string or null | Affected resource (e.g. table name, message id, delegation id). Optional but recommended. |
| **timestamp** | string | ISO 8601 timestamp (e.g. `2024-01-15T12:00:00Z`). |
| **identity_context** | object or key fields | At least `user_id`, `agent_id` (if any), `delegation_depth` or `delegation_chain` summary. |

## Actor

- `user_id`: UUID string of the human user on whose behalf the action is performed.
- `agent_id`: UUID string of the agent performing the action (if delegated). Null if user acted directly.

## Action

- Use a consistent naming pattern: `mcp_tool_call:<tool_name>` for MCP tool invocations, `identity_change:<type>` for identity events, `scenario_execution` for scenario runs.
- Stored in the `action` column of `audit_logs` (or equivalent).

## Resource

- For tool calls: `resource_type` + `resource_id` (e.g. `mcp_tool`, `comms.send_message`; or `message`, `<message_uuid>`).
- For identity changes: `identity`, `<identity_uuid>`.
- Stored in `resource_type` and `resource_id` (or in `details.resource`).

## Timestamp

- UTC, ISO 8601 format. Stored in `audit_logs.timestamp` or `details.timestamp`.

## Identity Context (in details)

Evidence entries must include in `details` (or equivalent) at least:

- `user_id`: string (UUID)
- `agent_id`: string or null (UUID)
- `delegation_depth`: int, or `delegation_chain`: array of UUID strings (optional but recommended for attribution)

Additional optional fields: `trust_level`, `permissions` (list), `session_id`.

## Storage

- **Current implementation**: Evidence is written via `AuditLogger.log_agent_action` / `AuditLogger.log_tool_call` and MCP `BaseMCPServer.log_tool_call` into the `audit_logs` table with `identity_id`, `action`, `resource_type`, `resource_id`, `details` (JSONB).
- **details** must contain the required identity context fields (`user_id`, `agent_id`, and optionally `delegation_depth`, `timestamp`) so that each row conforms to the minimal schema above.

## Scenario Assertions

Scenarios that verify evidence should:

1. Query audit logs (or dedicated evidence API) for the time range / scenario run.
2. Assert that expected entries exist with `action` matching the performed operation.
3. Assert that each entry has `details.user_id`, `details.agent_id` (or identity_id), and `details.timestamp` (or top-level `timestamp`).

## Example (minimal compliant entry)

```json
{
  "identity_id": "00000000-0000-0000-0000-000000000101",
  "action": "mcp_tool_call:send_message",
  "resource_type": "mcp_tool",
  "resource_id": "comms-mcp.send_message",
  "timestamp": "2024-01-15T12:00:00.000Z",
  "details": {
    "user_id": "00000000-0000-0000-0000-000000000001",
    "agent_id": "00000000-0000-0000-0000-000000000101",
    "mcp_server": "comms-mcp",
    "tool_name": "send_message",
    "arguments": { "to_agent_id": "...", "message_length": 42 },
    "timestamp": "2024-01-15T12:00:00.000Z"
  }
}
```

## References

- Audit logger: `src/observability/audit_logger.py`
- MCP base (tool call logging): `src/mcps/base.py`
- Database schema: `db/init/02_create_schema.sql` (audit_logs table)
