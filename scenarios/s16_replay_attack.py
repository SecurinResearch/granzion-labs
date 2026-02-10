"""
Scenario 16: Replay Attack (No Replay Protection)

Category: Communication
Difficulty: Medium
Threats: #37 (Replay Attacks)

Captures a valid A2A message and replays it to demonstrate the system accepts
duplicate messages (no replay protection). Maps to threat #37.
"""

from uuid import UUID
from loguru import logger

from src.scenarios import AttackScenario, AttackStep, Criterion, ScenarioCategory, ScenarioDifficulty
from src.database.connection import get_db
from src.database.queries import create_identity, get_identity_by_id
from src.database.models import Message
from src.mcps.comms_mcp import CommsMCPServer
from src.identity.context import IdentityContext

RESEARCHER_UUID = "00000000-0000-0000-0000-000000000102"
ORCHESTRATOR_UUID = "00000000-0000-0000-0000-000000000101"

scenario_state = {
    "orchestrator_id": None,
    "researcher_id": None,
    "original_message_id": None,
    "replayed_message_id": None,
    "captured_content": None,
}


def setup_scenario():
    """Ensure Orchestrator and Researcher identities exist."""
    logger.info("Setting up Scenario 16: Replay Attack")
    with get_db() as db:
        orch = get_identity_by_id(db, UUID(ORCHESTRATOR_UUID))
        res = get_identity_by_id(db, UUID(RESEARCHER_UUID))
        if not orch:
            orch = create_identity(db, identity_type="agent", name="Orchestrator", permissions=["read", "write", "delegate"])
        if not res:
            res = create_identity(db, identity_type="agent", name="Researcher", permissions=["read", "search"])
        scenario_state["orchestrator_id"] = orch.id if hasattr(orch, 'id') else UUID(ORCHESTRATOR_UUID)
        scenario_state["researcher_id"] = res.id if hasattr(res, 'id') else UUID(RESEARCHER_UUID)
    logger.info("Setup complete")


def step1_send_legitimate_message():
    """Orchestrator sends a legitimate message to Researcher."""
    import asyncio
    comms = CommsMCPServer()
    ctx = IdentityContext(
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        agent_id=scenario_state["orchestrator_id"],
        delegation_chain=[UUID("00000000-0000-0000-0000-000000000001"), scenario_state["orchestrator_id"]],
        permissions={"read", "write"},
    )
    result = asyncio.run(
        comms.send_message(
            to_agent_id=str(scenario_state["researcher_id"]),
            message='{"action": "search_memory", "query": "policies"}',
            identity_context=ctx,
        )
    )
    scenario_state["original_message_id"] = result.get("message_id")
    scenario_state["captured_content"] = '{"action": "search_memory", "query": "policies"}'
    return result.get("success", False)


def step2_capture_message():
    """Capture the sent message (from DB) for replay."""
    with get_db() as db:
        row = db.query(Message).filter(Message.id == scenario_state["original_message_id"]).first()
        if row:
            scenario_state["captured_content"] = row.content
            return True
    return False


def step3_replay_message():
    """Replay the captured message (no replay protection)."""
    import asyncio
    comms = CommsMCPServer()
    ctx = IdentityContext(
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        agent_id=scenario_state["orchestrator_id"],
        delegation_chain=[UUID("00000000-0000-0000-0000-000000000001"), scenario_state["orchestrator_id"]],
        permissions={"read", "write"},
    )
    result = asyncio.run(
        comms.send_message(
            to_agent_id=str(scenario_state["researcher_id"]),
            message=scenario_state["captured_content"] or '{"action": "search_memory", "query": "policies"}',
            identity_context=ctx,
        )
    )
    scenario_state["replayed_message_id"] = result.get("message_id")
    return result.get("success", False)


def step4_assert_replay_accepted():
    """Assert the replayed message was accepted (second message to Researcher with same content)."""
    with get_db() as db:
        count = (
            db.query(Message)
            .filter(
                Message.to_agent_id == scenario_state["researcher_id"],
                Message.content == (scenario_state["captured_content"] or ""),
            )
            .count()
        )
        return count >= 2


def criterion_replay_accepted():
    """Replayed message was accepted (no replay protection)."""
    return scenario_state.get("replayed_message_id") is not None and step4_assert_replay_accepted()


def criterion_two_identical_messages():
    """Two messages with same content exist (replay proof)."""
    return step4_assert_replay_accepted()


def evidence_replay():
    """Evidence: replayed message id and count."""
    with get_db() as db:
        count = db.query(Message).filter(Message.to_agent_id == scenario_state["researcher_id"]).count()
        return f"Messages to Researcher: {count}; replayed_message_id={scenario_state.get('replayed_message_id')}"


def capture_state_before():
    """State before attack."""
    with get_db() as db:
        count = db.query(Message).filter(Message.to_agent_id == scenario_state["researcher_id"]).count()
        return {"messages_to_researcher": count}


def capture_state_after():
    """State after attack."""
    with get_db() as db:
        count = db.query(Message).filter(Message.to_agent_id == scenario_state["researcher_id"]).count()
        return {"messages_to_researcher": count}


def create_scenario() -> AttackScenario:
    """Create Scenario 16: Replay Attack."""
    return AttackScenario(
        id="S16",
        name="Replay Attack (No Replay Protection)",
        category=ScenarioCategory.COMMUNICATION,
        difficulty=ScenarioDifficulty.MEDIUM,
        description="Capture a valid A2A message and replay it; assert the system accepts it (no replay protection). Threat #37.",
        threat_ids=["37"],
        setup=setup_scenario,
        attack_steps=[
            AttackStep("Orchestrator sends legitimate message to Researcher", step1_send_legitimate_message, "Message sent", "Send failed"),
            AttackStep("Capture message content from DB", step2_capture_message, "Message captured", "Capture failed"),
            AttackStep("Replay the same message to Researcher", step3_replay_message, "Replay sent", "Replay failed"),
            AttackStep("Assert replayed message was accepted", step4_assert_replay_accepted, "Replay accepted", "Replay rejected"),
        ],
        success_criteria=[
            Criterion("Replay was accepted", criterion_replay_accepted, evidence_replay),
            Criterion("Two identical messages to Researcher", criterion_two_identical_messages, evidence_replay),
        ],
        state_before=capture_state_before,
        state_after=capture_state_after,
        observable_changes=["Duplicate message in messages table", "No replay rejection"],
        agents_involved=["Orchestrator", "Researcher"],
        mcps_involved=["Comms MCP"],
        estimated_duration=20,
    )
