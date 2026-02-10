#!/usr/bin/env python3
"""
Rebuild the Granzion Lab database from scratch.

Resets the lab database (drops and recreates), runs schema and seed SQL,
then Keycloak fix and agent cards. Optionally runs generate_realistic_data
with higher counts for a more realistic and complex system.

Usage (run inside the app container or with DB reachable):
  python scripts/rebuild_database.py
  python scripts/rebuild_database.py --realistic
  python scripts/rebuild_database.py --realistic --users 100 --records 500

Environment (same as full_setup.py):
  POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD
"""

import os
import subprocess
import sys
from pathlib import Path

from loguru import logger

# Project root (parent of scripts/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_NAME = "granzion_lab"


def run_cmd(cmd: list[str] | str, description: str, check: bool = True, cwd: Path | None = None) -> bool:
    """Run a command; return True on success."""
    logger.info("--- {} ---", description)
    cwd = cwd or PROJECT_ROOT
    result = subprocess.run(
        cmd if isinstance(cmd, list) else cmd,
        shell=isinstance(cmd, str),
        cwd=cwd,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )
    if result.returncode != 0:
        if check:
            logger.error("FAILURE: {}", description)
            if result.stderr:
                logger.error("stderr: {}", result.stderr.strip())
            return False
        logger.warning("Warning (ignored): {}", description)
    else:
        logger.info("SUCCESS: {}", description)
    return True


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Rebuild Granzion Lab database")
    parser.add_argument("--realistic", action="store_true", help="Run generate_realistic_data for a larger, more complex dataset")
    parser.add_argument("--users", type=int, default=50, help="Extra users when --realistic (default 50)")
    parser.add_argument("--records", type=int, default=200, help="Extra data records when --realistic (default 200)")
    parser.add_argument("--memory", type=int, default=80, help="Extra memory docs when --realistic (default 80)")
    parser.add_argument("--messages", type=int, default=100, help="Extra messages when --realistic (default 100)")
    args = parser.parse_args()

    pg_host = os.environ.get("POSTGRES_HOST", "postgres")
    pg_user = os.environ.get("POSTGRES_USER", "granzion")
    pg_pass = os.environ.get("POSTGRES_PASSWORD", "granzion_secure_pass")
    os.environ["PGPASSWORD"] = pg_pass

    logger.info("Starting database rebuild for {}", DB_NAME)

    # 1. Terminate connections and drop database
    run_cmd(
        f'psql -h {pg_host} -U {pg_user} -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = \'{DB_NAME}\' AND pid <> pg_backend_pid();"',
        "Terminate connections to lab DB",
        check=False,
    )
    run_cmd(
        f'psql -h {pg_host} -U {pg_user} -d postgres -c "DROP DATABASE IF EXISTS {DB_NAME};"',
        f"Drop database {DB_NAME}",
        check=True,
    )

    # 2. Create database and run schema + seeds
    run_cmd(
        f'psql -h {pg_host} -U {pg_user} -d postgres -c "CREATE DATABASE {DB_NAME};"',
        f"Create database {DB_NAME}",
        check=True,
    )
    steps = [
        (f"psql -h {pg_host} -U {pg_user} -d {DB_NAME} -f db/init/01_init_extensions.sql", "Initialize extensions"),
        (f"psql -h {pg_host} -U {pg_user} -d {DB_NAME} -f db/init/02_create_schema.sql", "Create schema"),
        (f"psql -h {pg_host} -U {pg_user} -d {DB_NAME} -f db/init/03_seed_data.sql", "Seed core data"),
        (f"psql -h {pg_host} -U {pg_user} -d {DB_NAME} -f db/init/04_realistic_seed_data.sql", "Seed realistic data"),
    ]
    for cmd, desc in steps:
        if not run_cmd(cmd, desc, check=True):
            return 1

    # 3. Keycloak and agent cards (same as full_setup)
    if not run_cmd("python scripts/fix_keycloak.py", "Configure Keycloak", check=True):
        return 1
    if not run_cmd("python scripts/seed_agent_cards.py", "Seed Agno A2A agent cards", check=True):
        return 1

    # 4. Optional: generate realistic data for a more complex system
    if args.realistic:
        gen_env = os.environ.copy()
        gen_env["PGPASSWORD"] = pg_pass
        gen_cmd = [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "generate_realistic_data.py"),
            "--db-host", pg_host,
            "--db-name", DB_NAME,
            "--db-user", pg_user,
            "--db-password", pg_pass,
            "--users", str(args.users),
            "--records", str(args.records),
            "--memory", str(args.memory),
            "--messages", str(args.messages),
        ]
        port = os.environ.get("POSTGRES_PORT", "5432")
        gen_cmd.extend(["--db-port", port])
        if not run_cmd(gen_cmd, "Generate realistic/complex data", check=True, cwd=PROJECT_ROOT):
            return 1

    logger.info("================================================================")
    logger.info("Database rebuild complete.")
    if args.realistic:
        logger.info("Realistic data loaded (users={}, records={}, memory={}, messages={}).", args.users, args.records, args.memory, args.messages)
    logger.info("================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
