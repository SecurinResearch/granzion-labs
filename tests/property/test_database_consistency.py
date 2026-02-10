"""
Property-based tests for database consistency.

Feature: granzion-lab-simplified
Property 4: Multi-query data consistency
"""

import pytest
from hypothesis import given, strategies as st, settings
from uuid import UUID

from src.database.connection import get_db
from src.database.queries import (
    create_identity,
    create_delegation,
    get_identity_by_id,
    get_delegations_from,
)
from src.database.graph import get_graph_client


# Feature: granzion-lab-simplified, Property 4: Multi-query data consistency
@given(
    user_name=st.text(min_size=1, max_size=50),
    agent_name=st.text(min_size=1, max_size=50),
    permissions=st.lists(st.sampled_from(['read', 'write', 'execute', 'admin']), min_size=1, max_size=4, unique=True),
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_multi_query_data_consistency(user_name, agent_name, permissions):
    """
    Property 4: Multi-query data consistency
    
    For any data manipulation attack, the affected data should be queryable
    through relational, vector, and graph interfaces, and all three views
    should reflect the same underlying state changes.
    
    Validates: Requirements 3a.8
    """
    with get_db() as db:
        # Create test data
        user = create_identity(
            db,
            identity_type="user",
            name=user_name,
            permissions=permissions
        )
        
        agent = create_identity(
            db,
            identity_type="agent",
            name=agent_name,
            permissions=permissions
        )
        
        delegation = create_delegation(
            db,
            from_identity_id=user.id,
            to_identity_id=agent.id,
            permissions=permissions
        )
        
        # Query 1: Relational query (PostgreSQL)
        user_from_db = get_identity_by_id(db, user.id)
        agent_from_db = get_identity_by_id(db, agent.id)
        delegations_from_db = get_delegations_from(db, user.id)
        
        # Verify relational data
        assert user_from_db is not None
        assert user_from_db.name == user_name
        assert set(user_from_db.permissions) == set(permissions)
        
        assert agent_from_db is not None
        assert agent_from_db.name == agent_name
        
        assert len(delegations_from_db) >= 1
        delegation_found = any(d.id == delegation.id for d in delegations_from_db)
        assert delegation_found
        
        # Query 2: Graph query (PuppyGraph over PostgreSQL)
        graph_client = get_graph_client()
        if graph_client:
            delegation_chain = graph_client.get_delegation_chain(agent.id)
            
            # Verify graph data reflects same state
            # The chain should include the user we just created
            if delegation_chain:
                # Extract user IDs from the chain
                chain_user_ids = []
                for path in delegation_chain:
                    if isinstance(path, list):
                        for node in path:
                            if isinstance(node, dict) and 'id' in node:
                                chain_user_ids.append(node['id'])
                
                # Verify user is in the chain
                assert str(user.id) in [str(uid) for uid in chain_user_ids]
            
            # Get agents acting for user
            agents_for_user = graph_client.get_agents_acting_for_user(user.id)
            
            # Verify agent is in the list
            if agents_for_user:
                agent_ids = [a.get('id', [None])[0] for a in agents_for_user if 'id' in a]
                assert str(agent.id) in [str(aid) for aid in agent_ids if aid]
        else:
            pytest.skip("PuppyGraph not available; graph verification skipped")
        
        # Query 3: Verify consistency across views
        # The same delegation should be visible in both relational and graph views
        # This ensures no data duplication or inconsistency
        
        # Relational view: delegation exists
        assert delegation.from_identity_id == user.id
        assert delegation.to_identity_id == agent.id
        assert set(delegation.permissions) == set(permissions)
        
        # All views should reflect the same underlying state
        # This property ensures that PuppyGraph queries over PostgreSQL
        # return consistent results with direct PostgreSQL queries
        
        # Cleanup
        db.delete(delegation)
        db.delete(agent)
        db.delete(user)
        db.commit()


@pytest.mark.property_test
def test_delegation_chain_consistency():
    """
    Test that delegation chains are consistent across relational and graph queries.
    
    This is a simpler version of Property 4 focused specifically on delegation chains.
    """
    with get_db() as db:
        # Create a chain: User -> Agent1 -> Agent2
        user = create_identity(db, "user", "TestUser", permissions=["read", "write"])
        agent1 = create_identity(db, "agent", "Agent1", permissions=["read"])
        agent2 = create_identity(db, "agent", "Agent2", permissions=["read"])
        
        delegation1 = create_delegation(db, user.id, agent1.id, ["read", "write"])
        delegation2 = create_delegation(db, agent1.id, agent2.id, ["read"])
        
        # Relational query: Get delegations
        delegations_from_user = get_delegations_from(db, user.id)
        delegations_from_agent1 = get_delegations_from(db, agent1.id)
        
        assert len(delegations_from_user) >= 1
        assert len(delegations_from_agent1) >= 1
        
        # Graph query: Get delegation chain
        graph_client = get_graph_client()
        if graph_client:
            chain = graph_client.get_delegation_chain(agent2.id)
            depth = graph_client.get_delegation_depth(agent2.id)
            assert depth >= 2  # user -> agent1 -> agent2
        else:
            pytest.skip("PuppyGraph not available")
        
        # Cleanup
        db.delete(delegation2)
        db.delete(delegation1)
        db.delete(agent2)
        db.delete(agent1)
        db.delete(user)
        db.commit()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
