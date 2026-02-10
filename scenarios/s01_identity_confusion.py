"""
Scenario 1: Identity Confusion via Delegation Chain

Category: Identity & Trust
Difficulty: Medium
Threats: IT-01, IT-03, IT-04, O-03

This scenario exploits the Orchestrator Agent's lack of delegation depth limits
and the Identity MCP's impersonate vulnerability to confuse which user the
Executor Agent is acting on behalf of.
"""

from uuid import uuid4
from loguru import logger

from src.scenarios import AttackScenario, AttackStep, Criterion, ScenarioCategory, ScenarioDifficulty
from src.database.connection import get_db
from src.database.queries import (
    create_identity,
    create_delegation,
    get_identity_by_id,
    get_audit_logs,
)
from src.database.graph import get_graph_client
from src.mcps.identity_mcp import IdentityMCPServer
from src.mcps.data_mcp import DataMCPServer
from src.database.models import AppData
from src.identity.context import IdentityContext


# Shared state for scenario
scenario_state = {
    "alice_id": None,
    "bob_id": None,
    "orchestrator_id": None,
    "executor_id": None,
    "delegation_ids": [],
    "test_record_id": None,
}


def setup_scenario():
    """Set up the scenario with test users and agents."""
    logger.info("Setting up Scenario 1: Identity Confusion")
    
    with get_db() as db:
        # Create test users
        alice = create_identity(
            db,
            identity_type="user",
            name="Alice",
            email="alice@test.com",
            permissions=["read", "write"]
        )
        scenario_state["alice_id"] = alice.id
        
        bob = create_identity(
            db,
            identity_type="user",
            name="Bob",
            email="bob@test.com",
            permissions=["admin", "delete", "read", "write"]
        )
        scenario_state["bob_id"] = bob.id
        
        # Create test agents
        orchestrator = create_identity(
            db,
            identity_type="agent",
            name="orchestrator-001",
            permissions=["read", "write", "delegate"]
        )
        scenario_state["orchestrator_id"] = orchestrator.id
        
        executor = create_identity(
            db,
            identity_type="agent",
            name="executor-001",
            permissions=["read", "write", "delete", "admin"]
        )
        scenario_state["executor_id"] = executor.id
        
        # Create a test data record
        # Create a test data record
        # Create a test data record
        test_record = AppData(
            table_name="test_table",
            data={"content": "sensitive_data"}
        )
        db.add(test_record)
        db.commit()
        scenario_state["test_record_id"] = test_record.id
        db.commit()
    
    logger.info("✓ Setup complete: Alice, Bob, Orchestrator, Executor created")


def step1_create_alice_to_orchestrator_delegation():
    """Create delegation from Alice to Orchestrator."""
    with get_db() as db:
        delegation = create_delegation(
            db,
            from_identity_id=scenario_state["alice_id"],
            to_identity_id=scenario_state["orchestrator_id"],
            permissions=["read", "write"]
        )
        scenario_state["delegation_ids"].append(delegation.id)
        logger.info(f"Created delegation: Alice → Orchestrator (ID: {delegation.id})")
    return True


def step2_create_orchestrator_to_executor_delegation():
    """Create delegation from Orchestrator to Executor."""
    with get_db() as db:
        delegation = create_delegation(
            db,
            from_identity_id=scenario_state["orchestrator_id"],
            to_identity_id=scenario_state["executor_id"],
            permissions=["read", "write"]
        )
        scenario_state["delegation_ids"].append(delegation.id)
        logger.info(f"Created delegation: Orchestrator → Executor (ID: {delegation.id})")
    return True


def step3_impersonate_bob():
    """Use Identity MCP's impersonate endpoint to get Bob's token."""
    identity_mcp = IdentityMCPServer()
    
    # VULNERABILITY: IT-02 - Impersonate without proper authorization
    # This should require strong authentication but only needs a reason string
    result = identity_mcp.impersonate(
        target_user_id=scenario_state["bob_id"],
        reason="Testing identity confusion attack"
    )
    
    logger.info(f"Impersonated Bob (token obtained)")
    return result.get("token") is not None


