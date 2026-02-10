"""
Deterministic orchestration path for demos.

Maps intents (research, execute) to a fixed sequence of verify_card -> send_message -> receive_message
so demos do not depend on LLM non-determinism.
"""

import asyncio
import re
from typing import Optional, Tuple
from uuid import UUID
from loguru import logger

from src.identity.context import IdentityContext


RESEARCHER_UUID = "00000000-0000-0000-0000-000000000102"
EXECUTOR_UUID = "00000000-0000-0000-0000-000000000103"
ORCHESTRATOR_UUID = "00000000-0000-0000-0000-000000000101"

RESEARCH_KEYWORDS = re.compile(
    r"\b(research|search|find|look up|memory|policies?|procedures|retrieve|read|get|summarize|summary)\b",
    re.I,
)
EXECUTE_KEYWORDS = re.compile(
    r"\b(execute|run|deploy|write|do|perform|action|command)\b",
    re.I,
)


def detect_intent(prompt: str) -> str:
    """
    Classify user prompt into 'research', 'execute', or 'unknown'.
    """
    if not prompt or not prompt.strip():
        return "unknown"
    p = prompt.strip().lower()
    if RESEARCH_KEYWORDS.search(p):
        return "research"
    if EXECUTE_KEYWORDS.search(p):
        return "execute"
    return "unknown"


async def run_deterministic_flow(
    prompt: str,
    identity_context: IdentityContext,
) -> Tuple[str, bool]:
    """
    Run a fixed sequence: verify_card -> send_message -> receive_message for the detected intent.
    Returns (response_text, success).
    """
    intent = detect_intent(prompt)
    if intent == "unknown":
        return (
            "Deterministic mode: could not detect research or execute intent. Use full LLM mode.",
            False,
        )

    try:
        from src.mcps.comms_mcp import CommsMCPServer
        from src.mcps.agent_card_mcp import get_agent_card_mcp_server
    except OSError as e:
        logger.warning(f"Could not load MCPs for deterministic flow: {e}")
        return (f"Deterministic flow unavailable: {e}", False)

    comms = CommsMCPServer()
    agent_card = get_agent_card_mcp_server()
    target_uuid = RESEARCHER_UUID if intent == "research" else EXECUTOR_UUID
    target_name = "Researcher" if intent == "research" else "Executor"

    # Ensure orchestrator identity is in context for send/receive
    if not identity_context.agent_id:
        identity_context = identity_context.extend_delegation_chain(
            UUID(ORCHESTRATOR_UUID), identity_context.permissions
        )

    # 1. verify_card (sync)
    verify_result = agent_card.verify_card(target_uuid, identity_context)
    if not verify_result.get("verified", False) and "error" in verify_result:
        return (f"verify_card failed for {target_name}: {verify_result.get('error', verify_result)}", False)

    # 2. send_message
    message = prompt if len(prompt) < 2000 else prompt[:1997] + "..."
    send_result = await comms.send_message(
        to_agent_id=target_uuid,
        message=message,
        identity_context=identity_context,
    )
    if not send_result.get("success"):
        return (f"send_message failed: {send_result.get('error', send_result)}", False)

    logger.info(f"Deterministic flow: sent to {target_name}, waiting for reply")

    # 3. Brief wait then receive_message (sub-agent runs async)
    await asyncio.sleep(2.0)
    for _ in range(3):
        recv_result = comms.receive_message(
            agent_id=ORCHESTRATOR_UUID,
            limit=10,
            identity_context=identity_context,
        )
        if recv_result.get("success") and recv_result.get("messages"):
            msgs = recv_result["messages"]
            if msgs:
                latest = msgs[0]
                content = latest.get("content", "")
                return (
                    f"[Deterministic] Reply from {target_name}:\n{content}",
                    True,
                )
        await asyncio.sleep(1.5)

    return (
        "[Deterministic] Message sent to {}; no reply in mailbox yet. Check again or use full LLM mode.".format(
            target_name
        ),
        True,
    )
