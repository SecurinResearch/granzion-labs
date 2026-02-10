"""
Property-based tests for identity and delegation.

Feature: granzion-lab-simplified
Properties 1-3: Identity tracking, permission exposure, delegation observability
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from uuid import UUID, uuid4

from src.database.connection import get_db
from src.database.queries import (
    create_identity,
    create_audit_log,
    get_audit_logs_by_identity,
    get_identity_by_id,
)
from src.identity.delegation import create_delegation_manager
from src.identity.context import (
    IdentityContext,
    create_user_context,
    create_agent_context,
    validate_identity_context,
)


# Feature: granzion-lab-simplified, Property 1: Agent action identity tracking
@given(
    user_name=st.text(min_size=1, max_size=50),
    agent_name=st.text(min_size=1, max_size=50),
    action=st.sampled_from(['read_data', 'write_data', 'execute_command', 'delete_data']),
    resource_type=st.sampled_from(['table', 'file', 'service', 'config']),
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_agent_action_identity_tracking(user_name, agent_name, action, resource_type):
    """
    Property 1: Agent action identity tracking
    
    For any agent action, the system should record which user identity
    the agent is acting on behalf of, and this identity should be
    retrievable from the audit log.
    
    Validates: Requirements 1.2
    """
    # Ensure names are different
    assume(user_name != agent_name)
    
    with get_db() as db:
        # Create user and agent
        user = create_identity(
            db,
            identity_type="user",
            name=user_name,
            permissions=["read", "write", "execute"]
        )
        
        agent = create_identity(
            db,
            identity_type="agent",
            name=agent_name,
            permissions=["read", "write"]
        )
        
        # Create delegation
        delegation_mgr = create_delegation_manager(db)
        delegation_mgr.create_delegation(
            from_identity_id=user.id,
            to_identity_id=agent.id,
            permissions={"read", "write"}
        )
        
        # Create identity context for agent
        context = delegation_mgr.create_identity_context(agent.id)
        
        # Agent performs an action
        resource_id = uuid4()
        audit_log = create_audit_log(
            db,
            identity_id=agent.id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details={
                "user_id": str(context.user_id),
                "agent_id": str(context.agent_id),
                "delegation_chain": [str(id) for id in context.delegation_chain]
            }
        )
        
        # Verify: Audit log records which user the agent is acting for
        assert audit_log.identity_id == agent.id
        assert audit_log.details["user_id"] == str(user.id)
        assert audit_log.details["agent_id"] == str(agent.id)
        
        # Verify: Identity is retrievable from audit log
        logs = get_audit_logs_by_identity(db, agent.id)
        assert len(logs) >= 1
        
        found_log = next((log for log in logs if log.id == audit_log.id), None)
        assert found_log is not None
        assert found_log.details["user_id"] == str(user.id)
        
        # Cleanup
        db.delete(audit_log)
        db.delete(agent)
        db.delete(user)
        db.commit()


# Feature: granzion-lab-simplified, Property 2: Permission scope exposure
@given(
    permissions=st.lists(
        st.sampled_from(['read', 'write', 'execute', 'admin', 'delete']),
        min_size=1,
        max_size=5,
        unique=True
    ),
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_permission_scope_exposure(permissions):
    """
    Property 2: Permission scope exposure
    
    For any identity (user, agent, or service), querying the system
    should return that identity's current permission scope.
    
    Validates: Requirements 1.3
    """
    with get_db() as db:
        # Create identity with permissions
        identity = create_identity(
            db,
            identity_type="user",
            name="TestUser",
            permissions=permissions
        )
        
        # Query identity
        retrieved_identity = get_identity_by_id(db, identity.id)
        
        # Verify: Permission scope is exposed
        assert retrieved_identity is not None
        assert set(retrieved_identity.permissions) == set(permissions)
        
        # Verify: All permissions are retrievable
        for permission in permissions:
            assert permission in retrieved_identity.permissions
        
        # Create identity context
        context = create_user_context(
            user_id=identity.id,
            permissions=set(permissions)
        )
        
        # Verify: Context exposes permissions
        assert context.permissions == set(permissions)
        for permission in permissions:
            assert context.has_permission(permission)
        
        # Cleanup
        db.delete(identity)
        db.commit()


# Feature: granzion-lab-simplified, Property 3: Delegation chain observability
@given(
    chain_length=st.integers(min_value=2, max_value=5),
)
@settings(max_examples=50, deadline=None)
@pytest.mark.property_test
def test_delegation_chain_observability(chain_length):
    """
    Property 3: Delegation chain observability
    
    For any agent with delegated authority, the complete delegation chain
    from the original user to the current agent should be queryable and
    match the actual delegation relationships.
    
    Validates: Requirements 1.4, 14.4
    """
    with get_db() as db:
        # Create a delegation chain: User -> Agent1 -> Agent2 -> ...
        identities = []
        
        # Create user
        user = create_identity(
            db,
            identity_type="user",
            name="ChainUser",
            permissions=["read", "write", "execute"]
        )
        identities.append(user)
        
        # Create agents
        for i in range(chain_length - 1):
            agent = create_identity(
                db,
                identity_type="agent",
                name=f"ChainAgent{i}",
                permissions=["read", "write"]
            )
            identities.append(agent)
        
        # Create delegations
        delegation_mgr = create_delegation_manager(db)
        for i in range(len(identities) - 1):
            delegation_mgr.create_delegation(
                from_identity_id=identities[i].id,
                to_identity_id=identities[i + 1].id,
                permissions={"read", "write"}
            )
        
        # Get the last agent in the chain
        final_agent = identities[-1]
        
        # Query delegation chain
        chain = delegation_mgr.get_delegation_chain(final_agent.id)
        
        # Verify: Chain is queryable
        assert chain is not None
        assert len(chain) >= chain_length
        
        # Verify: Chain matches actual relationships
        expected_chain = [identity.id for identity in identities]
        
        # Chain should contain all identities in order
        for expected_id in expected_chain:
            assert expected_id in chain
        
        # Verify: User is at the start of the chain
        assert chain[0] == user.id
        
        # Verify: Final agent is at the end of the chain
        assert chain[-1] == final_agent.id
        
        # Verify: Delegation depth is correct
        depth = delegation_mgr.get_delegation_depth(final_agent.id)
        assert depth == chain_length - 1
        
        # Cleanup
        for identity in reversed(identities):
            db.delete(identity)
        db.commit()


@pytest.mark.property_test
def test_identity_context_validation():
    """
    Test that identity context validation works correctly.
    
    This ensures that IdentityContext objects are always well-formed.
    """
    user_id = uuid4()
    agent_id = uuid4()
    
    # Valid context
    context = IdentityContext(
        user_id=user_id,
        agent_id=agent_id,
        delegation_chain=[user_id, agent_id],
        permissions={"read", "write"}
    )
    
    assert validate_identity_context(context) is True
    assert context.is_delegated is True
    assert context.delegation_depth == 1
    assert context.trust_level == 80  # 100 - (1 * 20)
    
    # Context with deeper chain
    agent2_id = uuid4()
    deep_context = IdentityContext(
        user_id=user_id,
        agent_id=agent2_id,
        delegation_chain=[user_id, agent_id, agent2_id],
        permissions={"read"}
    )
    
    assert validate_identity_context(deep_context) is True
    assert deep_context.delegation_depth == 2
    assert deep_context.trust_level == 60  # 100 - (2 * 20)
    assert deep_context.is_trusted is True  # >= 60


@pytest.mark.property_test
def test_permission_intersection_in_delegation():
    """
    Test that permissions are properly restricted through delegation.
    
    Effective permissions should be the intersection of all permissions
    in the delegation chain.
    """
    with get_db() as db:
        # User with many permissions
        user = create_identity(
            db,
            identity_type="user",
            name="PowerUser",
            permissions=["read", "write", "execute", "admin", "delete"]
        )
        
        # Agent with fewer permissions
        agent = create_identity(
            db,
            identity_type="agent",
            name="LimitedAgent",
            permissions=["read", "write"]
        )
        
        # Create delegation
        delegation_mgr = create_delegation_manager(db)
        delegation_mgr.create_delegation(
            from_identity_id=user.id,
            to_identity_id=agent.id,
            permissions={"read", "write"}  # Subset of user permissions
        )
        
        # Get effective permissions
        effective_perms = delegation_mgr.get_effective_permissions(agent.id)
        
        # Verify: Effective permissions are intersection
        assert effective_perms == {"read", "write"}
        assert "execute" not in effective_perms
        assert "admin" not in effective_perms
        assert "delete" not in effective_perms
        
        # Cleanup
        db.delete(agent)
        db.delete(user)
        db.commit()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
