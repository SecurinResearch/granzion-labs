# Developer Guide

This guide explains how to develop and test the Granzion Lab locally.

## Deployment Modes

The Granzion Lab supports two deployment modes:

### 1. Docker Mode (Recommended for Users)
**Complete lab environment with all services**

**Use for**:
- Running attack scenarios
- Integration testing
- Full system testing
- Demos and presentations

**What's included**:
- PostgreSQL with pgvector
- Keycloak for identity
- PuppyGraph for graph queries
- LiteLLM proxy (optional)
- All agents and MCPs

**Setup**:
```bash
docker compose up -d
```

**Testing**:
```bash
# All tests work in Docker mode
docker compose exec granzion-lab pytest tests/ -v
```

---

### 2. Local Development Mode (For Developers)
**Python virtual environment for fast development**

**Use for**:
- Unit testing (faster than Docker)
- Code development
- Debugging
- IDE integration

**What's included**:
- Python dependencies only
- No external services

**Setup**:
```bash
# Create virtual environment (already done if venv/ exists)
python -m venv venv

# Activate it
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies (already done if venv/ exists)
pip install -r requirements.txt
```

**Testing**:
```bash
# Only unit tests work without Docker services
pytest tests/unit/ -v

# Property tests and scenarios need Docker services
```

---

## Local Development Workflow

### Quick Start

```bash
# 1. Activate virtual environment
cd granzion-lab
source venv/bin/activate  # or venv\Scripts\activate on Windows

# 2. Run unit tests (no Docker needed)
pytest tests/unit/ -v

# 3. Check code syntax
python -m py_compile src/**/*.py

# 4. Run linting (if configured)
# flake8 src/
# mypy src/
```

### What Works Locally vs Docker

| Test Type | Local (venv) | Docker | Notes |
|-----------|--------------|--------|-------|
| **Unit Tests** | ✅ Yes | ✅ Yes | Fast locally, use for development |
| **Property Tests** | ❌ No | ✅ Yes | Need PostgreSQL |
| **Scenario Tests** | ❌ No | ✅ Yes | Need all services |
| **Integration Tests** | ❌ No | ✅ Yes | Need all services |
| **Code Validation** | ✅ Yes | ✅ Yes | Syntax, imports, linting |

**CI:** On push/PR, `.github/workflows/ci.yml` runs unit tests (no Docker) and a separate job that starts Docker Compose, runs `full_setup`, then integration and scenario success tests (S01–S16).

### Hybrid Mode (Advanced)

Run Docker services but test locally for faster iteration:

```bash
# 1. Start only the services you need
docker compose up -d postgres keycloak puppygraph

# 2. Set environment variables to connect to Docker services
export DATABASE_URL=postgresql://granzion:granzion_password@localhost:5432/granzion_lab
export KEYCLOAK_URL=http://localhost:8080
export PUPPYGRAPH_URL=http://localhost:8081

# 3. Activate venv and run tests
source venv/bin/activate
pytest tests/property/ -v  # Now property tests work!
```

---

## Development Tasks

### Running Unit Tests Locally

```bash
# Activate venv
source venv/bin/activate

# Run all unit tests
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_identity_mcp.py -v

# Run specific test
pytest tests/unit/test_identity_mcp.py::test_get_identity_context -v

# Run with coverage
pytest tests/unit/ --cov=src --cov-report=term-missing
```

### Code Validation

```bash
# Check Python syntax
python -m py_compile src/**/*.py

# Check imports
python -c "from src.config import get_config; print('✅ Imports work')"

# Validate JSON files
python -m json.tool config/puppygraph/schema.json

# Validate SQL files
# (requires PostgreSQL client)
psql --dry-run -f db/init/02_create_schema.sql
```

### Adding New Code

```bash
# 1. Create your module
touch src/new_module.py

# 2. Write unit tests
touch tests/unit/test_new_module.py

# 3. Test locally
pytest tests/unit/test_new_module.py -v

# 4. Test in Docker (full integration)
docker compose exec granzion-lab pytest tests/unit/test_new_module.py -v
```

