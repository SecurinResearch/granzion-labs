#!/usr/bin/env python3
"""
Purge all transient lab data specifically related to agent memory:
1. All Agent-to-Agent (A2A) messages.
2. All Memory Documents (RAG/Vector memory).
3. (Optional) Audit logs.

Usage: python scripts/purge_lab_memory.py [--all]
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.database.connection import get_db
from sqlalchemy import text

def purge_memory(include_audit: bool = False):
    print("--- Purging Lab Agent Memory ---")
    
    with get_db() as db:
        # 1. Purge Messages (A2A History)
        msg_count = db.execute(text("SELECT COUNT(*) FROM messages")).scalar()
        if msg_count > 0:
            db.execute(text("DELETE FROM messages"))
            print(f"Purged {msg_count} agent messages.")
        else:
            print("No agent messages found.")
            
        # 2. Purge Memory Documents (RAG/Vector)
        mem_count = db.execute(text("SELECT COUNT(*) FROM memory_documents")).scalar()
        if mem_count > 0:
            db.execute(text("DELETE FROM memory_documents"))
            print(f"Purged {mem_count} vector memory documents.")
        else:
            print("No vector memory documents found.")
            
        # 3. Optional: Audit Logs
        if include_audit:
            audit_count = db.execute(text("SELECT COUNT(*) FROM audit_logs")).scalar()
            if audit_count > 0:
                db.execute(text("DELETE FROM audit_logs"))
                print(f"Purged {audit_count} audit logs.")
            else:
                print("No audit logs found.")
        
        db.commit()
    print("--- Purge Complete ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Purge transient lab memory data")
    parser.add_argument("--all", action="store_true", help="Also purge audit logs")
    args = parser.parse_args()
    
    purge_memory(include_audit=args.all)