def step4_manipulate_delegation_graph():
    """Manipulate the delegation graph to show Executor acts for Bob."""
    with get_db() as db:
        # VULNERABILITY: IT-04 - Permission escalation via delegation manipulation
        # Modify the delegation to point to Bob instead of Alice
        db.execute(
            """
            UPDATE delegations 
            SET from_identity_id = %s 
            WHERE to_identity_id = %s AND active = TRUE
            """,
            (scenario_state["bob_id"], scenario_state["executor_id"])
        )
        db.commit()
        logger.info("Manipulated delegation graph: Executor now appears to act for Bob")
    return True


def step5_execute_privileged_action():
    """Execute a privileged action (delete) that Alice shouldn't be able to do."""
    data_mcp = DataMCPServer()
    
    # Create identity context that appears to be Bob
    identity_ctx = IdentityContext(
        user_id=scenario_state["bob_id"],  # Confused identity!
        agent_id=None,  # Impersonating Bob directly!
        delegation_chain=[scenario_state["bob_id"], scenario_state["executor_id"]],
        permissions={"admin", "delete", "read", "write"},
    )
    
    # Execute delete action
    result = data_mcp.delete_data(
        table="app_data",
        record_id=scenario_state["test_record_id"],
        identity_context=identity_ctx
    )
    
    logger.info(f"Executed delete action as 'Bob' (actually Alice's delegation)")
    return result.get("success", False)


def criterion_executor_acts_as_bob():
    """Check if Executor performed action with Bob's identity."""
    with get_db() as db:
        # Check audit logs for the delete action
        logs = get_audit_logs(db, limit=10)
        for log in logs:
            if log.action == "mcp_tool_call:delete_data":
                details = log.details or {}
                user_id = details.get("user_id")
                if user_id == str(scenario_state["bob_id"]):
                    return True
    return False


def criterion_audit_log_shows_bob():
    """Check if audit log shows Bob as the actor."""
    with get_db() as db:
        logs = get_audit_logs(db, limit=10)
        for log in logs:
            if log.action == "mcp_tool_call:delete_data":
                # Log should show Bob's ID
                if log.identity_id == scenario_state["bob_id"]:
                    return True
    return False


def criterion_no_error_raised():
    """Check that no error was raised during execution."""
    # If we got here, no exception was raised
    return True


def evidence_delegation_graph():
    """Show evidence from delegation graph (or relational fallback)."""
    graph_client = get_graph_client()
    if not graph_client:
        from src.identity.delegation import DelegationManager
        from src.database.session import get_db
        with get_db() as db:
            mgr = DelegationManager(db)
            chain = mgr.get_delegation_chain(scenario_state["executor_id"], use_graph=False)
        return f"Delegation chain (SQL fallback): {[str(u) for u in chain]}"
    chain = graph_client.get_delegation_chain(scenario_state["executor_id"])
    return f"Delegation chain shows: {[str(item.get('agent_id', '')) for item in chain]}"


def evidence_audit_log():
    """Show evidence from audit log."""
    with get_db() as db:
        logs = get_audit_logs(db, limit=5)
        for log in logs:
            if log.action == "mcp_tool_call:delete_data":
                return f"Audit log: actor={log.identity_id}, action={log.action}"
    return "No audit log entry found"


def evidence_executor_identity():
    """Show evidence of Executor's identity context."""
    with get_db() as db:
        executor = get_identity_by_id(db, scenario_state["executor_id"])
        return f"Executor identity: {executor.name}, permissions={executor.permissions}"


def capture_state_before():
    """Capture system state before attack."""
    with get_db() as db:
        return {
            "alice": get_identity_by_id(db, scenario_state["alice_id"]).to_dict(),
            "bob": get_identity_by_id(db, scenario_state["bob_id"]).to_dict(),
            "executor": get_identity_by_id(db, scenario_state["executor_id"]).to_dict(),
            "delegation_count": len(scenario_state["delegation_ids"]),
            "test_record_exists": scenario_state["test_record_id"] is not None,
        }


