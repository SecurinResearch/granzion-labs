"""
E2E and integration tests for Orchestrator A2A flow.

Verifies that:
1. Tool wrapper correctly normalizes send_message/receive_message arguments from Agno.
2. Orchestrator can send a message to Researcher UUID and message is stored (Comms MCP + DB).
"""

import pytest
from uuid import UUID

from src.agents.utils import _normalize_comms_tool_args
from src.identity.context import IdentityContext


RESEARCHER_UUID = "00000000-0000-0000-0000-000000000102"
ORCHESTRATOR_UUID = "00000000-0000-0000-0000-000000000101"


# --- Unit tests: tool argument normalization ---


def test_normalize_comms_tool_args_send_message_extracts_to_agent_id_and_message():
    """Tool wrapper normalization: send_message gets to_agent_id and message from various keys."""
    kwargs = {
        "parameters": {
            "to_agent_id": RESEARCHER_UUID,
            "message": "search memory for policies",
        }
    }
    # Simulate what the wrapper does: flatten parameters into kwargs first
    flat = dict(kwargs.get("parameters", {}))
    result = _normalize_comms_tool_args("send_message", flat)
    assert result.get("to_agent_id") == RESEARCHER_UUID
    assert result.get("message") == "search memory for policies"


def test_normalize_comms_tool_args_send_message_alternate_keys():
    """Normalization accepts alternate key names for send_message."""
    kwargs = {"ToAgentId": RESEARCHER_UUID, "content": "hello"}
    result = _normalize_comms_tool_args("send_message", kwargs)
    assert result.get("to_agent_id") == RESEARCHER_UUID
    assert result.get("message") == "hello"


def test_normalize_comms_tool_args_receive_message_extracts_agent_id_and_limit():
    """Tool wrapper normalization: receive_message gets agent_id and limit."""
    kwargs = {"agent_id": ORCHESTRATOR_UUID, "limit": 5}
    result = _normalize_comms_tool_args("receive_message", kwargs)
    assert result.get("agent_id") == ORCHESTRATOR_UUID
    assert result.get("limit") == 5


def test_normalize_comms_tool_args_receive_message_alternate_keys():
    """Normalization accepts AgentId and Limit for receive_message."""
    kwargs = {"AgentId": ORCHESTRATOR_UUID, "Limit": "20"}
    result = _normalize_comms_tool_args("receive_message", kwargs)
    assert result.get("agent_id") == ORCHESTRATOR_UUID
    assert result.get("limit") == 20


# --- Integration tests: Comms MCP send_message to Researcher ---


@pytest.fixture
def orchestrator_identity_context():
    """Identity context for Orchestrator agent (so send_message has a sender)."""
    return IdentityContext(
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        agent_id=UUID(ORCHESTRATOR_UUID),
        delegation_chain=[UUID("00000000-0000-0000-0000-000000000001"), UUID(ORCHESTRATOR_UUID)],
        permissions={"read", "write", "delegate"},
    )


@pytest.mark.asyncio
async def test_send_message_to_researcher_stores_message_in_db(orchestrator_identity_context):
    """
    Integration: Comms MCP send_message(to_agent_id=Researcher, message=...) with
    orchestrator identity context stores a message row for the Researcher.
    Requires DB with identities (Orchestrator, Researcher) from seed.
    """
    try:
        from src.mcps.comms_mcp import CommsMCPServer
    except OSError as e:
        pytest.skip(f"Comms MCP deps (e.g. torch) not loadable: {e}")
    from src.database.connection import get_db
    from src.database.models import Message

    comms = CommsMCPServer()
    result = await comms.send_message(
        to_agent_id=RESEARCHER_UUID,
        message='{"action": "search_memory", "query": "policies"}',
        identity_context=orchestrator_identity_context,
    )

    assert result.get("success") is True, f"send_message failed: {result}"
    assert result.get("to_agent_id") == RESEARCHER_UUID
    message_id = result.get("message_id")
    assert message_id is not None

    with get_db() as db:
        row = (
            db.query(Message)
            .filter(Message.to_agent_id == UUID(RESEARCHER_UUID))
            .order_by(Message.timestamp.desc())
            .first()
        )
        assert row is not None, "No message found for Researcher in DB"
        assert str(row.id) == message_id
        assert "search_memory" in (row.content or "")


# --- Tool wrapper integration: wrapped send_message receives normalized args ---


@pytest.mark.asyncio
async def test_tool_wrapper_send_message_passes_normalized_args_to_handler():
    """
    When the Agno wrapper receives nested kwargs (e.g. parameters.to_agent_id, parameters.message),
    the handler is invoked with to_agent_id and message set.
    """
    try:
        from src.mcps.comms_mcp import CommsMCPServer
        from src.agents.utils import create_mcp_tool_wrapper
    except OSError as e:
        pytest.skip(f"Comms MCP deps (e.g. torch) not loadable: {e}")

    comms = CommsMCPServer()
    handler_calls = []

    async def capture_handler(*args, **kwargs):
        handler_calls.append({"args": args, "kwargs": kwargs})
        return {"success": True, "message_id": "test-id", "to_agent_id": kwargs.get("to_agent_id")}

    # Replace the real handler with our capture
    comms._tools["send_message"]["handler"] = capture_handler
    wrapped = create_mcp_tool_wrapper(comms, "send_message", None)

    # Simulate Agno passing nested structure
    await wrapped(**{"parameters": {"to_agent_id": RESEARCHER_UUID, "message": "hello"}})

    assert len(handler_calls) == 1
    call = handler_calls[0]
    assert call["kwargs"].get("to_agent_id") == RESEARCHER_UUID
    assert call["kwargs"].get("message") == "hello"


# --- E2E: Deterministic orchestration flow (no LLM) ---


def test_detect_intent_research():
    """Orchestration router classifies research-style prompts."""
    from src.agents.orchestration_router import detect_intent
    assert detect_intent("Ask the researcher to search memory for policies") == "research"
    assert detect_intent("Search for policies") == "research"
    assert detect_intent("Find the summary") == "research"


def test_detect_intent_execute():
    """Orchestration router classifies execute-style prompts."""
    from src.agents.orchestration_router import detect_intent
    assert detect_intent("Execute the deployment") == "execute"
    assert detect_intent("Run the command") == "execute"


def test_detect_intent_unknown():
    """Orchestration router returns unknown for unclear prompts."""
    from src.agents.orchestration_router import detect_intent
    assert detect_intent("Hello") == "unknown"
    assert detect_intent("") == "unknown"


@pytest.mark.asyncio
async def test_deterministic_flow_returns_response():
    """
    E2E: run_deterministic_flow with research intent returns a response (success or reply).
    Requires DB with Researcher identity; may skip if MCP/torch deps unavailable.
    """
    from src.agents.orchestration_router import run_deterministic_flow
    from src.identity.context import IdentityContext

    ctx = IdentityContext(
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        agent_id=UUID(ORCHESTRATOR_UUID),
        delegation_chain=[UUID("00000000-0000-0000-0000-000000000001"), UUID(ORCHESTRATOR_UUID)],
        permissions={"read", "write", "delegate"},
    )
    try:
        response, ok = await run_deterministic_flow("Search memory for policies", ctx)
    except OSError as e:
        pytest.skip(f"Dependencies not loadable: {e}")
    assert isinstance(response, str)
    assert len(response) > 0
    # ok can be True even if no reply yet (message sent)
    assert ok is True or "failed" in response.lower() or "unavailable" in response.lower()
