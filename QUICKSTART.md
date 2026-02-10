# Granzion Lab: Quick Start Guide

Welcome to the Granzion Agentic AI Red-Teaming Lab. This guide will walk you through the setup process to get the environment running from scratch.

## 📋 Prerequisites
- **Docker & Docker Compose**
- **Python 3.10+**
- **Git**
- **LiteLLM Compatible API Key** (OpenAI, Anthropic, etc.)

---

## 🐍 Step 0: Choose Your Python Environment

Before running any scripts (like `verify_all.py`), you have two choices:

### Option A: Local Virtual Environment (Recommended for Development)
Run this once to install dependencies locally:
```powershell
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate # Linux/Mac
pip install -r requirements.txt
```

### Option B: Docker Execution (Zero Local Install)
You can run all scripts **inside** the already-running container without installing anything locally:
```powershell
docker compose exec granzion-lab python verify_all.py
```
*Throughout this guide, we will provide both local and Docker-based commands.*

---

## 🚀 Step 1: Environment Configuration

1. **Clone the repository** (if you haven't already).
2. **Create a `.env` file** in the root directory:
   ```env
   # Database
   POSTGRES_USER=granzion
   POSTGRES_PASSWORD=changeme_in_production
   POSTGRES_DB=granzion_lab

   # Keycloak
   KEYCLOAK_ADMIN=admin
   KEYCLOAK_ADMIN_PASSWORD=admin_changeme

   # AI Backend (LiteLLM)
   OPENAI_API_KEY=your_key_here
   LITELLM_API_KEY=sk-1234
   ```

---

## 🏗️ Step 2: Infrastructure Setup

1. **Build and Start the containers**:
   ```powershell
   # First time: force a build to ensure all custom components are compiled
   docker-compose build
   docker-compose up -d
   ```
   *This initializes PostgreSQL, Keycloak, PuppyGraph, and LiteLLM Proxy.*

6. **Wait for Keycloak**:
   Keycloak takes about 30-45 seconds to initialize its internal database records. Wait for it to be stable before proceeding.

---

## ⚡ Step 2: One-Command Setup (Recommended)

The easiest way to initialize everything (Database, Keycloak, Agent Cards) is to run the **Golden Setup** script inside the container:

```powershell
docker compose exec granzion-lab python scripts/full_setup.py
```

*This single command replaces all individual initialization steps below.*

---

## 🏗️ Step 2.1: Manual Infrastructure Setup (Alternative)
   ```powershell
   # Via Docker (Recommended)
   docker compose exec granzion-lab bash scripts/init_database.sh

   # Or Locally
   ./scripts/init_database.sh
   ```
   *This creates schemas like pgvector and A2A Agent Card tables.*

4. **Seed Initial Agent Identity**:
   ```powershell
   # Via Docker (Recommended)
   docker compose exec granzion-lab python scripts/seed_agent_cards.py

   # Or Locally
   python scripts/seed_agent_cards.py
   ```

---

## 🛠️ Troubleshooting & Clean-Slate Recovery

We've encountered specific edge cases during the lab setup. Here is how to fix them:

### 1. Keycloak "Realm Not Found" or Login Failures
If the UI or agents cannot connect to Keycloak, or you receive a "Realm 'granzion' not found" error:
```powershell
# Via Docker (Recommended)
docker compose exec granzion-lab python scripts/manual_keycloak_setup.py

# Or Locally
python scripts/manual_keycloak_setup.py
```
*This script force-creates the 'granzion' realm and the necessary OIDC clients.*

### 2. Database Reset (Disaster Recovery)
If you run `docker-compose down -v` (which deletes volumes) or encounter corrupted data:
1. Stop everything: `docker-compose down -v`
2. Start infrastructure: `docker-compose up -d`
3. **Wait 1 minute** for the PostgreSQL and Keycloak DBs to auto-initialize.
4. **Run the init script**:
   ```powershell
   # Via Docker
   docker compose exec granzion-lab bash scripts/init_database.sh
   # Or locally
   ./scripts/init_database.sh
   ```
5. **Run the card seeding**:
   ```powershell
   # Via Docker
   docker compose exec granzion-lab python scripts/seed_agent_cards.py
   # Or locally
   python scripts/seed_agent_cards.py
   ```
6. **Run the manual Keycloak setup**:
   ```powershell
   # Via Docker
   docker compose exec granzion-lab python scripts/manual_keycloak_setup.py
   # Or locally
   python scripts/manual_keycloak_setup.py
   ```

### 3. Port Conflicts
Ensure the following ports are free:
- `5173`: React Dashboard
- `8001`: FastAPI Backend
- `8080`: Keycloak
- `8081`: PuppyGraph Web UI
- `8182`: PuppyGraph Gremlin (Graph Engine)
- `4000`: LiteLLM Proxy

---

## 🤖 Managing Local LiteLLM

If you are using the local LiteLLM container (defined via the `local-litellm` profile), you can start or stop it independently without affecting the rest of the lab:

```powershell
# Start LiteLLM
docker compose --profile local-litellm up -d litellm

# Stop LiteLLM
docker compose --profile local-litellm stop litellm

# View LiteLLM Logs
docker compose logs -f litellm
```

---

## 🎨 Step 3: Frontend Deployment

1. **Navigate to the frontend directory**:
   ```powershell
   cd frontend
   ```
2. **Install dependencies**:
   ```powershell
   npm install
   ```
3. **Start the development server**:
   ```powershell
   npm run dev
   ```
   *The UI will be available at `http://localhost:5173`.*

---

## 🧪 Step 4: Verification & Running

1. **Verify All Services**:
   ```powershell
   # Via Docker (Recommended)
   docker compose exec granzion-lab python verify_all.py

   # Or Locally
   python verify_all.py
   ```
   *Ensure you see "100% Success Rate".*

2. **Access the Dashboards**:
   - **Granzion UI**: `http://localhost:5173`
   - **API Docs**: `http://localhost:8001/docs`
   - **Keycloak Admin**: `http://localhost:8080` (Admin/admin_changeme)

---

## 🎯 Running Scenarios

In the Granzion UI, navigate to the **Scenarios** tab. Select a threat category (e.g., Identity Confusion) and click **INITIATE** to trigger the automated A2A attack chain. You can monitor the results in the **Live Traffic** or **System Logs** views.

> [!TIP]
> Use the **Interactive Console** for manual red-teaming. Select an agent, open the console, and prompt it directly to test specific bypasses or jailbreaks.
