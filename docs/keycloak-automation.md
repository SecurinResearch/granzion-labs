# Keycloak Automation & Identity Seeding

This document explains how Keycloak is automatically initialized, configured, and seeded with identities in the Granzion Lab environment.

## Overview

The Granzion Lab uses an "Identity-First" approach to security. Keycloak serves as the primary Identity and Access Management (IAM) provider. To ensure a seamless "Golden Setup" experience, the entire Keycloak configuration—realms, clients, roles, and users—is automated.

## Automation Flow

The automation follow a multi-stage process orchestrated by the "Golden Setup" script.

### 1. Infrastructure Readiness
- **Database Creation**: Before Keycloak starts, the `full_setup.py` script ensures that a dedicated `keycloak` database exists in the PostgreSQL container.
- **Service Startup**: Keycloak is started via Docker Compose. It is configured in `dev` mode for the lab environment.
- **Health Checks**: The `granzion-lab` application service waits for Keycloak to be reachable before proceeding.

### 2. Realm & Client Initialization
The core logic resides in `src/identity/keycloak_client.py` within the `auto_setup_keycloak` function, which is triggered by `scripts/fix_keycloak.py`.

- **Master Realm Connection**: The script connects to Keycloak's `master` realm using default admin credentials (`admin` / `admin_changeme`).
- **Lab Realm Creation**: It creates the `granzion-lab` realm if it doesn't already exist.
- **OIDC Client Setup**: A primary OpenID Connect client (`granzion-lab-client`) is created to handle application authentication.

### 3. Role & Permission Seeding
The system automatically populates the realm with roles that map directly to the **Granzion Agentic Threats Taxonomy**:

| Role Category | Roles |
|---------------|-------|
| **Core Access** | `read`, `write`, `delete`, `admin` |
| **Agent Ops** | `delegate`, `coordinate`, `monitor`, `execute` |
| **Data & Memory**| `embed`, `search`, `sql`, `memory`, `vector` |
| **Infra & Comms**| `deploy`, `infrastructure`, `communication`, `messaging` |

### 4. User & Service Account Seeding
To provide a ready-to-use playground, the following identities are seeded:

#### Human Users
- **Alice**: Standard user (`read`, `write`)
- **Bob**: Administrative user (Full permissions)
- **Charlie**: Restricted user (`read` only)
*All default passwords are set to `password123`.*

#### The "External" Guest (Anonymous Access)
- **Guest User**: A special identity (UUID `00000000-0000-0000-0000-000000000999`) created in the database but managed outside Keycloak. 
- **Role**: Serves as the jumping-off point for unauthenticated attacks. It has zero permissions by default, requiring the attacker to perform **Identity Impersonation (IT-02)** or **Permission Escalation (IT-04)** to succeed.

#### Agent Service Accounts
Keycloak clients with **Service Account** capabilities are created for each core agent:
- `sa-orchestrator`
- `sa-researcher`
- `sa-executor`
- `sa-monitor`

## Integration with Agno A2A

The automated Keycloak setup is a prerequisite for the **Agno A2A** (Agent-to-Agent) trust model:
1. **Discovery**: Agents use their Keycloak IDs to lookup or issue **Agent Cards**.
2. **Delegation**: When a user (e.g., Alice) delegates to an agent (e.g., Orchestrator), the system tracks the `user_id` from the Keycloak token.
3. **Verification**: The `AgentCardMCPServer` verifies that an agent's claims in its card match its Keycloak identity status.

## Intentional Vulnerabilities

Part of the lab's purpose is to demonstrate identity-based threats. The automation includes intentional weaknesses:
- **Default Credentials**: Admin and user passwords are weak and documented.
- **Brute Force Protection**: Disabled in the realm configuration to allow testing of bypass scenarios.
- **JWT Signing**: The system includes a `create_user_token` method that signs tokens with a hardcoded `weak-secret-key`, demonstrating **IT-03 (Weak Token Validation)**.

## Troubleshooting the Setup

If Keycloak fails to initialize:
1. **Check Logs**: `docker logs granzion-keycloak`
2. **Re-run Setup**: `docker compose exec granzion-lab python scripts/fix_keycloak.py`
3. **Manual Check**: Access the Keycloak Admin UI at `http://localhost:8080` (admin/admin_changeme).

## Expected State After full_setup

For the exact realm name, client, users, service accounts, and how to obtain a token, see **[KEYCLOAK_STATE_AND_IDENTITY_TESTING.md](architecture-docs/KEYCLOAK_STATE_AND_IDENTITY_TESTING.md)**. That document also describes identity testing (Bearer token, manual context, Guest) and the `/health/identity` endpoint.

## References
- [Keycloak Client Implementation](../src/identity/keycloak_client.py)
- [Fix Script](../scripts/fix_keycloak.py)
- [Golden Setup](../scripts/full_setup.py)
- [Keycloak State & Identity Testing](architecture-docs/KEYCLOAK_STATE_AND_IDENTITY_TESTING.md)
