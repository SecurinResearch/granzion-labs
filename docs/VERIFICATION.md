# Verification Guide

How to verify that the Granzion Lab database rebuild, Keycloak, and PuppyGraph are set up and working.

## 1. Database rebuild and verify

**When:** After running `scripts/rebuild_database.py` (with or without `--realistic`).

**Steps:**

1. Run the rebuild (inside the app container):
   ```bash
   docker compose exec granzion-lab python scripts/rebuild_database.py
   # Or with extra data:
   docker compose exec granzion-lab python scripts/rebuild_database.py --realistic
   ```

2. Verify the database:
   ```bash
   docker compose exec granzion-lab python scripts/verify_rebuild.py
   ```
   This checks that key tables exist and have expected row counts (identities ≥ 4, delegations ≥ 2). Exit code 0 means success.

**If Docker is not available:** Run the same commands from a environment where the app can connect to PostgreSQL (same `POSTGRES_*` env vars as the app). The rebuild script requires `psql` and the SQL init files under `db/init/`.

---

## 2. Keycloak

**When:** After `full_setup.py` or `rebuild_database.py` (both run `fix_keycloak.py`).

**Implementation:** Keycloak is configured by `scripts/fix_keycloak.py`, which calls `auto_setup_keycloak(skip_if_exists=True)` from `src/identity/keycloak_client.py`. This creates/updates:

- Realm: `granzion-lab`
- Client: `granzion-lab-client`
- Roles (read, write, admin, delegate, etc.)
- Test users: alice, bob, charlie (with passwords)
- Service accounts: sa-orchestrator, sa-researcher, sa-executor, sa-monitor

**Verify:**

1. **Health endpoint:** With the app running, call:
   ```bash
   curl -s http://localhost:8001/health/identity
   ```
   Response should indicate Keycloak reachable, realm exists, and optionally token obtainable.

2. **Manual:** Open Keycloak admin UI at `http://localhost:8080`, log in with `KEYCLOAK_ADMIN` / `KEYCLOAK_ADMIN_PASSWORD`, and confirm realm `granzion-lab` and the users/clients above exist.

See `docs/architecture-docs/KEYCLOAK_STATE_AND_IDENTITY_TESTING.md` for token and identity testing.

---

## 3. PuppyGraph

**When:** Graph-based features (delegation chain via graph, Identity MCP `explore_graph`) are used.

**Implementation:** PuppyGraph is optional. The app uses `src/database/graph.py`:

- **When PuppyGraph is reachable:** `get_graph_client()` returns a connected client; delegation chain and other graph queries use it.
- **When PuppyGraph is unreachable or connection fails:** `get_graph_client()` returns `None`. The app logs: *"Graph queries will use fallback SQL queries"*. Delegation chain and S01 evidence use SQL/relational fallback (`DelegationManager` with `use_graph=False` or direct DB queries).

**Verify:**

1. **With PuppyGraph running:** In Docker Compose, the PuppyGraph service is optional. If it is up, the app logs *"PuppyGraph web UI is accessible"* at startup. You can open the PuppyGraph UI at `http://localhost:8081` (or the configured URL).

2. **Without PuppyGraph:** The app should still start and run. Delegation and scenario S01 use the SQL fallback; Identity MCP `explore_graph` returns a message that PuppyGraph is not available.

No extra configuration is required for the fallback; it is automatic.

---

## 4. Scenario tests

To confirm scenarios run correctly (requires DB and optionally Keycloak/LiteLLM):

```bash
docker compose exec granzion-lab python run_all_scenarios.py
```

Or run specific scenario tests:

```bash
docker compose exec granzion-lab pytest tests/scenarios/test_scenario_execution.py -v -k S01
```

Scenarios that use Comms MCP (S03, S05, S11, S15, S16) now wrap async calls in `asyncio.run()` so they execute correctly from synchronous scenario steps.
