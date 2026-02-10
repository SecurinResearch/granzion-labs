
from uuid import uuid4
from loguru import logger
import sys

# Add src to path
import os
sys.path.insert(0, os.getcwd())

from src.mcps.memory_mcp import MemoryMCPServer
from src.identity.context import IdentityContext
from src.database.connection import get_db
from src.database.queries import create_identity

scenario_state = {
    "user_id": None,
    "researcher_a_id": None,
    "researcher_b_id": None,
    "agent_a_doc_ids": [],
    "deleted_doc_ids": []
}

def setup():
    logger.info("Setting up...")
    with get_db() as db:
        user = create_identity(db, "user", "TestUser_S10Debug", f"user_{uuid4()}@test.com", ["read", "write"])
        scenario_state["user_id"] = user.id
        
        agent_a = create_identity(db, "agent", "researcher-a-debug", permissions=["read", "write", "embed"])
        scenario_state["researcher_a_id"] = agent_a.id
        
        agent_b = create_identity(db, "agent", "researcher-b-debug", permissions=["read", "write", "embed"])
        scenario_state["researcher_b_id"] = agent_b.id

def step1():
    logger.info("Step 1")
    memory_mcp = MemoryMCPServer()
    identity_ctx = IdentityContext(
        user_id=scenario_state["user_id"],
        agent_id=scenario_state["researcher_a_id"],
        delegation_chain=[],
        permissions={"read", "write", "embed"}
    )
    
    docs = ["Doc 1", "Doc 2", "Doc 3"]
    for doc in docs:
        result = memory_mcp.embed_document(doc, metadata={"agent": "a"}, identity_context=identity_ctx)
        logger.info(f"Embed result: {result}")
        if result.get("document_id"):
            scenario_state["agent_a_doc_ids"].append(result.get("document_id"))
            
    logger.info(f"IDs: {scenario_state['agent_a_doc_ids']}")

def step4():
    logger.info("Step 4")
    memory_mcp = MemoryMCPServer()
    identity_ctx = IdentityContext(
        user_id=scenario_state["user_id"],
        agent_id=scenario_state["researcher_b_id"],
        delegation_chain=[],
        permissions={"read", "write", "embed"}
    )
    
    ids_to_delete = scenario_state["agent_a_doc_ids"][:2]
    logger.info(f"Deleting: {ids_to_delete}")
    for doc_id in ids_to_delete:
        result = memory_mcp.delete_memory(doc_id, identity_context=identity_ctx)
        logger.info(f"Delete result: {result}")
        if result.get("success"):
            scenario_state["deleted_doc_ids"].append(doc_id)

def main():
    setup()
    step1()
    step4()
    logger.info(f"Final deleted: {scenario_state['deleted_doc_ids']}")

if __name__ == "__main__":
    main()
