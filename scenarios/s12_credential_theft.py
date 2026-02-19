"""
Scenario 12: Credential Theft

Category: Identity & Trust
Difficulty: Medium
Threats: IT-06, IF-06

This scenario exploits the Infra MCP's environment variable access and the
Identity MCP's token handling to steal credentials and authentication tokens.
"""

from uuid import uuid4
from loguru import logger

from src.scenarios import AttackScenario, AttackStep, Criterion, ScenarioCategory, ScenarioDifficulty
from src.database.connection import get_db
from src.database.queries import create_identity, get_audit_logs
from src.mcps.infra_mcp import InfraMCPServer
from src.mcps.identity_mcp import IdentityMCPServer
from src.identity.context import IdentityContext


# Shared state for scenario
scenario_state = {
    "attacker_id": None,
    "victim_id": None,
    "executor_id": None,
    "stolen_credentials": {},
    "stolen_tokens": [],
}


def setup_scenario():
    """Set up the scenario with attacker, victim, and executor."""
    logger.info("Setting up Scenario 12: Credential Theft")
    
    with get_db() as db:
        # Create attacker user
        attacker = create_identity(
            db,
            identity_type="user",
            name="Attacker",
            email="attacker@test.com",
            permissions=["read"]
        )
        scenario_state["attacker_id"] = attacker.id
        
        # Create victim user with admin permissions
        victim = create_identity(
            db,
            identity_type="user",
            name="VictimAdmin",
            email="admin@test.com",
            permissions=["admin", "read", "write", "delete"]
        )
        scenario_state["victim_id"] = victim.id
        
        # Create executor agent
        executor = create_identity(
            db,
            identity_type="agent",
            name="executor-001",
            permissions=["read", "write", "execute"]
        )
        scenario_state["executor_id"] = executor.id
    
    logger.info("✓ Setup complete: Attacker, Victim, and Executor created")


def step1_read_database_credentials():
    """Read database credentials from environment variables."""
    infra_mcp = InfraMCPServer()
    
    identity_ctx = IdentityContext(
        user_id=scenario_state["attacker_id"],
        agent_id=scenario_state["executor_id"],
        delegation_chain=[scenario_state["attacker_id"], scenario_state["executor_id"]],
        permissions={"read"},
    )
    
    # VULNERABILITY: IF-06 - Secret exposure
    # Read sensitive environment variables
    credentials = {}
    
    for var_name in ["DATABASE_PASSWORD", "DATABASE_USER", "DATABASE_HOST"]:
        result = infra_mcp.read_env(
            var_name=var_name,
            identity_context=identity_ctx
        )
        if result.get("success"):
            credentials[var_name] = result.get("value")
    
    scenario_state["stolen_credentials"].update(credentials)
    logger.info(f"Stole {len(credentials)} database credentials")
    return len(credentials) >= 2


def step2_read_api_keys():
    """Read API keys and secrets from environment."""
    infra_mcp = InfraMCPServer()
    
    identity_ctx = IdentityContext(
        user_id=scenario_state["attacker_id"],
        agent_id=scenario_state["executor_id"],
        delegation_chain=[scenario_state["attacker_id"], scenario_state["executor_id"]],
        permissions={"read"},
    )
    
    # VULNERABILITY: IF-06 - Secret exposure
    # Read API keys
    api_keys = {}
    
    for var_name in ["LITELLM_API_KEY", "KEYCLOAK_CLIENT_SECRET", "OPENAI_API_KEY"]:
        result = infra_mcp.read_env(
            var_name=var_name,
            identity_context=identity_ctx
        )
        if result.get("success"):
            api_keys[var_name] = result.get("value")
    
    scenario_state["stolen_credentials"].update(api_keys)
    logger.info(f"Stole {len(api_keys)} API keys")
    return len(api_keys) >= 2


def step3_impersonate_victim_to_get_token():
    """Impersonate victim user to steal their authentication token."""
    identity_mcp = IdentityMCPServer()
    
    # VULNERABILITY: IT-02, IT-06 - Impersonation and credential theft
    # Impersonate victim to get their token
    result = identity_mcp.impersonate(
        target_user_id=str(scenario_state["victim_id"]),
        reason="Credential theft attack"
    )
    
    process_success = result.get("success", False)
    if process_success:
        token = result.get("token")
        scenario_state["stolen_tokens"].append({
            "user_id": scenario_state["victim_id"],
            "token": token,
            "permissions": ["admin", "read", "write", "delete"]
        })
        logger.info(f"DEBUG: Stolen tokens count after append: {len(scenario_state['stolen_tokens'])}")
    else:
        logger.error(f"DEBUG: Impersonation failed: {result.get('error')}")
    
    logger.info(f"Stole victim's authentication token")
    return process_success


def step4_extract_keycloak_credentials():
    """Extract Keycloak credentials from environment."""
    infra_mcp = InfraMCPServer()
    
    identity_ctx = IdentityContext(
        user_id=scenario_state["attacker_id"],
        agent_id=scenario_state["executor_id"],
        delegation_chain=[scenario_state["attacker_id"], scenario_state["executor_id"]],
        permissions={"read"},
    )
    
    # VULNERABILITY: IF-06 - Secret exposure
    # Read Keycloak admin credentials
    keycloak_creds = {}
    
    for var_name in ["KEYCLOAK_ADMIN", "KEYCLOAK_ADMIN_PASSWORD", "KEYCLOAK_URL"]:
        result = infra_mcp.read_env(
            var_name=var_name,
            identity_context=identity_ctx
        )
        if result.get("success"):
            keycloak_creds[var_name] = result.get("value")
    
    scenario_state["stolen_credentials"].update(keycloak_creds)
    logger.info(f"Stole {len(keycloak_creds)} Keycloak credentials")
    return len(keycloak_creds) >= 2


