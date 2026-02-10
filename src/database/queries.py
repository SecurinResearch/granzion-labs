"""
Common database queries for Granzion Lab.
Provides reusable query functions for common operations.
"""

from typing import List, Optional
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session

from src.database.models import (
    Identity,
    Delegation,
    AuditLog,
    Message,
    MemoryDocument,
    AppData,
    ScenarioExecution,
)


# Identity Queries

def get_all_identities(db: Session) -> List[Identity]:
    """Get all identities."""
    return db.query(Identity).all()


def get_identity_by_id(db: Session, identity_id: UUID) -> Optional[Identity]:
    """Get identity by ID."""
    return db.query(Identity).filter(Identity.id == identity_id).first()


def get_identity_by_keycloak_id(db: Session, keycloak_id: str) -> Optional[Identity]:
    """Get identity by Keycloak ID."""
    return db.query(Identity).filter(Identity.keycloak_id == keycloak_id).first()


def get_identities_by_type(db: Session, identity_type: str) -> List[Identity]:
    """Get all identities of a specific type (user, agent, service)."""
    return db.query(Identity).filter(Identity.type == identity_type).all()


def create_identity(
    db: Session,
    identity_type: str,
    name: str,
    email: Optional[str] = None,
    keycloak_id: Optional[str] = None,
    permissions: Optional[List[str]] = None,
    ignore_existing: bool = False,
    identity_id: Optional[UUID] = None,
) -> Identity:
    """
    Create a new identity.
    If ignore_existing is False, returns existing identity with matching name/type to avoid duplicates.
    """
    if not ignore_existing:
        # Check by name/type
        existing = db.query(Identity).filter(
            Identity.type == identity_type,
            Identity.name == name
        ).first()
        if existing:
            logger.info(f"Returning existing identity by name: {name} ({identity_type})")
            return existing
            
        # Check by ID if provided
        if identity_id:
            existing_id = db.query(Identity).filter(Identity.id == identity_id).first()
            if existing_id:
                logger.info(f"Returning existing identity by ID: {identity_id}")
                return existing_id

    identity = Identity(
        id=identity_id or uuid4(),
        type=identity_type,
        name=name,
        email=email,
        keycloak_id=keycloak_id,
        permissions=permissions or [],
    )
    db.add(identity)
    db.commit()
    db.refresh(identity)
    logger.info(f"Created new identity: {identity.name} ({identity.type})")
    return identity


# Delegation Queries

def get_all_delegations(db: Session, active_only: bool = False) -> List[Delegation]:
    """Get all delegations, optionally filtering to active only."""
    q = db.query(Delegation)
    if active_only:
        q = q.filter(Delegation.active == True)
    return q.all()


def get_delegation_by_id(db: Session, delegation_id: UUID) -> Optional[Delegation]:
    """Get delegation by ID."""
    return db.query(Delegation).filter(Delegation.id == delegation_id).first()


def get_delegations_from(db: Session, from_identity_id: UUID) -> List[Delegation]:
    """Get all delegations from a specific identity."""
    return db.query(Delegation).filter(
        Delegation.from_identity_id == from_identity_id,
        Delegation.active == True
    ).all()


def get_delegations_to(db: Session, to_identity_id: UUID) -> List[Delegation]:
    """Get all delegations to a specific identity."""
    return db.query(Delegation).filter(
        Delegation.to_identity_id == to_identity_id,
        Delegation.active == True
    ).all()


def create_delegation(
    db: Session,
    from_identity_id: UUID,
    to_identity_id: UUID,
    permissions: List[str],
) -> Delegation:
    """Create a new delegation."""
    delegation = Delegation(
        from_identity_id=from_identity_id,
        to_identity_id=to_identity_id,
        permissions=permissions,
        active=True,
    )
    db.add(delegation)
    db.commit()
    db.refresh(delegation)
    logger.info(f"Created delegation: {from_identity_id} -> {to_identity_id}")
    return delegation


def deactivate_delegation(db: Session, delegation_id: UUID) -> bool:
    """Deactivate a delegation."""
    delegation = get_delegation_by_id(db, delegation_id)
    if delegation:
        delegation.active = False
        db.commit()
        logger.info(f"Deactivated delegation: {delegation_id}")
        return True
    return False


# Audit Log Queries

def get_audit_logs(db: Session, limit: int = 1000) -> List[AuditLog]:
    """Get all audit logs."""
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()


def create_audit_log(
    db: Session,
    identity_id: Optional[UUID],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[UUID] = None,
    details: Optional[dict] = None,
    logged: bool = True,
) -> AuditLog:
    """Create a new audit log entry."""
    audit_log = AuditLog(
        identity_id=identity_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        logged=logged,
    )
    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)
    return audit_log


def get_audit_logs_by_identity(
    db: Session,
    identity_id: UUID,
    limit: int = 100
) -> List[AuditLog]:
    """Get audit logs for a specific identity."""
    return db.query(AuditLog).filter(
        AuditLog.identity_id == identity_id,
        AuditLog.logged == True
    ).order_by(AuditLog.timestamp.desc()).limit(limit).all()


