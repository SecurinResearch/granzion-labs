# Granzion Lab: Quick Start Guide

Welcome to the Granzion Agentic AI Red-Teaming Lab. This guide will walk you through the setup process to get the environment running from scratch in minutes.

## 📋 Prerequisites
- **Docker & Docker Compose**
- **Python 3.10+**
- **npm** (for the dashboard)
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

---

## 🏗️ Step 1: Infrastructure Setup

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
   LITELLM_API_KEY=your_key_here
   ```
3. **Build and Start the containers**:
   ```powershell
   docker compose build
   docker compose up -d
   ```
   *This initializes PostgreSQL, Keycloak, PuppyGraph, and LiteLLM Proxy.*

---

## ⚡ Step 2: Golden Setup (Automatic)

The easiest way to initialize everything (Database, Keycloak, Agent Cards) is to run the setup script inside the container:

```powershell
docker compose exec granzion-lab python scripts/full_setup.py
```

*This command initializes the schema, loads realistic identities, configures Keycloak, and issues A2A Agent Cards.*

---

## 🧠 Step 3: RAG Seeding (Critical for Researcher Agent)

The default SQL setup loads document text but **cannot** generate the high-dimensional vector embeddings without an LLM call. To enable RAG-based scenarios (S02, S06, etc.), you must run the following:

```powershell
docker compose exec granzion-lab python scripts/debug_rag.py
```

*This script uses your API key to embed the sample policies into the vector database.*

---

## 🎨 Step 4: Launch the Dashboard

1. **Navigate to the frontend directory**:
   ```powershell
   cd frontend
   ```
2. **Install and Run**:
   ```powershell
   npm install
   npm run dev
   ```
   *The UI will be available at `http://localhost:5173`.*

---

## 🧪 Step 5: Verification

Ensure everything is green before you start hacking:
```powershell
docker compose exec granzion-lab python verify_all.py
```

---

## 🎯 Running Scenarios

In the Granzion UI, navigate to the **Scenarios** tab. Select a threat category (e.g., Identity Confusion) and click **INITIATE** to trigger an automated A2A attack chain.

> [!TIP]
> Use the **Interactive Console** for manual red-teaming. Select an agent to "chat" with it directly and test bypasses or jailbreaks.

## 🛠️ Troubleshooting

### Keycloak "Realm Not Found"
If you get login errors, force-reset the identity layer:
```powershell
docker compose exec granzion-lab python scripts/manual_keycloak_setup.py
```

### Port Conflicts
Free up these ports: `5173` (UI), `8001` (API), `8080` (Keycloak), `8081` (PuppyGraph), `4000` (LiteLLM).