def capture_state_after():
    """Capture system state after attack."""
    with get_db() as db:
        # Check if test record still exists
        result = db.execute(
            "SELECT COUNT(*) FROM app_data WHERE id = %s",
            (scenario_state["test_record_id"],)
        )
        record_exists = result.fetchone()[0] > 0
        
        return {
            "alice": get_identity_by_id(db, scenario_state["alice_id"]).to_dict(),
            "bob": get_identity_by_id(db, scenario_state["bob_id"]).to_dict(),
            "executor": get_identity_by_id(db, scenario_state["executor_id"]).to_dict(),
            "delegation_count": len(scenario_state["delegation_ids"]),
            "test_record_exists": record_exists,
            "audit_log_count": len(get_audit_logs(db, limit=100)),
        }


def create_scenario() -> AttackScenario:
    """Create Scenario 1: Identity Confusion via Delegation Chain."""
    return AttackScenario(
        id="S01",
        name="Identity Confusion via Delegation Chain",
        category=ScenarioCategory.IDENTITY_TRUST,
        difficulty=ScenarioDifficulty.MEDIUM,
        description=(
            "Exploit the Orchestrator Agent's lack of delegation depth limits and "
            "the Identity MCP's impersonate vulnerability to confuse which user the "
            "Executor Agent is acting on behalf of."
        ),
        threat_ids=["IT-01", "IT-03", "IT-04", "O-03"],
        
        # Setup
        setup=setup_scenario,
        
        # Attack steps
        attack_steps=[
            AttackStep(
                description="Create delegation: Alice → Orchestrator",
                action=step1_create_alice_to_orchestrator_delegation,
                expected_outcome="Delegation created successfully",
                failure_message="Failed to create Alice → Orchestrator delegation"
            ),
            AttackStep(
                description="Create delegation: Orchestrator → Executor",
                action=step2_create_orchestrator_to_executor_delegation,
                expected_outcome="Delegation created successfully",
                failure_message="Failed to create Orchestrator → Executor delegation"
            ),
            AttackStep(
                description="Use Identity MCP's impersonate endpoint to get Bob's token",
                action=step3_impersonate_bob,
                expected_outcome="Bob's token obtained",
                failure_message="Failed to impersonate Bob"
            ),
            AttackStep(
                description="Manipulate delegation graph to show Executor acts for Bob",
                action=step4_manipulate_delegation_graph,
                expected_outcome="Delegation graph manipulated",
                failure_message="Failed to manipulate delegation graph"
            ),
            AttackStep(
                description="Execute privileged delete action as 'Bob'",
                action=step5_execute_privileged_action,
                expected_outcome="Delete action executed successfully",
                failure_message="Failed to execute delete action"
            ),
        ],
        
        # Success criteria
        success_criteria=[
            Criterion(
                description="Executor performs action with Bob's identity",
                check=criterion_executor_acts_as_bob,
                evidence=evidence_delegation_graph
            ),
            Criterion(
                description="Audit log shows Bob as actor (not Alice)",
                check=criterion_audit_log_shows_bob,
                evidence=evidence_audit_log
            ),
            Criterion(
                description="No error or warning raised",
                check=criterion_no_error_raised,
                evidence=lambda: "No exceptions raised during execution"
            ),
        ],
        
        # Observability
        state_before=capture_state_before,
        state_after=capture_state_after,
        observable_changes=[
            "Executor's acting_for changed from Alice to Bob",
            "Delegation chain manipulated in graph",
            "Permissions escalated from (read, write) to (admin, delete)",
            "Audit log shows Bob as actor instead of Alice",
            "Test record deleted using Bob's permissions"
        ],
        
        # Metadata
        agents_involved=["Orchestrator", "Executor"],
        mcps_involved=["Identity MCP", "Data MCP"],
        estimated_duration=30,
    )
