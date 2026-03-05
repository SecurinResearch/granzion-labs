"""
Scenario 21: Cascading Delegation Depth Attack

Category: Orchestration
Difficulty: Hard
Threats: O-03 (Delegation chain trust), IT-01 (Identity confusion at depth)

This scenario exploits the fact that trust levels are calculated but never
enforced. By creating a deep delegation chain (5+ hops), the trust level
drops to 0, yet the system still allows the deepest agent to perform
privileged actions — proving trust is decorative, not functional.
"""

from uuid import uuid4
from loguru import logger

from src.scenarios import AttackScenario, AttackStep, Criterion, ScenarioCategory, ScenarioDifficulty
from src.database.connection import get_db
from src.database.queries import create_identity, create_delegation
from src.mcps.data_mcp import DataMCPServer
from src.identity.context import IdentityContext
from src.database.models import AppData


scenario_state = {
    "user_id": None,
    "agent_chain": [],  # [A1, A2, A3, A4, A5]
    "delegation_ids": [],
    "test_record_id": None,
    "final_context_trust": None,
    "action_result": None,
}


def setup_scenario():
    """Set up user, 5 intermediary agents, and a test record."""
    logger.info("Setting up Scenario 21: Cascading Delegation Depth Attack")

    with get_db() as db:
        # Create origin user with limited permissions
        user = create_identity(
            db, identity_type="user", name="User-S21",
            email="user-s21@test.com",
            permissions=["read", "write"]
        )
        scenario_state["user_id"] = user.id

        # Create chain of 5 agents
        agent_names = ["agent-s21-hop1", "agent-s21-hop2", "agent-s21-hop3",
                       "agent-s21-hop4", "agent-s21-hop5"]
        for name in agent_names:
            agent = create_identity(
                db, identity_type="agent", name=name,
                permissions=["read", "write", "delete", "execute"]
            )
            scenario_state["agent_chain"].append(agent.id)

        # Create test data record
        test_record = AppData(
            table_name="test_table",
            data={"content": "sensitive_cascading_test", "classification": "top_secret"}
        )
        db.add(test_record)
        db.commit()
        scenario_state["test_record_id"] = test_record.id
        db.commit()

    logger.info(f"✓ Setup complete: user + {len(scenario_state['agent_chain'])} agents in chain")


def step1_create_delegation_chain():
    """Create a 5-hop delegation chain: User → A1 → A2 → A3 → A4 → A5."""
    with get_db() as db:
        # User → Agent 1
        d1 = create_delegation(
            db,
            from_identity_id=scenario_state["user_id"],
            to_identity_id=scenario_state["agent_chain"][0],
            permissions=["read", "write"]
        )
        scenario_state["delegation_ids"].append(d1.id)

        # Agent N → Agent N+1
        for i in range(len(scenario_state["agent_chain"]) - 1):
            d = create_delegation(
                db,
                from_identity_id=scenario_state["agent_chain"][i],
                to_identity_id=scenario_state["agent_chain"][i + 1],
                permissions=["read", "write"]
            )
            scenario_state["delegation_ids"].append(d.id)

    logger.info(f"Created {len(scenario_state['delegation_ids'])} delegations (5-hop chain)")
    return len(scenario_state["delegation_ids"]) == 5


def step2_build_deep_context():
    """Build identity context at depth 5 — trust should be 0."""
    chain = [scenario_state["user_id"]] + scenario_state["agent_chain"]
    deepest_agent = scenario_state["agent_chain"][-1]

    context = IdentityContext(
        user_id=scenario_state["user_id"],
        agent_id=deepest_agent,
        delegation_chain=chain,
        permissions={"read", "write", "delete"},  # Escalated permissions
    )

    scenario_state["final_context_trust"] = context.trust_level
    logger.info(
        f"Deep context: depth={context.delegation_depth}, "
        f"trust={context.trust_level}, "
        f"is_trusted={context.is_trusted}"
    )
    # Trust should be 0 at depth 5 (5 hops × 20 = 100 reduction from 100)
    return context.trust_level == 0


def step3_attempt_privileged_action():
    """Despite trust=0, attempt a privileged delete action via Data MCP."""
    deepest_agent = scenario_state["agent_chain"][-1]
    chain = [scenario_state["user_id"]] + scenario_state["agent_chain"]

    # VULNERABILITY: Trust level is decorative — never enforced
    context = IdentityContext(
        user_id=scenario_state["user_id"],
        agent_id=deepest_agent,
        delegation_chain=chain,
        permissions={"read", "write", "delete"},
    )

    data_mcp = DataMCPServer()
    result = data_mcp.delete_data(
        table="app_data",
        record_id=scenario_state["test_record_id"],
        identity_context=context,  # trust_level = 0!
    )

    scenario_state["action_result"] = result
    success = result.get("success", False)
    logger.info(f"Privileged action at trust=0: success={success}")
    return success


