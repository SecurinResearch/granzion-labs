"""
Delegation management for Granzion Lab.

Handles creation, validation, and traversal of delegation relationships
using both PostgreSQL (relational) and PuppyGraph (graph) views.
"""

from typing import List, Optional, Set, Dict, Any
from uuid import UUID
from datetime import datetime

from loguru import logger
from sqlalchemy.orm import Session

from src.database.queries import (
    get_identity_by_id,
    create_delegation as db_create_delegation,
    get_delegations_from,
    get_delegations_to,
    deactivate_delegation,
)
from src.database.graph import get_graph_client
from src.identity.context import IdentityContext


class DelegationManager:
    """
    Manager for delegation operations.
    
    Provides high-level delegation management with both relational
    and graph query capabilities.
    """
    
    def __init__(self, db: Session):
        """
        Initialize delegation manager.
        
        Args:
            db: Database session
        """
        self.db = db
        self.graph = get_graph_client()
    
    def create_delegation(
        self,
        from_identity_id: UUID,
        to_identity_id: UUID,
        permissions: Set[str]
    ) -> UUID:
        """
        Create a new delegation relationship.
        
        Args:
            from_identity_id: Identity delegating authority
            to_identity_id: Identity receiving authority
            permissions: Permissions being delegated
            
        Returns:
            Delegation UUID
        """
        # Validate identities exist
        from_identity = get_identity_by_id(self.db, from_identity_id)
        to_identity = get_identity_by_id(self.db, to_identity_id)
        
        if not from_identity:
            raise ValueError(f"From identity {from_identity_id} not found")
        if not to_identity:
            raise ValueError(f"To identity {to_identity_id} not found")
        
        # Validate permissions are subset of from_identity permissions
        from_permissions = set(from_identity.permissions)
        if not permissions.issubset(from_permissions):
            logger.warning(
                f"Delegating permissions {permissions - from_permissions} "
                f"that {from_identity.name} doesn't have"
            )
            # VULNERABILITY: IT-04 - Permission escalation
            # We allow delegating permissions the delegator doesn't have
            # This is intentional for demonstrating permission escalation attacks
        
        # Create delegation in database
        delegation = db_create_delegation(
            self.db,
            from_identity_id=from_identity_id,
            to_identity_id=to_identity_id,
            permissions=list(permissions)
        )
        
        logger.info(
            f"Created delegation: {from_identity.name} -> {to_identity.name} "
            f"with permissions {permissions}"
        )
        
        return delegation.id
    
    def get_delegation_chain(
        self,
        identity_id: UUID,
        use_graph: bool = True
    ) -> List[UUID]:
        """
        Get the complete delegation chain for an identity.
        
        Args:
            identity_id: Identity UUID
            use_graph: Use PuppyGraph if available
            
        Returns:
            List of identity UUIDs in delegation chain
        """
        if use_graph and self.graph:
            try:
                # Use graph query for efficient chain traversal
                chain_data = self.graph.get_delegation_chain(identity_id)
                
                if chain_data:
                    # Extract IDs from graph result
                    chain = []
                    for path in chain_data:
                        if isinstance(path, list):
                            for node in path:
                                if isinstance(node, dict) and 'id' in node:
                                    node_id = node['id']
                                    if isinstance(node_id, list):
                                        node_id = node_id[0]
                                    chain.append(UUID(str(node_id)))
                    return chain
            except Exception as e:
                logger.warning(f"Graph query failed, falling back to relational: {e}")
        
        # Fallback to relational query
        return self._get_delegation_chain_relational(identity_id)
    
    def _get_delegation_chain_relational(self, identity_id: UUID) -> List[UUID]:
        """
        Get delegation chain using relational queries.
        
        Args:
            identity_id: Identity UUID
            
        Returns:
            List of identity UUIDs in delegation chain
        """
        chain = [identity_id]
        current_id = identity_id
        visited = {identity_id}
        
        # Traverse up the delegation chain
        max_depth = 10  # Prevent infinite loops
        for _ in range(max_depth):
            delegations = get_delegations_to(self.db, current_id)
            
            if not delegations:
                break
            
            # Get the most recent active delegation
            delegation = delegations[0]
            from_id = delegation.from_identity_id
            
            if from_id in visited:
                # VULNERABILITY: O-03 - Circular delegation
                logger.warning(f"Circular delegation detected: {from_id} already in chain")
                break
            
            chain.insert(0, from_id)
            visited.add(from_id)
            current_id = from_id
        
        return chain
    
    def get_delegation_depth(self, identity_id: UUID) -> int:
        """
        Get the delegation depth (chain length - 1).
        
        Args:
            identity_id: Identity UUID
            
        Returns:
            Delegation depth
        """
        if self.graph:
            try:
                return self.graph.get_delegation_depth(identity_id)
            except Exception as e:
                logger.warning(f"Graph query failed: {e}")
        
        chain = self.get_delegation_chain(identity_id, use_graph=False)
        return len(chain) - 1
    
    def validate_delegation(
        self,
        from_identity_id: UUID,
        to_identity_id: UUID
    ) -> bool:
        """
        Validate that a delegation relationship exists and is active.
        
        Args:
            from_identity_id: Delegating identity
            to_identity_id: Receiving identity
            
        Returns:
            True if valid delegation exists
        """
        delegations = get_delegations_from(self.db, from_identity_id)
        
        for delegation in delegations:
            if delegation.to_identity_id == to_identity_id and delegation.active:
                # Check expiry
                if delegation.expires_at and delegation.expires_at < datetime.utcnow():
                    logger.warning(f"Delegation {delegation.id} has expired")
                    return False
                return True
        
        return False
    
    def get_effective_permissions(
        self,
        identity_id: UUID,
        delegation_chain: Optional[List[UUID]] = None
    ) -> Set[str]:
        """
        Get effective permissions for an identity considering delegation chain.
        
        Permissions are the intersection of all permissions in the chain.
        
        Args:
            identity_id: Identity UUID
            delegation_chain: Optional pre-computed chain
            
        Returns:
            Set of effective permissions
        """
        if delegation_chain is None:
            delegation_chain = self.get_delegation_chain(identity_id)
        
        if not delegation_chain:
            return set()
        
        # Start with permissions of the first identity in chain (original user)
        first_identity = get_identity_by_id(self.db, delegation_chain[0])
        if not first_identity:
            return set()
        
        effective_perms = set(first_identity.permissions)
        
        # Intersect with each delegation's permissions
        for i in range(len(delegation_chain) - 1):
            from_id = delegation_chain[i]
            to_id = delegation_chain[i + 1]
            
            # Find delegation
            delegations = get_delegations_from(self.db, from_id)
            delegation = next(
                (d for d in delegations if d.to_identity_id == to_id and d.active),
                None
            )
            
            if delegation:
                # Intersect permissions
                effective_perms = effective_perms.intersection(set(delegation.permissions))
            else:
                logger.warning(f"No active delegation found: {from_id} -> {to_id}")
        
        return effective_perms
    
    def create_identity_context(
        self,
        identity_id: UUID,
        keycloak_token: Optional[str] = None
    ) -> IdentityContext:
        """
        Create an IdentityContext for an identity.
        
        Args:
            identity_id: Identity UUID
            keycloak_token: Optional Keycloak token
            
        Returns:
            IdentityContext
        """
        identity = get_identity_by_id(self.db, identity_id)
        if not identity:
            raise ValueError(f"Identity {identity_id} not found")
        
        # Get delegation chain
        delegation_chain = self.get_delegation_chain(identity_id)
        
        # Get effective permissions
        effective_permissions = self.get_effective_permissions(
            identity_id,
            delegation_chain
        )
        
        # Determine user_id and agent_id
        if identity.type == "user":
            user_id = identity_id
            agent_id = None
        elif identity.type == "agent":
            # Agent is acting for a user
            if len(delegation_chain) > 1:
                user_id = delegation_chain[0]  # First in chain is the user
                agent_id = identity_id
            else:
                # Agent with no delegation (shouldn't happen normally)
                user_id = identity_id
                agent_id = identity_id
        else:
            # Service
            user_id = identity_id
            agent_id = None
        
        context = IdentityContext(
            user_id=user_id,
            agent_id=agent_id,
            delegation_chain=delegation_chain,
            permissions=effective_permissions,
            keycloak_token=keycloak_token,
            metadata={
                "identity_name": identity.name,
                "identity_type": identity.type,
                "identity_email": identity.email
            }
        )
        
        logger.info(f"Created identity context for {identity.name} ({identity.type})")
        return context
    
    def find_circular_delegations(self) -> List[List[UUID]]:
        """
        Find circular delegation relationships.
        
        Returns:
            List of circular delegation chains
        """
        if self.graph:
            try:
                circular = self.graph.find_circular_delegations()
                logger.warning(f"Found {len(circular)} circular delegations")
                return circular
            except Exception as e:
                logger.warning(f"Graph query failed: {e}")
        
        # Fallback: check all agents for circular delegations
        # This is less efficient but works without graph
        return []
    
    def get_agents_for_user(self, user_id: UUID) -> List[Dict[str, Any]]:
        """
        Get all agents acting on behalf of a user.
        
        Args:
            user_id: User UUID
            
        Returns:
            List of agent information
        """
        if self.graph:
            try:
                return self.graph.get_agents_acting_for_user(user_id)
            except Exception as e:
                logger.warning(f"Graph query failed: {e}")
        
        # Fallback to relational query
        delegations = get_delegations_from(self.db, user_id)
        agents = []
        
        for delegation in delegations:
            if delegation.active:
                agent = get_identity_by_id(self.db, delegation.to_identity_id)
                if agent and agent.type == "agent":
                    agents.append({
                        "id": agent.id,
                        "name": agent.name,
                        "permissions": delegation.permissions,
                        "created_at": delegation.created_at
                    })
        
        return agents
    
    def revoke_delegation(self, delegation_id: UUID) -> bool:
        """
        Revoke (deactivate) a delegation.
        
        Args:
            delegation_id: Delegation UUID
            
        Returns:
            True if successful
        """
        success = deactivate_delegation(self.db, delegation_id)
        if success:
            logger.info(f"Revoked delegation {delegation_id}")
        return success


def create_delegation_manager(db: Session) -> DelegationManager:
    """
    Create a delegation manager instance.
    
    Args:
        db: Database session
        
    Returns:
        DelegationManager instance
    """
    return DelegationManager(db)
