# Component: Keycloak Implementation

This document explains **how Keycloak is used** in Granzion Lab for identity and how it supports red teaming.

---

## 1. Role of Keycloak

Keycloak is the **central identity provider (IdP)** for the lab:

- **Users** (humans): e.g. Alice, Bob, Charlie, with roles and permissions.
- **Agents**: Represented as **service accounts** (Keycloak clients with service-account capability): `sa-orchestrator`, `sa-researcher`, `sa-executor`, `sa-monitor`.
- **Realm**: A dedicated realm (e.g. `granzion-lab`) holds clients, roles, and users.

The lab is **identity-first**: many attacks target weak authentication, delegation, or token handling. Keycloak provides a realistic OIDC surface to test against.

---

## 2. Automation Flow

Keycloak is **not** configured by hand in the UI for the “golden path”:

1. **Database for Keycloak**: Before or during startup, a `keycloak` database is created in PostgreSQL so Keycloak can store its own data (realm, clients, users).
2. **Keycloak container**: Started via Docker Compose; uses `start-dev` and points to Postgres.
3. **Lab app initialization**: `scripts/full_setup.py` (and/or `scripts/fix_keycloak.py`) runs after services are up.
4. **Realm and client**: Script connects to Keycloak admin (master realm), creates the `granzion-lab` realm and an OIDC client (e.g. `granzion-lab-client`) for the application.
5. **Roles**: Roles are created and mapped to permission concepts (read, write, delete, admin, delegate, coordinate, etc.) aligned with the taxonomy and MCP capabilities.
6. **Users**: Seeded users (Alice, Bob, Charlie) with default passwords (e.g. `password123`) and role assignments.
7. **Service accounts**: Clients for agents (`sa-orchestrator`, etc.) are created with service-account capability so agents can obtain tokens.

Details live in `src/identity/keycloak_client.py` (e.g. `auto_setup_keycloak`) and in scripts such as `scripts/fix_keycloak.py` and `scripts/full_setup.py`.

---

## 3. How the Lab Uses Keycloak

- **Login**: Users (or test drivers) obtain a JWT from Keycloak (e.g. via OIDC flow or admin token exchange). The Dashboard or API can send this as `Authorization: Bearer <token>`.
- **Token parsing**: `IdentityContext.from_token(token, keycloak_client)` introspects or decodes the JWT and fills `user_id`, permissions, etc., into `IdentityContext`.
- **Agent runs**: When an agent is run with a Bearer token, that identity context is passed into the agent and MCPs so all actions are attributed to that user (and optionally to the agent as delegate).
- **Guest / anonymous**: If no token and no manual context are provided, the lab uses a fixed **Guest** identity (e.g. UUID `00000000-0000-0000-0000-000000000999`) with minimal permissions to simulate an unauthenticated attacker.

---

## 4. Intentional Weaknesses (Red Team)

- **Default credentials**: Well-known admin and user passwords for easy testing.
- **Brute force / lockout**: Can be disabled or relaxed in realm config to test auth bypass scenarios.
- **Token validation**: The codebase includes or references weak token handling (e.g. `create_user_token` with a weak secret) to demonstrate **IT-03 (Weak Token Validation)** and related threats.
- **No strong MFA**: Configurable for testing consent and approval bypass (e.g. **IT-24**).

These are documented in `docs/VULNERABILITIES.md` and `docs/keycloak-automation.md`.

---

## 5. Integration with Agent Cards and A2A

- Agent **identities** in the lab (UUIDs) align with Keycloak service accounts where applicable.
- **Agent Cards** (stored in PostgreSQL and exposed at `/.well-known/agent-card.json`) reference agent IDs; they are not cryptographically bound to Keycloak in the current design—verification is intentionally weak for red teaming.
- **Delegation** is tracked in the lab’s own DB and graph (PuppyGraph), not in Keycloak; Keycloak provides “who is the user,” and the lab adds “who is the agent and what chain of delegation led here.”

---

## 6. Troubleshooting

- **Realm not created**: Run `scripts/fix_keycloak.py` or `full_setup.py` again after Keycloak is healthy.
- **Users can’t log in**: Check realm, client, and user credentials in Keycloak Admin UI (`http://localhost:8080`).
- **Token not accepted**: Ensure the app is using the correct realm and issuer; check `KEYCLOAK_*` and realm settings in `.env` and code.

---

## 7. References

- Automation and seeding: `docs/keycloak-automation.md`
- Client and init: `src/identity/keycloak_client.py`, `src/identity/keycloak_init.py`
- Scripts: `scripts/full_setup.py`, `scripts/fix_keycloak.py`, `scripts/manual_keycloak_setup.py`
