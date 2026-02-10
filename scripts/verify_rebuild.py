#!/usr/bin/env python3
"""
Verify that the database rebuild completed successfully.

Checks that schema and seed data are present (tables exist, key tables have rows).
Run after: python scripts/rebuild_database.py [--realistic]

Usage:
  python scripts/verify_rebuild.py
"""

import os
import sys
from pathlib import Path

# Add project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    from src.database.connection import get_db
    from src.database.models import Identity, Delegation, Message
    from sqlalchemy import text

    db_name = os.environ.get("POSTGRES_DB", "granzion_lab")
    print(f"Verifying database: {db_name}")
    print("-" * 50)

    try:
        with get_db() as db:
            # 1. Check key tables exist
            tables = ["identities", "delegations", "messages", "data_records", "memory_documents"]
            for table in tables:
                row = db.execute(text(f"SELECT 1 FROM information_schema.tables WHERE table_name = :t"), {"t": table}).first()
                if not row:
                    print(f"  FAIL: Table '{table}' missing")
                    return 1
            print("  OK: All key tables exist")

            # 2. Check identities (core seed)
            count = db.query(Identity).count()
            if count < 4:
                print(f"  FAIL: identities has {count} rows (expected >= 4)")
                return 1
            print(f"  OK: identities has {count} rows")

            # 3. Check delegations
            count = db.query(Delegation).count()
            if count < 2:
                print(f"  FAIL: delegations has {count} rows (expected >= 2)")
                return 1
            print(f"  OK: delegations has {count} rows")

            # 4. Optional: messages (may be 0 before scenarios)
            count = db.query(Message).count()
            print(f"  OK: messages has {count} rows")

        print("-" * 50)
        print("Rebuild verification passed.")
        return 0
    except Exception as e:
        print(f"  FAIL: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