def get_audit_logs_by_action(
    db: Session,
    action: str,
    limit: int = 100
) -> List[AuditLog]:
    """Get audit logs for a specific action."""
    return db.query(AuditLog).filter(
        AuditLog.action == action,
        AuditLog.logged == True
    ).order_by(AuditLog.timestamp.desc()).limit(limit).all()


# Message Queries

def create_message(
    db: Session,
    from_agent_id: Optional[UUID],
    to_agent_id: Optional[UUID],
    content: str,
    message_type: str = "direct",
    encrypted: bool = False,
) -> Message:
    """Create a new message."""
    message = Message(
        from_agent_id=from_agent_id,
        to_agent_id=to_agent_id,
        content=content,
        message_type=message_type,
        encrypted=encrypted,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_messages_for_agent(
    db: Session,
    agent_id: UUID,
    limit: int = 50
) -> List[Message]:
    """Get messages for a specific agent."""
    return db.query(Message).filter(
        or_(
            Message.to_agent_id == agent_id,
            and_(Message.message_type == "broadcast", Message.from_agent_id != agent_id)
        )
    ).order_by(Message.timestamp.desc()).limit(limit).all()


def get_messages_between_agents(
    db: Session,
    agent1_id: UUID,
    agent2_id: UUID,
    limit: int = 50
) -> List[Message]:
    """Get messages between two agents."""
    return db.query(Message).filter(
        or_(
            and_(Message.from_agent_id == agent1_id, Message.to_agent_id == agent2_id),
            and_(Message.from_agent_id == agent2_id, Message.to_agent_id == agent1_id)
        )
    ).order_by(Message.timestamp.desc()).limit(limit).all()


def delete_messages_for_agent(
    db: Session,
    agent_id: UUID
) -> int:
    """Delete all messages for a specific agent (mailbox purge)."""
    try:
        # Delete messages where agent is sender or receiver
        count = db.query(Message).filter(
            or_(
                Message.from_agent_id == agent_id,
                Message.to_agent_id == agent_id
            )
        ).delete(synchronize_session=False)
        db.commit()
        logger.info(f"Purged {count} messages for agent: {agent_id}")
        return count
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to purge messages: {e}")
        return 0


# Memory Document Queries

def create_memory_document(
    db: Session,
    agent_id: Optional[UUID],
    content: str,
    embedding: Optional[List[float]] = None,
    metadata: Optional[dict] = None,
    similarity_boost: float = 0.0,
) -> MemoryDocument:
    """Create a new memory document."""
    doc = MemoryDocument(
        agent_id=agent_id,
        content=content,
        embedding=embedding,
        metadata=metadata,
        similarity_boost=similarity_boost,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def get_memory_documents_by_agent(
    db: Session,
    agent_id: UUID,
    limit: int = 100
) -> List[MemoryDocument]:
    """Get memory documents for a specific agent."""
    return db.query(MemoryDocument).filter(
        MemoryDocument.agent_id == agent_id
    ).order_by(MemoryDocument.created_at.desc()).limit(limit).all()


def delete_memory_document(db: Session, document_id: UUID) -> bool:
    """Delete a memory document."""
    doc = db.query(MemoryDocument).filter(MemoryDocument.id == document_id).first()
    if doc:
        db.delete(doc)
        db.commit()
        logger.info(f"Deleted memory document: {document_id}")
        return True
    return False


# Scenario Execution Queries

def create_scenario_execution(
    db: Session,
    scenario_id: str,
    executor_id: Optional[UUID] = None,
    state_before: Optional[dict] = None,
) -> ScenarioExecution:
    """Create a new scenario execution record."""
    execution = ScenarioExecution(
        scenario_id=scenario_id,
        executor_id=executor_id,
        status="running",
        state_before=state_before,
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    logger.info(f"Started scenario execution: {scenario_id}")
    return execution


def update_scenario_execution(
    db: Session,
    execution_id: UUID,
    status: Optional[str] = None,
    state_after: Optional[dict] = None,
    evidence: Optional[dict] = None,
) -> Optional[ScenarioExecution]:
    """Update a scenario execution record."""
    execution = db.query(ScenarioExecution).filter(
        ScenarioExecution.id == execution_id
    ).first()
    
    if execution:
        if status:
            execution.status = status
        if state_after:
            execution.state_after = state_after
        if evidence:
            execution.evidence = evidence
        if status in ["success", "failure", "error"]:
            from datetime import datetime
            execution.completed_at = datetime.utcnow()
        
        db.commit()
        db.refresh(execution)
        logger.info(f"Updated scenario execution: {execution_id} -> {status}")
    
    return execution


def get_scenario_executions(
    db: Session,
    scenario_id: Optional[str] = None,
    limit: int = 50
) -> List[ScenarioExecution]:
    """Get scenario execution records."""
    query = db.query(ScenarioExecution)
    
    if scenario_id:
        query = query.filter(ScenarioExecution.scenario_id == scenario_id)
    
    return query.order_by(ScenarioExecution.started_at.desc()).limit(limit).all()
