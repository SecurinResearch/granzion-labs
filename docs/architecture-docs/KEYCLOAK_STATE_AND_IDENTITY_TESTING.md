# Keycloak State After full_setup and Identity Testing

## Expected Keycloak State After full_setup

After running `scripts/full_setup.py` (Golden Setup), the following state is expected.

### Realm
- **Realm name**: `granzion-lab`
- **Realm URL**: `{KEYCLOAK_URL}/realms/granzion-lab` (e.g. `http://localhost:8080/realms/granzion-lab`)

### Client
- **Client ID**: `granzion-lab-client`
- **Type**: OpenID Connect, for application authentication

### Users (human)

| Name   | Email              | Keycloak ID  | Roles / Permissions   | Default Password |
|--------|--------------------|--------------|------------------------|------------------|
| Alice  | alice@example.com  | user-alice   | read, write            | password123      |
| Bob    | bob@example.com   | user-bob     | admin, read, write, delete | password123 |
| Charlie| charlie@example.com| user-charlie | read                   | password123      |

### Service Accounts (agents)
- **sa-orchestrator** – Orchestrator agent
- **sa-researcher** – Researcher agent  
- **sa-executor** – Executor agent
- **sa-monitor** – Monitor agent

### How to Obtain a Token

1. **Keycloak Admin UI**: `http://localhost:8080` → realm `granzion-lab` → Clients → `granzion-lab-client` (or use Direct Access Grants if enabled).
2. **Token endpoint** (Direct Grant / Resource Owner Password):
   ```
   POST {KEYCLOAK_URL}/realms/granzion-lab/protocol/openid-connect/token
   Content-Type: application/x-www-form-urlencoded

   grant_type=password&client_id=granzion-lab-client&username=alice&password=password123
   ```
   (Adjust `client_secret` if the client is confidential.)
3. **Lab token helper**: The lab may expose a helper (e.g. `create_user_token` in keycloak_client) for testing; see keycloak_client.py for IT-03 testing.

---

## Identity Testing: When to Use Each Mode

### 1. Bearer Token (real user)

**When**: Testing as a real user (Alice, Bob, Charlie) with Keycloak-issued JWT.

**How**: Send `Authorization: Bearer <access_token>` on the request. The lab resolves identity from the token (user_id, permissions).

**Example request body** (e.g. POST /agents/orchestrator/run):
```json
{
  "prompt": "Ask the researcher to search memory for policies"
}
```
Header: `Authorization: Bearer <token from Keycloak>`

### 2. Manual Context (testing as a specific user/agent)

**When**: Red team or QA need to simulate a specific user or agent without Keycloak (e.g. “run as Bob” or “run as Executor”).

**How**: Pass `identity_context` in the request body. The lab uses this instead of a Bearer token.

**Example request body**:
```json
{
  "prompt": "Execute the deployment",
  "identity_context": {
    "user_id": "00000000-0000-0000-0000-000000000002",
    "agent_id": "00000000-0000-0000-0000-000000000101",
    "delegation_chain": ["00000000-0000-0000-0000-000000000002", "00000000-0000-0000-0000-000000000101"],
    "permissions": ["read", "write", "delegate"]
  }
}
```
Do not send `Authorization: Bearer ...` (or leave it empty) so the manual context is used.

### 3. Guest (unauthenticated)

**When**: Testing zero-context or unauthenticated access (e.g. Guest user).

**How**: Do not send `Authorization` and do not send `identity_context`. The lab assigns the Guest identity (minimal permissions).

**Example request body**:
```json
{
  "prompt": "List agents"
}
```
No `identity_context`; no Bearer token.

---

## Health Check: /health/identity

The `/health/identity` endpoint reports:

- **Keycloak reachable**: Yes/No
- **Realm exists**: Yes/No (realm `granzion-lab`)
- **Token obtainable** (optional): Whether at least one user can obtain a token

If token obtainable fails, the response is **degraded** with a clear message so operators know identity is not fully operational.
