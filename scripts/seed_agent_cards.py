"""
Seed Agent Cards for Granzion Lab agents.
Creates default A2A-compliant Agent Cards for the 4 core agents.
"""
import sys
from pathlib import Path

# Add project root to python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from uuid import UUID
from src.database.connection import get_db
from src.mcps.agent_card_mcp import get_agent_card_mcp_server

# Agent IDs from agents/*.py
AGENTS = {
    "Orchestrator": {
        "id": "00000000-0000-0000-0000-000000000101",
        "capabilities": ["orchestrate", "route", "message", "delegate"]
    },
    "Researcher": {
        "id": "00000000-0000-0000-0000-000000000102",
        "capabilities": ["search", "retrieve", "analyze", "read_memory"]
    },
    "Executor": {
        "id": "00000000-0000-0000-0000-000000000103",
        "capabilities": ["execute", "write", "delete", "network"]
    },
    "Monitor": {
        "id": "00000000-0000-0000-0000-000000000104",
        "capabilities": ["audit", "observe", "alert", "report"]
    }
}

def seed_cards():
    mcp_server = get_agent_card_mcp_server()
    print("Seeding Agent Cards...")
    
    for name, data in AGENTS.items():
        result = mcp_server.issue_card(
            agent_id=data["id"],
            capabilities=data["capabilities"],
            issuer_id=AGENTS["Orchestrator"]["id"] # Orchestrator is the default issuer
        )
        if result.get("success"):
            print(f"✓ Created card for {name} ({data['id']})")
        else:
            print(f"✗ Failed for {name}: {result.get('error')}")

if __name__ == "__main__":
    seed_cards()
