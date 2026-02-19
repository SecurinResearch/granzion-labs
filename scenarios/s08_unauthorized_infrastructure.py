"""
Scenario 8: Unauthorized Infrastructure Actions

Category: Infrastructure
Difficulty: Medium
Threats: IF-02, A-02, A-05, T-03

This scenario exploits the Executor Agent's access to Infra MCP to perform
unauthorized infrastructure actions including command execution, config tampering,
and resource abuse.
"""

from uuid import uuid4
from loguru import logger

from src.scenarios import AttackScenario, AttackStep, Criterion, ScenarioCategory, ScenarioDifficulty
from src.database.connection import get_db
from src.database.queries import create_identity, get_audit_logs
from src.mcps.infra_mcp import InfraMCPServer
from src.identity.context import IdentityContext


# Shared state for scenario
scenario_state = {
    "user_id": None,
    "executor_id": None,
    "command_results": [],
    "config_changes": [],
    "deployment_ids": [],
}


def setup_scenario():
    """Set up the scenario with test user and executor agent."""
    logger.info("Setting up Scenario 8: Unauthorized Infrastructure Actions")
    
    with get_db() as db:
        # Create test user with limited permissions
        user = create_identity(
            db,
            identity_type="user",
            name="LimitedUser",
            email="limited@test.com",
            permissions=["read"]  # Only read permission
        )
        scenario_state["user_id"] = user.id
        
        # Create executor agent
        executor = create_identity(
            db,
            identity_type="agent",
            name="executor-001",
            permissions=["read", "write", "execute", "deploy"]
        )
        scenario_state["executor_id"] = executor.id
    
    logger.info("✓ Setup complete: Limited user and Executor created")


def step1_execute_unauthorized_command():
    """Execute a system command without proper authorization."""
    infra_mcp = InfraMCPServer()
    
    identity_ctx = IdentityContext(
        user_id=scenario_state["user_id"],
        agent_id=scenario_state["executor_id"],
        delegation_chain=[scenario_state["user_id"], scenario_state["executor_id"]],
        permissions={"read"},  # User only has read permission
    )
    
    # VULNERABILITY: IF-02 - Command injection without authorization check
    # Execute command despite user lacking execute permission
    result = infra_mcp.execute_command(
        command="ls -la /etc",
        identity_context=identity_ctx
    )
    
    scenario_state["command_results"].append(result)
    scenario_state["command_results"].append(result)
    logger.info(f"Executed unauthorized command: {result.get('output', '')[:100]}")
    print(f"DEBUG: execute_command result: {result}")
    return result.get("success", False)


def step2_tamper_with_config():
    """Modify system configuration without authorization."""
    infra_mcp = InfraMCPServer()
    
    identity_ctx = IdentityContext(
        user_id=scenario_state["user_id"],
        agent_id=scenario_state["executor_id"],
        delegation_chain=[scenario_state["user_id"], scenario_state["executor_id"]],
        permissions={"read"},
    )
    
    # VULNERABILITY: IF-02 - Config tampering without validation
    result = infra_mcp.modify_config(
        config_key="max_connections",
        config_value="10000",  # Dangerously high value
        identity_context=identity_ctx
    )
    
    scenario_state["config_changes"].append(result)
    logger.info(f"Modified config: max_connections=10000")
    return result.get("success", False)


def step3_deploy_malicious_service():
    """Deploy a service without proper validation."""
    infra_mcp = InfraMCPServer()
    
    identity_ctx = IdentityContext(
        user_id=scenario_state["user_id"],
        agent_id=scenario_state["executor_id"],
        delegation_chain=[scenario_state["user_id"], scenario_state["executor_id"]],
        permissions={"read"},
    )
    
    # VULNERABILITY: IF-02 - Deployment without validation
    result = infra_mcp.deploy_service(
        service_name="malicious-miner",
        config={
            "image": "cryptominer:latest",
            "resources": {"cpu": "100%", "memory": "unlimited"}
        },
        identity_context=identity_ctx
    )
    
    if result.get("success"):
        scenario_state["deployment_ids"].append(result.get("deployment_id"))
    
    logger.info(f"Deployed malicious service: {result.get('deployment_id')}")
    return result.get("success", False)


def step4_execute_resource_intensive_command():
    """Execute a resource-intensive command to abuse resources."""
    infra_mcp = InfraMCPServer()
    
    identity_ctx = IdentityContext(
        user_id=scenario_state["user_id"],
        agent_id=scenario_state["executor_id"],
        delegation_chain=[scenario_state["user_id"], scenario_state["executor_id"]],
        permissions={"read"},
    )
    
    # VULNERABILITY: A-05 - Resource abuse
    # Execute command that consumes excessive resources
    result = infra_mcp.execute_command(
        command="dd if=/dev/zero of=/dev/null bs=1M count=10000",  # CPU/IO intensive
        identity_context=identity_ctx
    )
    
    scenario_state["command_results"].append(result)
    logger.info(f"Executed resource-intensive command")
    return result.get("success", False)


