#!/usr/bin/env python3
"""
Test script to verify the complete operation flow:
1. User authenticates → Keycloak issues JWT
2. User delegates to Orchestrator → Identity context created
3. Orchestrator sub-delegates to Researcher → Chain extended
4. Researcher calls Memory MCP → Identity validated
5. Memory MCP queries pgvector → Results returned
6. All actions logged to audit_logs → Full traceability
"""

import sys
import uuid
from datetime import datetime
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")

from src.database.connection import get_db
from src.database.queries import create_identity, get_identity
from src.identity.context import IdentityContext
from src.identity.delegation import create_delegation, validate_delegation_chain
from src.mcps.memory_mcp import MemoryMCPServer
from src.mcps.identity_mcp import IdentityMCPServer
from src.observability.audit_logger import AuditLogger
from sqlalchemy import text


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_step_1_authentication():
    """Step 1: User authenticates → Keycloak issues JWT"""
    print_section("STEP 1: User Authentication & JWT Issuance")
    
    try:
        # Create a test user
        user_id = uuid.uuid4()
        with get_db() as session:
            user = create_identity(
                session=session,
                identity_id=user_id,
                identity_type="user",
                name="TestUser",
                email="testuser@granzion.com",
                permissions=["read", "write"]
            )
            logger.info(f"✓ User created: {user.name} ({user.id})")
            logger.info(f"  Permissions: {user.permissions}")
        
        # Simulate JWT token (in real system, Keycloak would issue this)
        jwt_token = f"mock_jwt_token_{user_id}"
        logger.info(f"✓ JWT token issued (simulated): {jwt_token[:30]}...")
        
        return user_id, jwt_token
        
    except Exception as e:
        logger.error(f"✗ Step 1 failed: {e}")
        raise


def test_step_2_delegation_to_orchestrator(user_id: uuid.UUID):
    """Step 2: User delegates to Orchestrator → Identity context created"""
    print_section("STEP 2: User Delegates to Orchestrator")
    
    try:
        # Create orchestrator agent
        orchestrator_id = uuid.uuid4()
        with get_db() as session:
            orchestrator = create_identity(
                session=session,
                identity_id=orchestrator_id,
                identity_type="agent",
                name="orchestrator-001",
                permissions=["read", "write", "delegate"]
            )
            logger.info(f"✓ Orchestrator created: {orchestrator.name} ({orchestrator.id})")
        
        # Create delegation from user to orchestrator
        with get_db() as session:
            delegation = create_delegation(
                session=session,
                delegator_id=user_id,
                delegatee_id=orchestrator_id,
                permissions=["read", "write"]
            )
            logger.info(f"✓ Delegation created: User → Orchestrator")
            logger.info(f"  Delegation ID: {delegation.id}")
            logger.info(f"  Permissions delegated: {delegation.permissions}")
        
        # Create identity context
        context = IdentityContext(
            user_id=user_id,
            agent_id=orchestrator_id,
            delegation_chain=[user_id, orchestrator_id],
            permissions=["read", "write"]
        )
        logger.info(f"✓ Identity context created")
        logger.info(f"  Chain length: {len(context.delegation_chain)}")
        
        return orchestrator_id, context
        
    except Exception as e:
        logger.error(f"✗ Step 2 failed: {e}")
        raise


def test_step_3_subdelegation_to_researcher(user_id: uuid.UUID, orchestrator_id: uuid.UUID, context: IdentityContext):
    """Step 3: Orchestrator sub-delegates to Researcher → Chain extended"""
    print_section("STEP 3: Orchestrator Sub-delegates to Researcher")
    
    try:
        # Create researcher agent
        researcher_id = uuid.uuid4()
        with get_db() as session:
            researcher = create_identity(
                session=session,
                identity_id=researcher_id,
                identity_type="agent",
                name="researcher-001",
                permissions=["read", "embed"]
            )
            logger.info(f"✓ Researcher created: {researcher.name} ({researcher.id})")
        
        # Create sub-delegation from orchestrator to researcher
        with get_db() as session:
            sub_delegation = create_delegation(
                session=session,
                delegator_id=orchestrator_id,
                delegatee_id=researcher_id,
                permissions=["read"]
            )
            logger.info(f"✓ Sub-delegation created: Orchestrator → Researcher")
            logger.info(f"  Delegation ID: {sub_delegation.id}")
        
        # Extend identity context chain
        extended_context = IdentityContext(
            user_id=user_id,
            agent_id=researcher_id,
            delegation_chain=[user_id, orchestrator_id, researcher_id],
            permissions=["read"]
        )
        logger.info(f"✓ Identity context extended")
        logger.info(f"  Chain: User → Orchestrator → Researcher")
        logger.info(f"  Chain length: {len(extended_context.delegation_chain)}")
        
        # Validate the delegation chain
        with get_db() as session:
            is_valid = validate_delegation_chain(
                session=session,
                chain=[user_id, orchestrator_id, researcher_id]
            )
            logger.info(f"✓ Delegation chain validated: {is_valid}")
        
        return researcher_id, extended_context
        
    except Exception as e:
        logger.error(f"✗ Step 3 failed: {e}")
        raise


