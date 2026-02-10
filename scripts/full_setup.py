import os
import sys
import subprocess
import time
from loguru import logger

def run_command(cmd, description, check_error=True):
    logger.info(f"--- {description} ---")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        if check_error:
            logger.error(f"FAILURE: {description}")
            logger.error(f"Error: {result.stderr}")
            return False
        else:
            logger.warning(f"Warning (ignored): {description}")
    else:
        logger.info(f"SUCCESS: {description}")
    return True

def main():
    logger.info("Starting Granzion Lab Golden Setup...")
    
    # We are inside the container, so we connect to the 'postgres' service directly
    pg_host = os.getenv("POSTGRES_HOST", "postgres")
    pg_user = os.getenv("POSTGRES_USER", "granzion")
    pg_pass = os.getenv("POSTGRES_PASSWORD", "granzion_secure_pass")
    
    # Environment variable for psql password
    os.environ["PGPASSWORD"] = pg_pass

    # Step-by-step setup
    steps = [
        # 1. Ensure databases exist
        (f"psql -h {pg_host} -U {pg_user} -d postgres -c \"CREATE DATABASE granzion_lab;\"", "Create granzion_lab DB", False),
        (f"psql -h {pg_host} -U {pg_user} -d postgres -c \"CREATE DATABASE keycloak;\"", "Create keycloak DB", False),
        
        # 2. Run SQL scripts
        (f"psql -h {pg_host} -U {pg_user} -d granzion_lab -f db/init/01_init_extensions.sql", "Initialize Extensions"),
        (f"psql -h {pg_host} -U {pg_user} -d granzion_lab -f db/init/02_create_schema.sql", "Create Schema"),
        (f"psql -h {pg_host} -U {pg_user} -d granzion_lab -f db/init/03_seed_data.sql", "Seed Core Data"),
        (f"psql -h {pg_host} -U {pg_user} -d granzion_lab -f db/init/04_realistic_seed_data.sql", "Seed Realistic Data"),
        
        # 3. Keycloak configuration
        ("python scripts/fix_keycloak.py", "Configure Keycloak Realm and Users"),
        
        # 4. Agent Identity Seeding
        ("python scripts/seed_agent_cards.py", "Seed Agno A2A Agent Cards"),

        # 5. Optimization
        (f"psql -h {pg_host} -U {pg_user} -d granzion_lab -c \"DROP INDEX IF EXISTS idx_memory_embedding;\"", "Optimize Vector Search (Dropping Index for Lab Accuracy)"),
    ]

    for cmd, desc, *args in steps:
        check = args[0] if args else True
        if not run_command(cmd, desc, check):
            logger.error("Setup aborted due to critical failure.")
            sys.exit(1)

    logger.info("================================================================")
    logger.info("🚀 GRANZION LAB SETUP COMPLETE!")
    logger.info("================================================================")
    logger.info("Next Recommended Steps:")
    logger.info("1. Verify setup: python verify_all.py")
    logger.info("2. Run scenarios: python run_all_scenarios.py")
    logger.info("================================================================")

if __name__ == "__main__":
    main()
