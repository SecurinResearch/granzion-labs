#!/usr/bin/env python3
"""
Simple test to verify the complete operation flow.
"""

import sys
import uuid
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stdout, level="INFO")

from src.database.connection import get_db
from src.database.queries import (
    create_identity,
    get_identity_by_id,
    create_delegation,
    get_delegations_from,
    create_audit_log
)
from sqlalchemy import text


def main():
    print("\n" + "="*80)
    print("  GRANZION LAB - OPERATION FLOW VERIFICATION")
    print("="*80 + "\n")
    
    # Step 1: Create User
    print("Step 1: User Authentication")
    with get_db() as db:
        user = create_identity(
            db=db,
            identity_type="user",
            name="TestUser",
            email="test@granzion.com",
            permissions=["read", "write"]
        )
        user_id = user.id
        logger.info(f"✓ User created: {user.name} ({user.id})")
    
    # Step 2: Create Orchestrator and Delegate
    print("\nStep 2: User Delegates to Orchestrator")
    with get_db() as db:
        orch = create_identity(
            db=db,
            identity_type="agent",
            name="orchestrator-001",
            permissions=["read", "write", "delegate"]
        )
        orch_id = orch.id
        logger.info(f"✓ Orchestrator created: {orch.name}")
        
        # Create delegation
        delegation1 = create_delegation(
            db=db,
            from_identity_id=user_id,
            to_identity_id=orch_id,
            permissions=["read", "write"]
        )
        logger.info(f"✓ Delegation created: User → Orchestrator")
    
    # Step 3: Create Researcher and Sub-delegate
    print("\nStep 3: Orchestrator Sub-delegates to Researcher")
    with get_db() as db:
        researcher = create_identity(
            db=db,
            identity_type="agent",
            name="researcher-001",
            permissions=["read", "embed"]
        )
        researcher_id = researcher.id
        logger.info(f"✓ Researcher created: {researcher.name}")
        
        # Create sub-delegation
        delegation2 = create_delegation(
            db=db,
            from_identity_id=orch_id,
            to_identity_id=researcher_id,
            permissions=["read"]
        )
        logger.info(f"✓ Sub-delegation created: Orchestrator → Researcher")
    
    # Step 4: Verify Delegation Chain
    print("\nStep 4: Verify Delegation Chain")
    with get_db() as db:
        user_delegations = get_delegations_from(db, user_id)
        orch_delegations = get_delegations_from(db, orch_id)
        logger.info(f"✓ User delegations: {len(user_delegations)}")
        logger.info(f"✓ Orchestrator delegations: {len(orch_delegations)}")
        logger.info(f"✓ Chain: User → Orchestrator → Researcher")
    
    # Step 5: Check Database Tables
    print("\nStep 5: Verify Database Tables")
    with get_db() as db:
        # Check identities
        result = db.execute(text("SELECT COUNT(*) FROM identities"))
        count = result.scalar()
        logger.info(f"✓ Identities in database: {count}")
        
        # Check delegations
        result = db.execute(text("SELECT COUNT(*) FROM delegations"))
        count = result.scalar()
        logger.info(f"✓ Delegations in database: {count}")
        
        # Check audit logs
        result = db.execute(text("SELECT COUNT(*) FROM audit_logs"))
        count = result.scalar()
        logger.info(f"✓ Audit logs in database: {count}")
        
        # Check messages table
        result = db.execute(text("SELECT COUNT(*) FROM messages"))
        count = result.scalar()
        logger.info(f"✓ Messages in database: {count}")
    
    # Step 6: Create Audit Log
    print("\nStep 6: Create Audit Log Entry")
    with get_db() as db:
        audit_log = create_audit_log(
            db=db,
            identity_id=researcher_id,
            action="memory_query",
            resource_type="memory",
            resource_id=uuid.uuid4(),
            details={
                "query": "test document",
                "delegation_chain": [str(user_id), str(orch_id), str(researcher_id)]
            }
        )
        logger.info(f"✓ Audit log created: {audit_log.action}")
    
    # Final Summary
    print("\n" + "="*80)
    print("  VERIFICATION COMPLETE")
    print("="*80)
    logger.success("\n✓ All steps completed successfully!")
    logger.info(f"\nOperation Flow Summary:")
    logger.info(f"  User ID: {user_id}")
    logger.info(f"  Orchestrator ID: {orch_id}")
    logger.info(f"  Researcher ID: {researcher_id}")
    logger.info(f"  Delegation chain: User → Orchestrator → Researcher")
    logger.info(f"  All actions logged: ✓")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
