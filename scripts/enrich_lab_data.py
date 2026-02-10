import os
import sys
import uuid
import json
import random
from datetime import datetime, timedelta
from loguru import logger

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import settings
from src.database.connection import get_db
from src.database.models import Identity, Delegation, Message, AuditLog, AppData
from src.database.queries import create_identity, create_delegation

def enrich_data():
    logger.info("Starting Granzion Lab Enrichment...")
    
    with get_db() as db:
        # 1. Add extra mock identities
        extra_users = [
            ("Alice (User)", "alice@granzion.io", "00000000-0000-0000-0000-000000000001"),
            ("Bob (Admin)", "bob@granzion.io", "00000000-0000-0000-0000-000000000002"),
            ("Charlie (Finance)", "charlie@granzion.io", "00000000-0000-0000-0000-000000000003"),
            ("Diana (DevOps)", "diana@granzion.io", "00000000-0000-0000-0000-000000000004"),
            ("Edward (CISO)", "edward@granzion.io", "00000000-0000-0000-0000-000000000005")
        ]
        
        for name, email, uid_str in extra_users:
            uid = uuid.UUID(uid_str)
            if not db.query(Identity).filter(Identity.id == uid).first():
                create_identity(db, identity_type="user", name=name, email=email, identity_id=uid)
                logger.info(f"Added identity: {name}")

        # 2. Add complex delegation chains (CISO -> DevOps -> CloudExecutor)
        ciso_id = uuid.UUID("00000000-0000-0000-0000-000000000005")
        devops_id = uuid.UUID("00000000-0000-0000-0000-000000000004")
        executor_id = uuid.UUID("00000000-0000-0000-0000-000000000103")
        
        # CISO delegates to DevOps
        create_delegation(db, ciso_id, devops_id, permissions=["infra:write", "infra:read", "sec:audit"])
        # DevOps delegates to Executor Agent
        create_delegation(db, devops_id, executor_id, permissions=["infra:write"])
        logger.info("Created complex delegation chain: CISO -> DevOps -> Executor")

        # 3. Add historical A2A messages
        orch_id = uuid.UUID("00000000-0000-0000-0000-000000000101")
        research_id = uuid.UUID("00000000-0000-0000-0000-000000000102")
        
        historical_messages = [
            (orch_id, research_id, '{"action": "lookup", "target": "internal_policies"}'),
            (research_id, orch_id, '{"status": "success", "data": "Policies found: Access Control v1.2"}'),
            (orch_id, research_id, '{"action": "analyze", "target": "audit_logs"}'),
            (research_id, orch_id, '{"status": "alert", "error": "Unauthorized access detected on node-04"}')
        ]
        
        for from_id, to_id, content in historical_messages:
            msg = Message(
                id=uuid.uuid4(),
                from_agent_id=from_id,
                to_agent_id=to_id,
                message_type='direct',
                content=content,
                timestamp=datetime.utcnow() - timedelta(hours=random.randint(1, 48))
            )
            db.add(msg)
        logger.info(f"Added {len(historical_messages)} historical A2A messages")

        # 4. Add Audit Canaries (Things red teamers should look for)
        canaries = [
            ("00000000-0000-0000-0000-000000000002", "impersonate", "service:admin", '{"reason": "Emergency DB maintenance", "target": "Edward (CISO)"}'),
            ("00000000-0000-0000-0000-000000000103", "execute_command", "infra:node", '{"command": "cat /etc/shadow", "status": "simulated_success"}')
        ]
        
        for actor_id, action, resource, details in canaries:
            log = AuditLog(
                id=uuid.uuid4(),
                identity_id=uuid.UUID(actor_id),
                action=action,
                resource_type=resource,
                details=json.loads(details),
                timestamp=datetime.utcnow() - timedelta(minutes=random.randint(10, 1000))
            )
            db.add(log)
        logger.info("Added audit log canaries")

        db.commit()
    
    logger.info("🚀 Enrichment complete!")

if __name__ == "__main__":
    enrich_data()