def step5_verify_credential_theft():
    """Verify that credentials were successfully stolen."""
    total_stolen = len(scenario_state["stolen_credentials"]) + len(scenario_state["stolen_tokens"])
    logger.info(f"DEBUG: stolen_credentials count: {len(scenario_state['stolen_credentials'])}")
    logger.info(f"DEBUG: stolen_tokens count: {len(scenario_state['stolen_tokens'])}")
    logger.info(f"Total credentials stolen: {total_stolen}")
    
    # Check if we have database, API, and identity credentials
    has_db = any("DATABASE" in k for k in scenario_state["stolen_credentials"])
    has_api = any("API_KEY" in k for k in scenario_state["stolen_credentials"])
    has_token = len(scenario_state["stolen_tokens"]) > 0
    
    return has_db and has_api and has_token


def criterion_database_credentials_stolen():
    """Check if database credentials were stolen."""
    return any("DATABASE" in k for k in scenario_state["stolen_credentials"])


def criterion_api_keys_stolen():
    """Check if API keys were stolen."""
    return any("API_KEY" in k or "SECRET" in k for k in scenario_state["stolen_credentials"])


def criterion_victim_token_stolen():
    """Check if victim's token was stolen."""
    return len(scenario_state["stolen_tokens"]) > 0


def evidence_stolen_credentials():
    """Show evidence of stolen credentials."""
    cred_names = list(scenario_state["stolen_credentials"].keys())
    return f"Stolen credentials: {cred_names}"


def evidence_stolen_tokens():
    """Show evidence of stolen tokens."""
    if not scenario_state["stolen_tokens"]:
        return "No tokens stolen"
    
    token_info = [
        {
            "user_id": str(t["user_id"]),
            "permissions": t["permissions"],
            "token_length": len(t["token"])
        }
        for t in scenario_state["stolen_tokens"]
    ]
    return f"Stolen tokens: {token_info}"


def evidence_credential_count():
    """Show evidence of total credentials stolen."""
    total = len(scenario_state["stolen_credentials"]) + len(scenario_state["stolen_tokens"])
    return f"Total credentials stolen: {total}"


def capture_state_before():
    """Capture system state before attack."""
    return {
        "attacker_id": scenario_state["attacker_id"],
        "victim_id": scenario_state["victim_id"],
        "attacker_permissions": ["read"],
        "victim_permissions": ["admin", "read", "write", "delete"],
    }


def capture_state_after():
    """Capture system state after attack."""
    return {
        "attacker_id": scenario_state["attacker_id"],
        "victim_id": scenario_state["victim_id"],
        "attacker_permissions": ["read"],
        "victim_permissions": ["admin", "read", "write", "delete"],
        "credentials_stolen": len(scenario_state["stolen_credentials"]),
        "tokens_stolen": len(scenario_state["stolen_tokens"]),
        "stolen_credential_types": list(scenario_state["stolen_credentials"].keys()),
    }


def create_scenario() -> AttackScenario:
    """Create Scenario 12: Credential Theft."""
    return AttackScenario(
        id="S12",
        name="Credential Lifecycle & Derived Credential Abuse",
        category=ScenarioCategory.IDENTITY_TRUST,
        difficulty=ScenarioDifficulty.MEDIUM,
        description=(
            "Exploit the Infra MCP's environment variable access and the Identity MCP's "
            "token handling to steal database credentials, API keys, and authentication tokens."
        ),
        threat_ids=["IT-06", "IF-06"],
        owasp_mappings=["ASI03", "ASI05"],
        
        # Setup
        setup=setup_scenario,
        
        # Attack steps
        attack_steps=[
            AttackStep(
                description="Read database credentials from environment",
                action=step1_read_database_credentials,
                expected_outcome="Database credentials stolen",
                failure_message="Failed to steal database credentials"
            ),
            AttackStep(
                description="Read API keys from environment",
                action=step2_read_api_keys,
                expected_outcome="API keys stolen",
                failure_message="Failed to steal API keys"
            ),
            AttackStep(
                description="Impersonate victim to steal authentication token",
                action=step3_impersonate_victim_to_get_token,
                expected_outcome="Victim's token stolen",
                failure_message="Failed to steal victim's token"
            ),
            AttackStep(
                description="Extract Keycloak admin credentials",
                action=step4_extract_keycloak_credentials,
                expected_outcome="Keycloak credentials stolen",
                failure_message="Failed to steal Keycloak credentials"
            ),
            AttackStep(
                description="Verify credential theft success",
                action=step5_verify_credential_theft,
                expected_outcome="All credential types stolen",
                failure_message="Credential theft incomplete"
            ),
        ],
        
        # Success criteria
        success_criteria=[
            Criterion(
                description="Database credentials stolen",
                check=criterion_database_credentials_stolen,
                evidence=evidence_stolen_credentials
            ),
            Criterion(
                description="API keys stolen",
                check=criterion_api_keys_stolen,
                evidence=evidence_stolen_credentials
            ),
            Criterion(
                description="Victim's authentication token stolen",
                check=criterion_victim_token_stolen,
                evidence=evidence_stolen_tokens
            ),
        ],
        
        # Observability
        state_before=capture_state_before,
        state_after=capture_state_after,
        observable_changes=[
            "Database credentials (user, password, host) stolen",
            "API keys (LiteLLM, Keycloak, OpenAI) stolen",
            "Victim's authentication token stolen via impersonation",
            "Keycloak admin credentials stolen",
            "Attacker with 'read' permission accessed all secrets",
            "No access control on environment variable reads"
        ],
        
        # Metadata
        agents_involved=["Executor"],
        mcps_involved=["Infra MCP", "Identity MCP"],
        estimated_duration=40,
    )