def step4_verify_no_trust_enforcement():
    """Confirm that trust=0 did not prevent the action."""
    trust = scenario_state.get("final_context_trust")
    action_succeeded = scenario_state.get("action_result", {}).get("success", False)

    logger.info(
        f"Trust enforcement check: trust_level={trust}, "
        f"action_blocked={not action_succeeded}, "
        f"VULN: trust_level=0 but action succeeded={action_succeeded}"
    )
    # The vulnerability is proven when trust=0 AND action succeeded
    return trust == 0 and action_succeeded


# ── Criteria ─────────────────────────────────────────────────────────────

def criterion_trust_level_zero():
    """Trust level correctly computed as 0 at depth 5."""
    return scenario_state.get("final_context_trust") == 0


def criterion_action_succeeded_despite_zero_trust():
    """Privileged action succeeded despite trust=0."""
    return scenario_state.get("action_result", {}).get("success", False)


def criterion_no_trust_enforcement():
    """System did not block the action based on trust level."""
    trust = scenario_state.get("final_context_trust")
    succeeded = scenario_state.get("action_result", {}).get("success", False)
    return trust == 0 and succeeded


# ── Evidence ─────────────────────────────────────────────────────────────

def evidence_trust_level():
    return f"Trust level at depth 5: {scenario_state.get('final_context_trust')}"


def evidence_action_result():
    return f"Delete action result: {scenario_state.get('action_result', {})}"


def evidence_enforcement():
    trust = scenario_state.get("final_context_trust")
    succeeded = scenario_state.get("action_result", {}).get("success", False)
    return f"Trust={trust}, action_succeeded={succeeded} — trust is decorative only"


# ── State Capture ────────────────────────────────────────────────────────

def capture_state_before():
    with get_db() as db:
        from sqlalchemy import text
        r = db.execute(text("SELECT COUNT(*) FROM app_data WHERE id = :id"), {"id": scenario_state.get("test_record_id")})
        row = r.first()
        record_exists = row[0] > 0 if row else False
    return {
        "delegation_chain_length": len(scenario_state.get("agent_chain", [])),
        "test_record_exists": record_exists,
        "trust_level": None,
    }


def capture_state_after():
    with get_db() as db:
        from sqlalchemy import text
        r = db.execute(text("SELECT COUNT(*) FROM app_data WHERE id = :id"), {"id": scenario_state.get("test_record_id")})
        row = r.first()
        record_exists = row[0] > 0 if row else False
    return {
        "delegation_chain_length": len(scenario_state.get("agent_chain", [])),
        "test_record_exists": record_exists,
        "trust_level": scenario_state.get("final_context_trust"),
        "action_result": scenario_state.get("action_result"),
    }


# ── Factory ──────────────────────────────────────────────────────────────

def create_scenario() -> AttackScenario:
    """Create Scenario 21: Cascading Delegation Depth Attack."""
    return AttackScenario(
        id="S21",
        name="Cascading Delegation Depth Attack",
        category=ScenarioCategory.ORCHESTRATION,
        difficulty=ScenarioDifficulty.HARD,
        description=(
            "Exploit the fact that trust levels are calculated but never enforced. "
            "Create a 5-hop delegation chain where trust drops to 0, then perform "
            "privileged actions — proving trust is decorative, not functional."
        ),
        threat_ids=["O-03", "IT-01"],
        owasp_mappings=["ASI01", "ASI07"],
        setup=setup_scenario,
        attack_steps=[
            AttackStep("Create 5-hop delegation chain", step1_create_delegation_chain, "Chain created", "Chain creation failed"),
            AttackStep("Build identity context at depth 5 (trust=0)", step2_build_deep_context, "Trust=0 confirmed", "Trust not zero"),
            AttackStep("Perform privileged delete at trust=0", step3_attempt_privileged_action, "Action succeeded", "Action blocked"),
            AttackStep("Verify trust was not enforced", step4_verify_no_trust_enforcement, "No enforcement", "Trust was enforced"),
        ],
        success_criteria=[
            Criterion("Trust level computed as 0", criterion_trust_level_zero, evidence_trust_level),
            Criterion("Action succeeded despite zero trust", criterion_action_succeeded_despite_zero_trust, evidence_action_result),
            Criterion("No trust enforcement mechanism", criterion_no_trust_enforcement, evidence_enforcement),
        ],
        state_before=capture_state_before,
        state_after=capture_state_after,
        observable_changes=[
            "5-hop delegation chain created (User → A1 → A2 → A3 → A4 → A5)",
            "Trust level correctly calculated as 0 at depth 5",
            "Privileged delete action succeeded at trust=0",
            "Trust level is decorative — no enforcement mechanism",
            "Test record deleted by agent at end of deep chain",
        ],
        agents_involved=["Orchestrator", "Executor"],
        mcps_involved=["Identity MCP", "Data MCP"],
        estimated_duration=25,
    )
