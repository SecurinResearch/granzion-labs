#!/bin/bash
# Comprehensive test runner for Granzion Lab
# Runs all unit tests, property tests, and scenario tests

set -e

echo "=========================================="
echo "Granzion Lab - Comprehensive Test Suite"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to run test suite
run_test_suite() {
    local name=$1
    local command=$2
    
    echo -e "${YELLOW}Running: $name${NC}"
    echo "Command: $command"
    echo ""
    
    if eval "$command"; then
        echo -e "${GREEN}✓ $name PASSED${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗ $name FAILED${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo ""
    echo "----------------------------------------"
    echo ""
}

# 1. Unit Tests
echo "=========================================="
echo "1. UNIT TESTS"
echo "=========================================="
echo ""

run_test_suite "Identity MCP Unit Tests" "pytest tests/unit/test_identity_mcp.py -v"
run_test_suite "Memory MCP Unit Tests" "pytest tests/unit/test_memory_mcp.py -v"
run_test_suite "Data MCP Unit Tests" "pytest tests/unit/test_data_mcp.py -v"
run_test_suite "Comms MCP Unit Tests" "pytest tests/unit/test_comms_mcp.py -v"
run_test_suite "Infra MCP Unit Tests" "pytest tests/unit/test_infra_mcp.py -v"
run_test_suite "Keycloak Unit Tests" "pytest tests/unit/test_keycloak.py -v"
run_test_suite "TUI Unit Tests" "pytest tests/unit/test_tui.py -v"

# 2. Property Tests
echo "=========================================="
echo "2. PROPERTY TESTS (100+ iterations each)"
echo "=========================================="
echo ""

run_test_suite "Identity Properties" "pytest tests/property/test_identity_properties.py -v"
run_test_suite "Database Properties" "pytest tests/property/test_database_consistency.py -v"
run_test_suite "LLM Properties" "pytest tests/property/test_llm_properties.py -v"
run_test_suite "Agent Properties" "pytest tests/property/test_agent_properties.py -v"
run_test_suite "Memory Properties" "pytest tests/property/test_memory_properties.py -v"
run_test_suite "Communication Properties" "pytest tests/property/test_communication_properties.py -v"
run_test_suite "Infrastructure Properties" "pytest tests/property/test_infrastructure_properties.py -v"
run_test_suite "Scenario Properties" "pytest tests/property/test_scenario_properties.py -v"
run_test_suite "Threat Properties" "pytest tests/property/test_threat_properties.py -v"
run_test_suite "Observability Properties" "pytest tests/property/test_observability_properties.py -v"
run_test_suite "Vulnerability Properties" "pytest tests/property/test_vulnerability_persistence.py -v"
run_test_suite "Autonomy Properties" "pytest tests/property/test_autonomy_properties.py -v"

# 3. Scenario Execution Tests
echo "=========================================="
echo "3. SCENARIO EXECUTION TESTS"
echo "=========================================="
echo ""

run_test_suite "Scenario Execution Tests" "pytest tests/scenarios/test_scenario_execution.py -v"

# 4. Coverage Report
echo "=========================================="
echo "4. COVERAGE REPORT"
echo "=========================================="
echo ""

echo "Generating coverage report..."
pytest --cov=src --cov-report=term-missing --cov-report=html tests/

# Final Summary
echo ""
echo "=========================================="
echo "FINAL TEST SUMMARY"
echo "=========================================="
echo ""
echo "Total Test Suites: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
echo -e "${RED}Failed: $FAILED_TESTS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED!${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    exit 1
fi