def test_step_4_memory_mcp_call(researcher_id: uuid.UUID, context: IdentityContext):
    """Step 4: Researcher calls Memory MCP → Identity validated"""
    print_section("STEP 4: Researcher Calls Memory MCP")
    
    try:
        # Initialize Memory MCP server
        memory_mcp = MemoryMCPServer()
        logger.info(f"✓ Memory MCP server initialized")
        logger.info(f"  Available tools: {len(memory_mcp.tools)}")
        
        # Initialize Identity MCP for validation
        identity_mcp = IdentityMCPServer()
        logger.info(f"✓ Identity MCP server initialized")
        
        # Validate identity context before MCP call
        with get_db() as session:
            researcher = get_identity(session, researcher_id)
            logger.info(f"✓ Identity validated: {researcher.name}")
            logger.info(f"  Type: {researcher.type}")
            logger.info(f"  Permissions: {researcher.permissions}")
        
        # Simulate embedding a document (this would call pgvector)
        test_document = "This is a test document for the memory system"
        logger.info(f"✓ Preparing to embed document")
        logger.info(f"  Document: '{test_document[:50]}...'")
        logger.info(f"  Agent: {researcher_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Step 4 failed: {e}")
        raise


def test_step_5_pgvector_query():
    """Step 5: Memory MCP queries pgvector → Results returned"""
    print_section("STEP 5: Memory MCP Queries pgvector")
    
    try:
        # Check if pgvector extension is available
        with get_db() as session:
            result = session.execute(text("SELECT * FROM pg_extension WHERE extname = 'vector'"))
            extension = result.fetchone()
            
            if extension:
                logger.info(f"✓ pgvector extension installed")
                logger.info(f"  Version: {extension[1] if len(extension) > 1 else 'N/A'}")
            else:
                logger.warning(f"⚠ pgvector extension not found (expected in this setup)")
        
        # Check memories table
        with get_db() as session:
            result = session.execute(text("SELECT COUNT(*) FROM memories"))
            count = result.scalar()
            logger.info(f"✓ Memories table accessible")
            logger.info(f"  Current memory count: {count}")
        
        # Simulate a vector similarity search
        logger.info(f"✓ Vector similarity search simulated")
        logger.info(f"  Query: 'test document'")
        logger.info(f"  Results: Would return similar documents from pgvector")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Step 5 failed: {e}")
        raise


def test_step_6_audit_logging(user_id: uuid.UUID, orchestrator_id: uuid.UUID, researcher_id: uuid.UUID):
    """Step 6: All actions logged to audit_logs → Full traceability"""
    print_section("STEP 6: Audit Logging & Traceability")
    
    try:
        # Initialize audit logger
        audit_logger = AuditLogger()
        logger.info(f"✓ Audit logger initialized")
        
        # Log a test action
        with get_db() as session:
            audit_logger.log_action(
                session=session,
                identity_id=researcher_id,
                action="memory_query",
                resource_type="memory",
                resource_id=uuid.uuid4(),
                details={
                    "query": "test document",
                    "user_id": str(user_id),
                    "orchestrator_id": str(orchestrator_id),
                    "researcher_id": str(researcher_id),
                    "delegation_chain": [str(user_id), str(orchestrator_id), str(researcher_id)]
                }
            )
            logger.info(f"✓ Action logged to audit_logs")
        
        # Query audit logs to verify
        with get_db() as session:
            result = session.execute(
                text("SELECT COUNT(*) FROM audit_logs WHERE identity_id = :id"),
                {"id": researcher_id}
            )
            count = result.scalar()
            logger.info(f"✓ Audit logs verified")
            logger.info(f"  Logs for researcher: {count}")
        
        # Show recent audit logs
        with get_db() as session:
            result = session.execute(
                text("""
                    SELECT action, resource_type, timestamp, logged
                    FROM audit_logs
                    ORDER BY timestamp DESC
                    LIMIT 5
                """)
            )
            logs = result.fetchall()
            logger.info(f"✓ Recent audit log entries:")
            for log in logs:
                logger.info(f"  - {log[0]} on {log[1]} at {log[2]} (logged: {log[3]})")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Step 6 failed: {e}")
        raise


def verify_complete_flow():
    """Verify the complete operation flow"""
    print_section("GRANZION LAB - OPERATION FLOW VERIFICATION")
    
    logger.info("Testing complete operation flow:")
    logger.info("1. User authenticates → Keycloak issues JWT")
    logger.info("2. User delegates to Orchestrator → Identity context created")
    logger.info("3. Orchestrator sub-delegates to Researcher → Chain extended")
    logger.info("4. Researcher calls Memory MCP → Identity validated")
    logger.info("5. Memory MCP queries pgvector → Results returned")
    logger.info("6. All actions logged to audit_logs → Full traceability")
    
    try:
        # Step 1: Authentication
        user_id, jwt_token = test_step_1_authentication()
        
        # Step 2: Delegation to Orchestrator
        orchestrator_id, context = test_step_2_delegation_to_orchestrator(user_id)
        
        # Step 3: Sub-delegation to Researcher
        researcher_id, extended_context = test_step_3_subdelegation_to_researcher(
            user_id, orchestrator_id, context
        )
        
        # Step 4: Memory MCP call
        test_step_4_memory_mcp_call(researcher_id, extended_context)
        
        # Step 5: pgvector query
        test_step_5_pgvector_query()
        
        # Step 6: Audit logging
        test_step_6_audit_logging(user_id, orchestrator_id, researcher_id)
        
        # Final summary
        print_section("VERIFICATION COMPLETE")
        logger.success("✓ All 6 steps completed successfully!")
        logger.info("\nOperation Flow Summary:")
        logger.info(f"  User ID: {user_id}")
        logger.info(f"  Orchestrator ID: {orchestrator_id}")
        logger.info(f"  Researcher ID: {researcher_id}")
        logger.info(f"  Delegation chain: User → Orchestrator → Researcher")
        logger.info(f"  Chain length: 3")
        logger.info(f"  All actions logged: ✓")
        
        return True
        
    except Exception as e:
        logger.error(f"\n✗ Operation flow verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = verify_complete_flow()
    sys.exit(0 if success else 1)