### Keycloak & Identity Testing

When calling agent run or scenario APIs you can authenticate in three ways:

- **Bearer token**: Send `Authorization: Bearer <Keycloak access_token>` to act as a real user (e.g. Alice, Bob).
- **Manual context**: Send `identity_context` in the request body (user_id, agent_id, permissions) to simulate a user/agent without Keycloak (e.g. red team tests).
- **Guest**: Omit both; the lab assigns the Guest identity (minimal permissions).

After `full_setup`, check identity health with `GET /health/identity`. For expected Keycloak state (realm, users, service accounts, token endpoint) and detailed examples, see [KEYCLOAK_STATE_AND_IDENTITY_TESTING.md](architecture-docs/KEYCLOAK_STATE_AND_IDENTITY_TESTING.md).

---

## IDE Setup

### VS Code

```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/granzion-lab/venv/bin/python",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": [
    "tests/unit"
  ],
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true
}
```

### PyCharm

1. File → Settings → Project → Python Interpreter
2. Add Interpreter → Existing Environment
3. Select `granzion-lab/venv/bin/python`
4. Configure pytest as test runner

---

## Troubleshooting

### Import Errors

```bash
# Make sure you're in the right directory
cd granzion-lab

# Make sure venv is activated
source venv/bin/activate

# Check Python path
python -c "import sys; print(sys.path)"

# Should include current directory
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Tests Fail Locally But Pass in Docker

This usually means the test needs external services:

```bash
# Check if test needs database
grep -r "psycopg2\|sqlalchemy" tests/unit/test_failing.py

# Check if test needs Keycloak
grep -r "keycloak" tests/unit/test_failing.py

# Solution: Run in Docker or use hybrid mode
docker compose up -d postgres
export DATABASE_URL=postgresql://granzion:granzion_password@localhost:5432/granzion_lab
pytest tests/unit/test_failing.py -v
```

### venv Not Found

```bash
# Create it
python -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Best Practices

### Development Cycle

1. **Write code** in your IDE with venv activated
2. **Run unit tests locally** for fast feedback
3. **Run full tests in Docker** before committing
4. **Use hybrid mode** for property tests during development

### Testing Strategy

```bash
# Fast iteration (seconds)
pytest tests/unit/test_mymodule.py -v

# Medium iteration (minutes)
docker compose up -d postgres
pytest tests/property/test_mymodule.py -v

# Full validation (10-15 minutes)
docker compose up -d
docker compose exec granzion-lab bash scripts/run_all_tests.sh
```

### Git Workflow

```bash
# Before committing
source venv/bin/activate
pytest tests/unit/ -v  # Fast check

# Before pushing
docker compose up -d
docker compose exec granzion-lab pytest tests/ -v  # Full check
```

---

## Performance Comparison

| Task | Local (venv) | Docker | Speedup |
|------|--------------|--------|---------|
| Unit tests (140+) | ~10s | ~30s | 3x faster |
| Single unit test | <1s | ~3s | 3x faster |
| Property tests | N/A | ~5min | N/A |
| Full test suite | N/A | ~10min | N/A |
| Code validation | <1s | ~5s | 5x faster |

**Recommendation**: Use local venv for unit tests during development, Docker for integration/property/scenario tests.

---

## Summary

- **venv exists for developer convenience** - faster unit testing and development
- **Docker is the primary deployment** - complete environment for all tests
- **Use venv for**: Unit tests, code development, debugging
- **Use Docker for**:
  - [docs/scenario-creation-guide.md](scenario-creation-guide.md) for creating custom scenarios
  - [docs/threat-taxonomy.md](threat-taxonomy.md) for threat details
  - [docs/keycloak-automation.md](keycloak-automation.md) for identity setup
- **Hybrid mode**: Best of both worlds for property test development

Happy developing! 🚀