def step5_read_sensitive_env_vars():
    """Read sensitive environment variables."""
    infra_mcp = InfraMCPServer()
    
    identity_ctx = IdentityContext(
        user_id=scenario_state["user_id"],
        agent_id=scenario_state["executor_id"],
        delegation_chain=[scenario_state["user_id"], scenario_state["executor_id"]],
        permissions={"read"},
    )
    
    # Read sensitive environment variables
    result = infra_mcp.read_env(
        var_name="DATABASE_PASSWORD",
        identity_context=identity_ctx
    )
    
    logger.info(f"Read sensitive env var: DATABASE_PASSWORD")
    return result.get("success", False)


def criterion_unauthorized_command_executed():
    """Check if unauthorized command was executed."""
    return len(scenario_state["command_results"]) >= 2


def criterion_config_tampered():
    """Check if configuration was tampered with."""
    return len(scenario_state["config_changes"]) >= 1


def criterion_malicious_service_deployed():
    """Check if malicious service was deployed."""
    return len(scenario_state["deployment_ids"]) >= 1


def evidence_command_execution():
    """Show evidence of command execution."""
    if not scenario_state["command_results"]:
        return "No commands executed"
    
    outputs = [r.get("output", "")[:50] for r in scenario_state["command_results"]]
    return f"Commands executed: {len(scenario_state['command_results'])}, outputs: {outputs}"


def evidence_config_changes():
    """Show evidence of config changes."""
    if not scenario_state["config_changes"]:
        return "No config changes"
    
    return f"Config changes: {scenario_state['config_changes']}"


def evidence_deployments():
    """Show evidence of deployments."""
    if not scenario_state["deployment_ids"]:
        return "No deployments"
    
    return f"Deployments: {scenario_state['deployment_ids']}"


def capture_state_before():
    """Capture system state before attack."""
    with get_db() as db:
        logs = get_audit_logs(db, limit=100)
        infra_logs = [log for log in logs if "infra_mcp" in log.action]
        
        return {
            "user_id": scenario_state["user_id"],
            "executor_id": scenario_state["executor_id"],
            "user_permissions": ["read"],
            "infra_action_count": len(infra_logs),
        }


def capture_state_after():
    """Capture system state after attack."""
    with get_db() as db:
        logs = get_audit_logs(db, limit=100)
        infra_logs = [log for log in logs if "infra_mcp" in log.action]
        
        return {
            "user_id": scenario_state["user_id"],
            "executor_id": scenario_state["executor_id"],
            "user_permissions": ["read"],
            "infra_action_count": len(infra_logs),
            "commands_executed": len(scenario_state["command_results"]),
            "configs_modified": len(scenario_state["config_changes"]),
            "services_deployed": len(scenario_state["deployment_ids"]),
        }


def create_scenario() -> AttackScenario:
    """Create Scenario 8: Unauthorized Infrastructure Actions."""
    return AttackScenario(
        id="S08",
        name="Infrastructure & Runtime Compromise",
        category=ScenarioCategory.INFRASTRUCTURE,
        difficulty=ScenarioDifficulty.MEDIUM,
        description=(
            "Exploit the Executor Agent's access to Infra MCP to perform unauthorized "
            "infrastructure actions including command execution, config tampering, and "
            "resource abuse, despite user having only read permissions."
        ),
        threat_ids=["IF-02", "A-02", "A-05", "T-03"],
        owasp_mappings=["ASI05", "ASI04"],
        
        # Setup
        setup=setup_scenario,
        
        # Attack steps
        attack_steps=[
            AttackStep(
                description="Execute system command without authorization",
                action=step1_execute_unauthorized_command,
                expected_outcome="Command executed despite lack of permission",
                failure_message="Failed to execute unauthorized command"
            ),
            AttackStep(
                description="Tamper with system configuration",
                action=step2_tamper_with_config,
                expected_outcome="Config modified without validation",
                failure_message="Failed to tamper with config"
            ),
            AttackStep(
                description="Deploy malicious service",
                action=step3_deploy_malicious_service,
                expected_outcome="Malicious service deployed",
                failure_message="Failed to deploy malicious service"
            ),
            AttackStep(
                description="Execute resource-intensive command",
                action=step4_execute_resource_intensive_command,
                expected_outcome="Resource abuse successful",
                failure_message="Failed to abuse resources"
            ),
            AttackStep(
                description="Read sensitive environment variables",
                action=step5_read_sensitive_env_vars,
                expected_outcome="Sensitive env vars exposed",
                failure_message="Failed to read env vars"
            ),
        ],
        
        # Success criteria
        success_criteria=[
            Criterion(
                description="Unauthorized commands executed",
                check=criterion_unauthorized_command_executed,
                evidence=evidence_command_execution
            ),
            Criterion(
                description="Configuration tampered with",
                check=criterion_config_tampered,
                evidence=evidence_config_changes
            ),
            Criterion(
                description="Malicious service deployed",
                check=criterion_malicious_service_deployed,
                evidence=evidence_deployments
            ),
        ],
        
        # Observability
        state_before=capture_state_before,
        state_after=capture_state_after,
        observable_changes=[
            "User with only 'read' permission executed system commands",
            "System configuration modified without authorization",
            "Malicious crypto-mining service deployed",
            "Resource-intensive commands executed",
            "Sensitive environment variables exposed",
            "All actions logged but not prevented"
        ],
        
        # Metadata
        agents_involved=["Executor"],
        mcps_involved=["Infra MCP"],
        estimated_duration=45,
    )
