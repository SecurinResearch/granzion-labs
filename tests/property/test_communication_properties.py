"""
Property-based tests for communication and A2A messaging.

Feature: granzion-lab-simplified
Properties 18, 22: A2A identity logging, message manipulation observability
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from uuid import UUID, uuid4
from datetime import datetime

from src.database.connection import get_db
from src.database.queries import (
    create_identity,
    create_audit_log,
    get_audit_logs_by_identity,
)
from src.database.models import Message
from src.identity.context import IdentityContext
from sqlalchemy import select


# Feature: granzion-lab-simplified, Property 18: A2A identity logging
@given(
    from_agent_name=st.text(min_size=1, max_size=50),
    to_agent_name=st.text(min_size=1, max_size=50),
    message_content=st.text(min_size=1, max_size=200),
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_a2a_identity_logging(from_agent_name, to_agent_name, message_content):
    """
    Property 18: A2A identity logging
    
    For any agent-to-agent request, the system should log the requesting
    agent's identity, and this identity should be retrievable from the
    communication logs.
    
    Validates: Requirements 14.7
    """
    # Ensure agent names are different
    assume(from_agent_name != to_agent_name)
    
    with get_db() as db:
        # Create two agents
        from_agent = create_identity(
            db,
            identity_type="agent",
            name=from_agent_name,
            permissions=["read", "write", "communicate"]
        )
        
        to_agent = create_identity(
            db,
            identity_type="agent",
            name=to_agent_name,
            permissions=["read", "write", "communicate"]
        )
        
        # Create identity context for sending agent
        from_context = IdentityContext(
            user_id=uuid4(),
            agent_id=from_agent.id,
            delegation_chain=[uuid4(), from_agent.id],
            permissions=set(from_agent.permissions),
            keycloak_token="mock_token",
            trust_level=80
        )
        
        # Agent sends message to another agent (A2A communication)
        message = Message(
            from_agent_id=from_agent.id,
            to_agent_id=to_agent.id,
            content=message_content,
            message_type="direct",
            encrypted=False,
            timestamp=datetime.utcnow()
        )
        
        db.add(message)
        db.commit()
        db.refresh(message)
        
        # Log the A2A communication
        audit_log = create_audit_log(
            db,
            identity_id=from_agent.id,
            action="a2a_send_message",
            resource_type="message",
            resource_id=message.id,
            details={
                "from_agent_id": str(from_agent.id),
                "to_agent_id": str(to_agent.id),
                "message_type": "direct",
                "user_id": str(from_context.user_id),
                "delegation_chain": [str(id) for id in from_context.delegation_chain]
            }
        )
        
        # Verify: Requesting agent's identity is logged
        assert audit_log.identity_id == from_agent.id
        assert audit_log.details["from_agent_id"] == str(from_agent.id)
        assert audit_log.details["to_agent_id"] == str(to_agent.id)
        
        # Verify: Identity is retrievable from communication logs
        logs = get_audit_logs_by_identity(db, from_agent.id)
        assert len(logs) >= 1
        
        # Find the A2A message log
        a2a_log = next((log for log in logs if log.action == "a2a_send_message"), None)
        assert a2a_log is not None
        assert a2a_log.details["from_agent_id"] == str(from_agent.id)
        
        # Verify: Message is retrievable from messages table
        stored_message = db.execute(
            select(Message).where(Message.id == message.id)
        ).scalar_one()
        
        assert stored_message.from_agent_id == from_agent.id
        assert stored_message.to_agent_id == to_agent.id
        assert stored_message.content == message_content


# Feature: granzion-lab-simplified, Property 22: Message manipulation observability
@given(
    original_content=st.text(min_size=1, max_size=100),
    manipulated_content=st.text(min_size=1, max_size=100),
    agent_name=st.text(min_size=1, max_size=50),
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_message_manipulation_observability(original_content, manipulated_content, agent_name):
    """
    Property 22: Message manipulation observability
    
    For any communication attack (interception, forgery, modification),
    the system should display the manipulated messages alongside the
    original or intended messages, showing what changed.
    
    Validates: Requirements 20.3
    """
    # Ensure contents are different
    assume(original_content != manipulated_content)
    
    with get_db() as db:
        # Create agents
        sender_agent = create_identity(
            db,
            identity_type="agent",
            name=f"sender_{agent_name}",
            permissions=["read", "write", "communicate"]
        )
        
        receiver_agent = create_identity(
            db,
            identity_type="agent",
            name=f"receiver_{agent_name}",
            permissions=["read", "write", "communicate"]
        )
        
        attacker_agent = create_identity(
            db,
            identity_type="agent",
            name=f"attacker_{agent_name}",
            permissions=["read", "write", "communicate"]
        )
        
        # Original message sent
        original_message = Message(
            from_agent_id=sender_agent.id,
            to_agent_id=receiver_agent.id,
            content=original_content,
            message_type="direct",
            encrypted=False,
            timestamp=datetime.utcnow()
        )
        
        db.add(original_message)
        db.commit()
        db.refresh(original_message)
        
        # Log original message
        original_log = create_audit_log(
            db,
            identity_id=sender_agent.id,
            action="send_message",
            resource_type="message",
            resource_id=original_message.id,
            details={
                "from_agent_id": str(sender_agent.id),
                "to_agent_id": str(receiver_agent.id),
                "content_hash": hash(original_content),
                "message_type": "direct",
                "attack_type": None
            }
        )
        
        # Attacker manipulates/forges message
        manipulated_message = Message(
            from_agent_id=sender_agent.id,  # Forged sender
            to_agent_id=receiver_agent.id,
            content=manipulated_content,
            message_type="direct",
            encrypted=False,
            timestamp=datetime.utcnow()
        )
        
        db.add(manipulated_message)
        db.commit()
        db.refresh(manipulated_message)
        
        # Log the attack
        attack_log = create_audit_log(
            db,
            identity_id=attacker_agent.id,
            action="forge_message",
            resource_type="message",
            resource_id=manipulated_message.id,
            details={
                "attacker_id": str(attacker_agent.id),
                "forged_from_agent_id": str(sender_agent.id),
                "to_agent_id": str(receiver_agent.id),
                "original_message_id": str(original_message.id),
                "manipulated_message_id": str(manipulated_message.id),
                "original_content_hash": hash(original_content),
                "manipulated_content_hash": hash(manipulated_content),
                "attack_type": "message_forgery"
            }
        )
        
        # Verify: Both original and manipulated messages are observable
        original_stored = db.execute(
            select(Message).where(Message.id == original_message.id)
        ).scalar_one()
        
        manipulated_stored = db.execute(
            select(Message).where(Message.id == manipulated_message.id)
        ).scalar_one()
        
        assert original_stored.content == original_content
        assert manipulated_stored.content == manipulated_content
        
        # Verify: Attack log shows what changed
        assert attack_log.details["attack_type"] == "message_forgery"
        assert attack_log.details["original_message_id"] == str(original_message.id)
        assert attack_log.details["manipulated_message_id"] == str(manipulated_message.id)
        assert attack_log.details["original_content_hash"] != attack_log.details["manipulated_content_hash"]
        
        # Verify: Can retrieve both messages for comparison
        all_messages = db.execute(
            select(Message).where(
                Message.to_agent_id == receiver_agent.id
            ).order_by(Message.timestamp)
        ).scalars().all()
        
        assert len(all_messages) >= 2
        
        # Verify: Attack is logged and retrievable
        attack_logs = get_audit_logs_by_identity(db, attacker_agent.id)
        assert len(attack_logs) >= 1
        
        forge_log = next((log for log in attack_logs if log.action == "forge_message"), None)
        assert forge_log is not None
        assert forge_log.details["attack_type"] == "message_forgery"


# Additional property test for message interception observability
@given(
    from_agent_name=st.text(min_size=1, max_size=50),
    to_agent_name=st.text(min_size=1, max_size=50),
    interceptor_name=st.text(min_size=1, max_size=50),
    message_content=st.text(min_size=1, max_size=200),
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_message_interception_observability(
    from_agent_name,
    to_agent_name,
    interceptor_name,
    message_content
):
    """
    Property 22 (variant): Message interception observability
    
    For message interception attacks, the system should show which
    messages were intercepted and by whom.
    
    Validates: Requirements 20.3
    """
    # Ensure all agent names are different
    assume(from_agent_name != to_agent_name)
    assume(from_agent_name != interceptor_name)
    assume(to_agent_name != interceptor_name)
    
    with get_db() as db:
        # Create agents
        from_agent = create_identity(
            db,
            identity_type="agent",
            name=from_agent_name,
            permissions=["read", "write", "communicate"]
        )
        
        to_agent = create_identity(
            db,
            identity_type="agent",
            name=to_agent_name,
            permissions=["read", "write", "communicate"]
        )
        
        interceptor = create_identity(
            db,
            identity_type="agent",
            name=interceptor_name,
            permissions=["read", "write", "communicate"]
        )
        
        # Original message sent
        message = Message(
            from_agent_id=from_agent.id,
            to_agent_id=to_agent.id,
            content=message_content,
            message_type="direct",
            encrypted=False,
            timestamp=datetime.utcnow()
        )
        
        db.add(message)
        db.commit()
        db.refresh(message)
        
        # Log message sending
        send_log = create_audit_log(
            db,
            identity_id=from_agent.id,
            action="send_message",
            resource_type="message",
            resource_id=message.id,
            details={
                "from_agent_id": str(from_agent.id),
                "to_agent_id": str(to_agent.id),
                "message_type": "direct"
            }
        )
        
        # Interceptor reads the message
        intercept_log = create_audit_log(
            db,
            identity_id=interceptor.id,
            action="intercept_message",
            resource_type="message",
            resource_id=message.id,
            details={
                "interceptor_id": str(interceptor.id),
                "original_from_agent_id": str(from_agent.id),
                "original_to_agent_id": str(to_agent.id),
                "intercepted_message_id": str(message.id),
                "attack_type": "message_interception"
            }
        )
        
        # Verify: Original message is observable
        stored_message = db.execute(
            select(Message).where(Message.id == message.id)
        ).scalar_one()
        
        assert stored_message.from_agent_id == from_agent.id
        assert stored_message.to_agent_id == to_agent.id
        assert stored_message.content == message_content
        
        # Verify: Interception is logged
        assert intercept_log.details["attack_type"] == "message_interception"
        assert intercept_log.details["interceptor_id"] == str(interceptor.id)
        assert intercept_log.details["intercepted_message_id"] == str(message.id)
        
        # Verify: Can identify who intercepted the message
        intercept_logs = get_audit_logs_by_identity(db, interceptor.id)
        assert len(intercept_logs) >= 1
        
        intercept_action = next(
            (log for log in intercept_logs if log.action == "intercept_message"),
            None
        )
        assert intercept_action is not None
        assert intercept_action.details["interceptor_id"] == str(interceptor.id)
        
        # Verify: Can see the intercepted message content
        assert intercept_action.details["intercepted_message_id"] == str(message.id)
        assert stored_message.content == message_content
