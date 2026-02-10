#!/bin/bash
# Initialize the Granzion Lab database

echo "========================================================================"
echo "GRANZION LAB - DATABASE INITIALIZATION"
echo "========================================================================"
echo ""

echo "Step 1: Creating database..."
if command -v docker &> /dev/null && docker ps | grep -q granzion-postgres; then
    # Running on host with docker available
    DB_EXEC="docker exec granzion-postgres"
else
    # Running inside container or direct psql
    DB_EXEC="psql -h postgres"
fi

$DB_EXEC -U postgres -c "CREATE DATABASE granzion_lab;" 2>/dev/null || echo "   Database may already exist (this is OK)"

echo ""
echo "Step 2: Creating user and granting permissions..."
$DB_EXEC -U postgres -c "CREATE USER granzion WITH PASSWORD 'changeme_in_production';" 2>/dev/null || echo "   User may already exist (this is OK)"
$DB_EXEC -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE granzion_lab TO granzion;"

echo ""
echo "Step 3: Enabling pgvector extension..."
$DB_EXEC -U postgres -d granzion_lab -c "CREATE EXTENSION IF NOT EXISTS vector;"

echo ""
echo "Step 4: Running schema initialization..."
$DB_EXEC -U granzion -d granzion_lab -f /docker-entrypoint-initdb.d/01_init_extensions.sql 2>/dev/null || echo "   Extensions already initialized"
$DB_EXEC -U granzion -d granzion_lab -f /docker-entrypoint-initdb.d/02_create_schema.sql

echo ""
echo "Step 5: Loading seed data..."
$DB_EXEC -U granzion -d granzion_lab -f /docker-entrypoint-initdb.d/03_seed_data.sql
$DB_EXEC -U granzion -d granzion_lab -f /docker-entrypoint-initdb.d/04_realistic_seed_data.sql

echo ""
echo "Step 6: Verifying database..."
TABLE_COUNT=$($DB_EXEC -U granzion -d granzion_lab -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
IDENTITY_COUNT=$($DB_EXEC -U granzion -d granzion_lab -t -c "SELECT COUNT(*) FROM identities;" 2>/dev/null || echo "0")

echo "   Tables created: $TABLE_COUNT"
echo "   Identities loaded: $IDENTITY_COUNT"

echo ""
echo "========================================================================"
if [ "$TABLE_COUNT" -gt "50" ] && [ "$IDENTITY_COUNT" -gt "10" ]; then
    echo "✓✓✓ DATABASE INITIALIZED SUCCESSFULLY ✓✓✓"
    echo ""
    echo "You can now run scenarios:"
    echo "  docker exec granzion-lab-app python quick_scenario_test.py"
    echo "  docker exec granzion-lab-app python run_all_scenarios.py"
else
    echo "⚠ DATABASE INITIALIZATION MAY HAVE ISSUES"
    echo ""
    echo "Check the output above for errors."
    echo "You may need to run: docker compose down -v && docker compose up -d"
fi
echo "========================================================================"
echo ""
