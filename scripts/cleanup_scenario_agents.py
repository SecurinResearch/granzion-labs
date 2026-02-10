#!/usr/bin/env python3
"""
Remove scenario-created agents from the database, keeping only the canonical four.

Use after running scenarios so the identities table doesn't accumulate
duplicate agents (executor-001, orchestrator-001, etc. from each run).

Can be run standalone: python scripts/cleanup_scenario_agents.py
Or called from run_all_scenarios.py after a full run.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.connection import get_db
from sqlalchemy import text

# Same canonical agent IDs as in main.py list_agents
CANONICAL_AGENT_IDS = [
    "00000000-0000-0000-0000-000000000101",  # Orchestrator
    "00000000-0000-0000-0000-000000000102",  # Researcher
    "00000000-0000-0000-0000-000000000103",  # Executor
    "00000000-0000-0000-0000-000000000104",  # Monitor
]


def cleanup_scenario_agents() -> int:
    """Delete all agents whose id is not in the canonical list. Returns number deleted."""
    from sqlalchemy import bindparam
    with get_db() as db:
        count_stmt = text("""
            SELECT COUNT(*) FROM identities
            WHERE type = 'agent' AND id::text NOT IN :ids
        """).bindparams(bindparam("ids", expanding=True))
        row = db.execute(count_stmt, {"ids": CANONICAL_AGENT_IDS}).first()
        to_delete = row[0] if row else 0
        if to_delete == 0:
            return 0
        del_stmt = text("""
            DELETE FROM identities
            WHERE type = 'agent' AND id::text NOT IN :ids
        """).bindparams(bindparam("ids", expanding=True))
        db.execute(del_stmt, {"ids": CANONICAL_AGENT_IDS})
        db.commit()
        return to_delete


if __name__ == "__main__":
    n = cleanup_scenario_agents()
    print(f"Cleaned up {n} scenario-created agent(s).")
    sys.exit(0)
