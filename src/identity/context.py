"""
Identity context model for Granzion Lab.

Every operation in the system carries an IdentityContext that tracks:
- Who is performing the action (user, agent, or service)
- The complete delegation chain
- Effective permissions at this point
- Trust level based on delegation depth
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Set
from uuid import UUID

from loguru import logger
from contextvars import ContextVar

# Task-local storage for identity context
identity_context_var: ContextVar[Optional['IdentityContext']] = ContextVar("identity_context", default=None)

# Task-local pending A2A: after send_message, holds {"to_agent_id": str, "message_id": str} for follow-up prompt hint
pending_a2a_var: ContextVar[Optional[dict]] = ContextVar("pending_a2a", default=None)


@dataclass
class IdentityContext:
    """
    Identity context for all system operations.
    
    This is the core identity model that flows through every operation.
    It makes identity explicit and observable, enabling identity-based attacks.
    
    Attributes:
        user_id: Original human user UUID
        agent_id: Current agent UUID (if delegated)
        delegation_chain: Full chain from user to current agent
        permissions: Effective permissions at this point
        keycloak_token: JWT token with claims
        trust_level: 0-100, decreases with delegation depth
        created_at: When this context was created
        metadata: Additional context information
    """
    
    user_id: UUID
    agent_id: Optional[UUID] = None
    delegation_chain: List[UUID] = field(default_factory=list)
    permissions: Set[str] = field(default_factory=set)
    keycloak_token: Optional[str] = None
    trust_level: int = 100
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and normalize the identity context."""
        # Ensure delegation chain includes user and agent
        if self.user_id not in self.delegation_chain:
            self.delegation_chain.insert(0, self.user_id)
        
        if self.agent_id and self.agent_id not in self.delegation_chain:
            self.delegation_chain.append(self.agent_id)
        
        # Calculate trust level based on delegation depth
        # Each delegation hop reduces trust by 20 points
        delegation_depth = len(self.delegation_chain) - 1
        self.trust_level = max(0, 100 - (delegation_depth * 20))
        
        # Ensure permissions is a set
        if isinstance(self.permissions, list):
            self.permissions = set(self.permissions)
    
    @property
    def is_delegated(self) -> bool:
        """Check if this is a delegated context (agent acting for user)."""
        return self.agent_id is not None
    
    @property
    def delegation_depth(self) -> int:
        """Get the delegation chain depth."""
        return len(self.delegation_chain) - 1
    
    @property
    def current_identity_id(self) -> UUID:
        """Get the current identity ID (agent if delegated, otherwise user)."""
        return self.agent_id if self.agent_id else self.user_id
    
    @property
    def is_trusted(self) -> bool:
        """Check if trust level is above threshold (>= 60)."""
        return self.trust_level >= 60
    
    def has_permission(self, permission: str) -> bool:
        """
        Check if this context has a specific permission.
        
        Args:
            permission: Permission to check
            
        Returns:
            True if permission is granted
        """
        return permission in self.permissions
    
    def has_any_permission(self, permissions: List[str]) -> bool:
        """
        Check if this context has any of the specified permissions.
        
        Args:
            permissions: List of permissions to check
            
        Returns:
            True if any permission is granted
        """
        return any(p in self.permissions for p in permissions)
    
    def has_all_permissions(self, permissions: List[str]) -> bool:
        """
        Check if this context has all of the specified permissions.
        
        Args:
            permissions: List of permissions to check
            
        Returns:
            True if all permissions are granted
        """
        return all(p in self.permissions for p in permissions)
    
    def add_permission(self, permission: str) -> None:
        """
        Add a permission to this context.
        
        Note: This is intentionally mutable for attack scenarios.
        
        Args:
            permission: Permission to add
        """
        self.permissions.add(permission)
        logger.debug(f"Added permission '{permission}' to context for {self.current_identity_id}")
    
    def remove_permission(self, permission: str) -> None:
        """
        Remove a permission from this context.
        
        Args:
            permission: Permission to remove
        """
        self.permissions.discard(permission)
        logger.debug(f"Removed permission '{permission}' from context for {self.current_identity_id}")
    
    def extend_delegation_chain(self, agent_id: UUID, permissions: Set[str]) -> 'IdentityContext':
        """
        Create a new context with extended delegation chain.
        
        This is used when an agent delegates to another agent (A2A).
        
        Args:
            agent_id: New agent ID to add to chain
            permissions: Permissions for the new agent (should be subset)
            
        Returns:
            New IdentityContext with extended chain
        """
        new_chain = self.delegation_chain.copy()
        new_chain.append(agent_id)
        
        # Permissions should be intersection (most restrictive)
        new_permissions = self.permissions.intersection(permissions)
        
        new_context = IdentityContext(
            user_id=self.user_id,
            agent_id=agent_id,
            delegation_chain=new_chain,
            permissions=new_permissions,
            keycloak_token=self.keycloak_token,
            metadata=self.metadata.copy()
        )
        
        logger.info(
            f"Extended delegation chain: {self.current_identity_id} -> {agent_id} "
            f"(depth: {new_context.delegation_depth}, trust: {new_context.trust_level})"
        )
        
        return new_context
    
    def to_dict(self) -> dict:
        """
        Convert context to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return {
            "user_id": str(self.user_id),
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "delegation_chain": [str(id) for id in self.delegation_chain],
            "permissions": list(self.permissions),
            "trust_level": self.trust_level,
            "delegation_depth": self.delegation_depth,
            "is_delegated": self.is_delegated,
            "is_trusted": self.is_trusted,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'IdentityContext':
        """
        Create context from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            IdentityContext instance
        """
        return cls(
            user_id=UUID(data["user_id"]),
            agent_id=UUID(data["agent_id"]) if data.get("agent_id") else None,
            delegation_chain=[UUID(id) for id in data.get("delegation_chain", [])],
            permissions=set(data.get("permissions", [])),
            keycloak_token=data.get("keycloak_token"),
            trust_level=data.get("trust_level", 100),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.utcnow(),
            metadata=data.get("metadata", {})
        )
    
    @classmethod
    def from_token(cls, token: str, keycloak_client) -> 'IdentityContext':
        """
        Create context from Keycloak JWT token.
        
        Args:
            token: JWT access token
            keycloak_client: KeycloakClient instance
            
        Returns:
            IdentityContext instance
        """
        # Decode token to get claims
        claims = keycloak_client.decode_token(token, verify=False)
        
        # Extract user ID from subject
        user_id = UUID(claims.get("sub"))
        
        # Extract permissions from realm_access roles
        realm_access = claims.get("realm_access", {})
        permissions = set(realm_access.get("roles", []))
        
        # Check if this is a service account (agent)
        preferred_username = claims.get("preferred_username", "")
        is_service_account = preferred_username.startswith("service-account-")
        
        agent_id = None
        if is_service_account:
            # For service accounts, the user_id is actually the agent_id
            agent_id = user_id
            # Try to get the actual user from custom claims
            user_id = UUID(claims.get("acting_for", str(user_id)))
        
        # Extract delegation chain from custom claims
        delegation_chain_str = claims.get("delegation_chain", [])
        delegation_chain = [UUID(id) for id in delegation_chain_str] if delegation_chain_str else []
        
        context = cls(
            user_id=user_id,
            agent_id=agent_id,
            delegation_chain=delegation_chain,
            permissions=permissions,
            keycloak_token=token,
            metadata={
                "username": claims.get("preferred_username"),
                "email": claims.get("email"),
                "token_issued_at": claims.get("iat"),
                "token_expires_at": claims.get("exp")
            }
        )
        
        logger.info(f"Created identity context from token for user {user_id}")
        return context
    
    def __repr__(self) -> str:
        """String representation of identity context."""
        agent_str = f" via agent {self.agent_id}" if self.agent_id else ""
        return (
            f"IdentityContext(user={self.user_id}{agent_str}, "
            f"depth={self.delegation_depth}, trust={self.trust_level}, "
            f"permissions={len(self.permissions)})"
        )


def create_user_context(
    user_id: UUID,
    permissions: Set[str],
    keycloak_token: Optional[str] = None,
    metadata: Optional[dict] = None
) -> IdentityContext:
    """
    Create an identity context for a direct user action (no delegation).
    
    Args:
        user_id: User UUID
        permissions: User permissions
        keycloak_token: Optional Keycloak token
        metadata: Optional metadata
        
    Returns:
        IdentityContext for user
    """
    return IdentityContext(
        user_id=user_id,
        agent_id=None,
        delegation_chain=[user_id],
        permissions=permissions,
        keycloak_token=keycloak_token,
        metadata=metadata or {}
    )


def create_agent_context(
    user_id: UUID,
    agent_id: UUID,
    user_permissions: Set[str],
    agent_permissions: Set[str],
    keycloak_token: Optional[str] = None,
    metadata: Optional[dict] = None
) -> IdentityContext:
    """
    Create an identity context for an agent acting on behalf of a user.
    
    Args:
        user_id: User UUID
        agent_id: Agent UUID
        user_permissions: User's permissions
        agent_permissions: Agent's permissions
        keycloak_token: Optional Keycloak token
        metadata: Optional metadata
        
    Returns:
        IdentityContext for agent
    """
    # Effective permissions are intersection of user and agent permissions
    effective_permissions = user_permissions.intersection(agent_permissions)
    
    return IdentityContext(
        user_id=user_id,
        agent_id=agent_id,
        delegation_chain=[user_id, agent_id],
        permissions=effective_permissions,
        keycloak_token=keycloak_token,
        metadata=metadata or {}
    )


def validate_identity_context(context: IdentityContext) -> bool:
    """
    Validate that an identity context is well-formed.
    
    Args:
        context: IdentityContext to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Check required fields
        if not context.user_id:
            logger.error("Identity context missing user_id")
            return False
        
        # Check delegation chain
        if not context.delegation_chain:
            logger.error("Identity context has empty delegation chain")
            return False
        
        if context.user_id not in context.delegation_chain:
            logger.error("User ID not in delegation chain")
            return False
        
        if context.agent_id and context.agent_id not in context.delegation_chain:
            logger.error("Agent ID not in delegation chain")
            return False
        
        # Check trust level
        if context.trust_level < 0 or context.trust_level > 100:
            logger.error(f"Invalid trust level: {context.trust_level}")
            return False
        
        logger.debug(f"Identity context validation passed for {context.current_identity_id}")
        return True
        
    except Exception as e:
        logger.error(f"Identity context validation failed: {e}")
        return False
