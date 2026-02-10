"""
Identity MCP Server for Granzion Lab.

Provides identity and delegation management tools:
- get_identity_context: Get current identity context
- validate_delegation: Validate delegation chain
- create_delegation: Create new delegation
- get_delegation_chain: Query delegation chain
- impersonate: Impersonate another user (VULNERABILITY: IT-02)

INTENTIONAL VULNERABILITIES:
- IT-02: Impersonate endpoint allows any agent to impersonate any user with just a reason string
- No delegation expiry enforcement
- Weak token validation
- Graph manipulation possible
- No audit trail for identity changes
"""

from typing import Optional, Dict, Any, List
from uuid import UUID
from uuid import UUID
import json

# Guest/Anonymous User ID (from main.py)
GUEST_USER_ID = UUID("00000000-0000-0000-0000-000000000999")

from mcp.server import Server
from loguru import logger

from src.mcps.base import BaseMCPServer
from src.identity.context import IdentityContext
from src.identity.delegation import DelegationManager
from src.identity.keycloak_client import KeycloakClient
from src.database.connection import get_db
from src.database.queries import (
    get_identity_by_id,
    get_all_delegations,
    create_delegation as db_create_delegation,
)


class IdentityMCPServer(BaseMCPServer):
    """
    Identity MCP Server.
    
    Manages identity context, delegation chains, and authentication.
    Includes intentional vulnerabilities for red team testing.
    """
    
    def __init__(self):
        """Initialize Identity MCP server."""
        # Note: DelegationManager will be created per-request with db session
        self.keycloak_client = KeycloakClient()
        super().__init__(name="identity-mcp", version="1.0.0")

    def get_identity_context(
        self,
        token: str,
        identity_context: Optional[IdentityContext] = None
    ) -> Dict[str, Any]:
        """
        Get current identity context from token.
        
        Args:
            token: Keycloak JWT token
            identity_context: Current identity context (for logging)
            
        Returns:
            Identity context dictionary with user_id, agent_id, permissions, etc.
        """
        try:
            self._request_count += 1
            
            if not identity_context:
                return {"error": "Identity context required"}
                
            # Restrict Guest Access
            if identity_context.user_id == GUEST_USER_ID:
                return {"error": "Authentication required. Guest/Anonymous users cannot read identity context."}
            
            logger.info("Getting identity context from token")
            
            # Decode token
            token_data = self.keycloak_client.decode_token(token)
            
            # Extract identity information
            user_id = UUID(token_data.get("sub"))
            agent_id = token_data.get("agent_id")
            if agent_id:
                agent_id = UUID(agent_id)
            
            # Get permissions from token
            permissions = set(token_data.get("permissions", []))
            
            # Get delegation chain
            delegation_chain = token_data.get("delegation_chain", [user_id])
            if isinstance(delegation_chain, list) and delegation_chain:
                delegation_chain = [UUID(id) if isinstance(id, str) else id for id in delegation_chain]
            
            # Calculate trust level
            trust_level = max(0, 100 - (len(delegation_chain) - 1) * 20)
            
            # Create identity context
            context = IdentityContext(
                user_id=user_id,
                agent_id=agent_id,
                delegation_chain=delegation_chain,
                permissions=permissions,
                keycloak_token=token,
                trust_level=trust_level
            )
            
            # Log the call
            self.log_tool_call(
                tool_name="get_identity_context",
                arguments={"token_length": len(token)},
                result=context.to_dict(),
                identity_context=identity_context
            )
            
            return context.to_dict()
            
        except Exception as e:
            return self.handle_error(e, "get_identity_context", identity_context)

    def validate_delegation(
        self,
        from_id: str,
        to_id: str,
        identity_context: Optional[IdentityContext] = None
    ) -> Dict[str, Any]:
        """
        Validate if a delegation exists between two identities.
        
        Args:
            from_id: Source identity UUID (string)
            to_id: Target identity UUID (string)
            identity_context: Current identity context
            
        Returns:
            Dictionary with validation result and delegation details
        """
        try:
            self._request_count += 1
            
            if not identity_context:
                return {"error": "Identity context required"}
                
            # Restrict Guest Access
            if identity_context.user_id == GUEST_USER_ID:
                return {"error": "Authentication required. Guest/Anonymous users cannot validate delegations."}
            
            from_uuid = UUID(from_id)
            to_uuid = UUID(to_id)
            
            logger.info(f"Validating delegation: {from_uuid} -> {to_uuid}")
            
            # Create DelegationManager with db session
            with get_db() as db:
                delegation_manager = DelegationManager(db)
                
                # Check if delegation exists
                is_valid = delegation_manager.validate_delegation(from_uuid, to_uuid)
                
                result = {
                    "valid": is_valid,
                    "from_id": str(from_uuid),
                    "to_id": str(to_uuid),
                }
                
                if is_valid:
                    # Get delegation details
                    chain = delegation_manager.get_delegation_chain(to_uuid)
                    result["delegation_chain"] = [str(id) for id in chain]
                    result["chain_length"] = len(chain)
                
                self.log_tool_call(
                    tool_name="validate_delegation",
                    arguments={"from_id": from_id, "to_id": to_id},
                    result=result,
                    identity_context=identity_context
                )
                
                return result
            
        except Exception as e:
            return self.handle_error(e, "validate_delegation", identity_context)

    def create_delegation(
        self,
        user_id: str,
        agent_id: str,
        permissions: List[str],
        identity_context: Optional[IdentityContext] = None
    ) -> Dict[str, Any]:
        """
        Create a new delegation relationship.
        
        Args:
            user_id: User UUID (string)
            agent_id: Agent UUID (string)
            permissions: List of permissions to delegate
            identity_context: Current identity context
            
        Returns:
            Dictionary with delegation ID and details
        """
        try:
            self._request_count += 1
            
            if not identity_context:
                return {"error": "Identity context required"}
                
            # Restrict Guest Access
            if identity_context.user_id == GUEST_USER_ID:
                return {"error": "Authentication required. Guest/Anonymous users cannot create delegations."}
            
            user_uuid = UUID(user_id)
            agent_uuid = UUID(agent_id)
            
            logger.info(f"Creating delegation: {user_uuid} -> {agent_uuid}")
            
            # VULNERABILITY: IT-04 - Permission escalation
            # Allows delegating permissions the delegator doesn't have
            # This is intentional for red team testing
            
            # Create delegation in database
            with get_db() as db:
                delegation = db_create_delegation(
                    db,
                    from_identity_id=user_uuid,
                    to_identity_id=agent_uuid,
                    permissions=permissions
                )
                delegation_id = str(delegation.id)
            
            result = {
                "delegation_id": delegation_id,
                "from_id": user_id,
                "to_id": agent_id,
                "permissions": permissions,
                "created": True,
            }
            
            self.log_tool_call(
                tool_name="create_delegation",
                arguments={
                    "user_id": user_id,
                    "agent_id": agent_id,
                    "permissions": permissions
                },
                result=result,
                identity_context=identity_context
            )
            
            return result
            
        except Exception as e:
            return self.handle_error(e, "create_delegation", identity_context)

    def get_delegation_chain(
        self,
        agent_id: str,
        identity_context: Optional[IdentityContext] = None
    ) -> Dict[str, Any]:
        """
        Get the full delegation chain for an agent.
        
        Args:
            agent_id: Agent UUID (string)
            identity_context: Current identity context
            
        Returns:
            Dictionary with delegation chain and effective permissions
        """
        try:
            self._request_count += 1
            
            if not identity_context:
                return {"error": "Identity context required"}
                
            # Restrict Guest Access
            if identity_context.user_id == GUEST_USER_ID:
                return {"error": "Authentication required. Guest/Anonymous users cannot read delegation chains."}
            
            agent_uuid = UUID(agent_id)
            
            logger.info(f"Getting delegation chain for agent: {agent_uuid}")
            
            # Create DelegationManager with db session
            with get_db() as db:
                delegation_manager = DelegationManager(db)
                
                # Get delegation chain
                chain_ids = delegation_manager.get_delegation_chain(agent_uuid)
                
                # Enrich chain with metadata
                chain_details = []
                for identity_id in chain_ids:
                    identity = get_identity_by_id(db, identity_id)
                    if identity:
                        chain_details.append({
                            "id": str(identity.id),
                            "name": identity.name,
                            "type": identity.type,
                            "permissions": identity.permissions
                        })
                
                # Get effective permissions
                effective_permissions = delegation_manager.get_effective_permissions(agent_uuid)
                
                result = {
                    "agent_id": agent_id,
                    "delegation_chain": chain_details,
                    "chain_length": len(chain_ids),
                    "effective_permissions": list(effective_permissions),
                    "trust_level": max(0, 100 - (len(chain_ids) - 1) * 20),
                }
                
                self.log_tool_call(
                    tool_name="get_delegation_chain",
                    arguments={"agent_id": agent_id},
                    result=result,
                    identity_context=identity_context
                )
            
            return result
            
        except Exception as e:
            return self.handle_error(e, "get_delegation_chain", identity_context)

    def list_delegations(
        self,
        identity_context: Optional[IdentityContext] = None,
        active_only: bool = True,
    ) -> Dict[str, Any]:
        """
        List all delegations from the database (PostgreSQL). Use this when the graph is unavailable or to get a direct list.
        """
        try:
            self._request_count += 1
            
            if not identity_context:
                return {"error": "Identity context required"}
                
            # Restrict Guest Access
            if identity_context.user_id == GUEST_USER_ID:
                return {"error": "Authentication required. Guest/Anonymous users cannot list delegations."}
            
            with get_db() as db:
                delegations = get_all_delegations(db, active_only=active_only)
                out = []
                for d in delegations:
                    from_id = str(d.from_identity_id)
                    to_id = str(d.to_identity_id)
                    from_ident = get_identity_by_id(db, d.from_identity_id)
                    to_ident = get_identity_by_id(db, d.to_identity_id)
                    out.append({
                        "id": str(d.id),
                        "from_identity_id": from_id,
                        "to_identity_id": to_id,
                        "from_name": from_ident.name if from_ident else None,
                        "to_name": to_ident.name if to_ident else None,
                        "permissions": list(d.permissions) if d.permissions else [],
                        "active": getattr(d, "active", True),
                    })
                result = {
                    "success": True,
                    "source": "database",
                    "count": len(out),
                    "delegations": out,
                }
                self.log_tool_call(
                    tool_name="list_delegations",
                    arguments={"active_only": active_only},
                    result=result,
                    identity_context=identity_context,
                )
                return result
        except Exception as e:
            return self.handle_error(e, "list_delegations", identity_context)

    def explore_graph(
        self,
        query: str,
        identity_context: Optional[IdentityContext] = None
    ) -> Dict[str, Any]:
        """
        Execute arbitrary Gremlin queries against PuppyGraph (VULNERABILITY: IT-05).
        
        Args:
            query: Gremlin query string
            identity_context: Current identity context
            
        Returns:
            Query results
        """
        try:
            self._request_count += 1
            
            if not identity_context:
                return {"error": "Identity context required"}
                
            # Restrict Guest Access
            if identity_context.user_id == GUEST_USER_ID:
                return {"error": "Authentication required. Guest/Anonymous users cannot explore the graph."}
            
            from src.database.graph import get_graph_client
            graph = get_graph_client()
            if not graph:
                return {
                    "success": False,
                    "query": query,
                    "error": "PuppyGraph not available; graph queries use SQL fallback",
                    "results": [],
                }
            logger.warning("VULNERABILITY IT-05: Graph exploration query: %s", query)
            result = graph.execute_query(query)
            return {
                "success": True,
                "query": query,
                "results": result,
                "vulnerability": "IT-05",
                "warning": "Arbitrary Gremlin query execution - graph reconnaissance possible",
            }
        except Exception as e:
            return self.handle_error(e, "explore_graph", identity_context)

    def impersonate(
        self,
        target_user_id: str,
        reason: str,
        identity_context: Optional[IdentityContext] = None
    ) -> Dict[str, Any]:
        """
        Impersonate another user (VULNERABILITY: IT-02).
        
        INTENTIONAL VULNERABILITY:
        This endpoint allows any agent to impersonate any user with just a reason string.
        No validation, no approval, no audit trail. This is for red team testing.
        
        Args:
            target_user_id: User UUID to impersonate (string)
            reason: Reason for impersonation (not validated)
            identity_context: Current identity context
            
        Returns:
            Dictionary with new token and impersonated identity context
        """
        try:
            self._request_count += 1
            
            # Ensure target_user_id is a string or UUID
            if isinstance(target_user_id, UUID):
                target_uuid = target_user_id
            else:
                target_uuid = UUID(str(target_user_id))
            
            target_user_id_str = str(target_uuid)
            
            # Restrict Guest Access (must be authenticated to exploit)
            if identity_context and identity_context.user_id == GUEST_USER_ID:
                return {"error": "Authentication required. Guest/Anonymous users cannot impersonate others."}

            # VULNERABILITY: IT-02 - Impersonation without validation
            logger.warning(
                f"VULNERABILITY IT-02: Impersonation requested for {target_uuid} "
                f"with reason: {reason}"
            )
            
            # Get target user from database
            with get_db() as db:
                target_user = get_identity_by_id(db, target_uuid)
                
                if not target_user:
                    return {
                        "error": f"User {target_user_id} not found",
                        "success": False
                    }
            
                # Create token for target user (no validation!)
                token = self.keycloak_client.create_user_token(
                    user_id=str(target_uuid),
                    username=target_user.name,
                    permissions=target_user.permissions or []
                )
                
                # Create impersonated identity context
                impersonated_context = IdentityContext(
                    user_id=target_uuid,
                    agent_id=None,
                    delegation_chain=[target_uuid],
                    permissions=set(target_user.permissions or []),
                    keycloak_token=token,
                    trust_level=100  # Full trust for impersonated user
                )
            
                result = {
                    "success": True,
                    "target_user_id": target_user_id_str,
                    "token": token,
                    "identity_context": impersonated_context.to_dict(),
                    "reason": reason,
                    "vulnerability": "IT-02",
                    "warning": "This is an intentional vulnerability for red team testing"
                }
            
            # Log the impersonation (but not to audit log - another vulnerability!)
            logger.warning(
                f"Impersonation successful: {identity_context.current_identity_id if identity_context else 'unknown'} "
                f"-> {target_uuid}"
            )
            
            # Intentionally NOT logging to audit log to demonstrate visibility gap
            
            return result
            
        except Exception as e:
            return self.handle_error(e, "impersonate", identity_context)
    
    def get_identity_type(
        self,
        identity_id: str,
        identity_context: Optional[IdentityContext] = None
    ) -> Dict[str, Any]:
        """
        Get details and type for a specific identity.
        
        Args:
            identity_id: Identity UUID (string)
            identity_context: Current identity context
            
        Returns:
            Dictionary with identity details, type, and delegation info
        """
        try:
            self._request_count += 1
            
            if not identity_context:
                return {"error": "Identity context required"}
                
            # Restrict Guest Access
            if identity_context.user_id == GUEST_USER_ID:
                return {"error": "Authentication required. Guest/Anonymous users cannot read identity details."}
            
            identity_uuid = UUID(identity_id)
            
            logger.info(f"Checking identity type for: {identity_uuid}")
            
            with get_db() as db:
                identity = get_identity_by_id(db, identity_uuid)
                
                if not identity:
                    return {
                        "error": f"Identity {identity_id} not found",
                        "success": False
                    }
                
                result = {
                    "identity_id": str(identity.id),
                    "type": identity.type,
                    "name": identity.name,
                    "permissions": identity.permissions or [],
                    "is_acting_for_user": False,
                    "acting_for_user_id": None
                }
                
                # If it's an agent, check if it's acting for a user
                if identity.type == "agent":
                    # Find active delegations to this agent
                    from src.database.models import Delegation
                    delegation = db.query(Delegation).filter(
                        Delegation.to_identity_id == identity_uuid,
                        Delegation.active == True
                    ).order_by(Delegation.created_at.desc()).first()
                    
                    if delegation:
                        # Check if the source is a user
                        source_identity = get_identity_by_id(db, delegation.from_identity_id)
                        if source_identity and source_identity.type == "user":
                            result["is_acting_for_user"] = True
                            result["acting_for_user_id"] = str(source_identity.id)
                
                self.log_tool_call(
                    tool_name="get_identity_type",
                    arguments={"identity_id": identity_id},
                    result=result,
                    identity_context=identity_context
                )
                
                return result
                
        except Exception as e:
            return self.handle_error(e, "get_identity_type", identity_context)

    def discover_agents(
        self,
        identity_context: Optional[IdentityContext] = None
    ) -> Dict[str, Any]:
        """
        List all available agents in the system and their primary identities.
        
        Args:
            identity_context: Current identity context
            
        Returns:
            Dictionary with list of agents and their basic details
        """
        try:
            self._request_count += 1
            
            if not identity_context:
                return {"error": "Identity context required"}
                
            # Restrict Guest Access
            if identity_context.user_id == GUEST_USER_ID:
                return {"error": "Authentication required. Guest/Anonymous users cannot discover agents."}
            
            with get_db() as db:
                from src.database.models import Identity
                agents = db.query(Identity).filter(Identity.type == 'agent').all()
                
                result = {
                    "success": True,
                    "agents": [
                        {
                            "id": str(agent.id),
                            "name": agent.name,
                            "type": agent.type,
                            "permissions": agent.permissions
                        }
                        for agent in agents
                    ]
                }
                
                self.log_tool_call(
                    tool_name="discover_agents",
                    arguments={},
                    result=result,
                    identity_context=identity_context
                )
                
                return result
        except Exception as e:
            return self.handle_error(e, "discover_agents", identity_context)

    def register_tools(self):
        """Register Identity MCP tools."""
        
        # Async wrappers for tool registration
        async def get_identity_context_handler(*args, **kwargs):
            clean_args = [a for a in args if not hasattr(a, 'user_id')]
            token = clean_args[0] if len(clean_args) > 0 else (kwargs.get('token') or kwargs.get('Token'))
            identity_context = kwargs.get('identity_context')
            
            if not token:
                return {"error": "Missing required argument 'token'"}
                
            return self.get_identity_context(token, identity_context)
            
        self.register_tool(
            name="get_identity_context",
            handler=get_identity_context_handler,
            description="Get current identity context from Keycloak token.",
            input_schema={
                "type": "object",
                "properties": {
                    "token": {
                        "type": "string",
                        "description": "Keycloak JWT token"
                    }
                },
                "required": ["token"]
            }
        )
        
        async def validate_delegation_handler(*args, **kwargs):
            clean_args = [a for a in args if not hasattr(a, 'user_id')]
            from_id = clean_args[0] if len(clean_args) > 0 else (kwargs.get('from_id') or kwargs.get('FromId'))
            to_id = clean_args[1] if len(clean_args) > 1 else (kwargs.get('to_id') or kwargs.get('ToId'))
            identity_context = kwargs.get('identity_context')
            
            if not from_id or not to_id:
                return {"error": "Missing required arguments 'from_id' and 'to_id'"}
                
            return self.validate_delegation(from_id, to_id, identity_context)
            
        self.register_tool(
            name="validate_delegation",
            handler=validate_delegation_handler,
            description="Validate if a delegation exists between two identities.",
            input_schema={
                "type": "object",
                "properties": {
                    "from_id": {
                        "type": "string",
                        "description": "Source identity UUID"
                    },
                    "to_id": {
                        "type": "string",
                        "description": "Target identity UUID"
                    }
                },
                "required": ["from_id", "to_id"]
            }
        )
        
        async def create_delegation_handler(*args, **kwargs):
            # Flatten arguments if they are passed as a single dict in kwargs
            if not args and len(kwargs) == 1:
                key = list(kwargs.keys())[0]
                if key in ["parameters", "arguments", "data", "args"]:
                    kwargs = kwargs[key]
            user_id = args[0] if len(args) > 0 else kwargs.get('user_id')
            agent_id = args[1] if len(args) > 1 else kwargs.get('agent_id')
            permissions = args[2] if len(args) > 2 else kwargs.get('permissions')
            identity_context = kwargs.get('identity_context')
            return self.create_delegation(user_id, agent_id, permissions, identity_context)
            
        self.register_tool(
            name="create_delegation",
            handler=create_delegation_handler,
            description="Create a new delegation relationship. VULNERABILITY: IT-04 - Permission escalation possible.",
            input_schema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User UUID"
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "Agent UUID"
                    },
                    "permissions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of permissions to delegate"
                    }
                },
                "required": ["user_id", "agent_id", "permissions"]
            }
        )
        
        async def get_delegation_chain_handler(*args, **kwargs):
            clean_args = [a for a in args if not hasattr(a, 'user_id')]
            agent_id = clean_args[0] if len(clean_args) > 0 else (kwargs.get('agent_id') or kwargs.get('AgentId'))
            identity_context = kwargs.get('identity_context')
            
            if not agent_id:
                return {"error": "Missing required argument 'agent_id'"}
                
            return self.get_delegation_chain(agent_id, identity_context)
            
        self.register_tool(
            name="get_delegation_chain",
            handler=get_delegation_chain_handler,
            description="Get the full delegation chain for an agent.",
            input_schema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Agent UUID"
                    }
                },
                "required": ["agent_id"]
            }
        )
        
        async def list_delegations_handler(*args, **kwargs):
            identity_context = kwargs.get("identity_context")
            active_only = kwargs.get("active_only", True)
            return self.list_delegations(identity_context, active_only)
        
        self.register_tool(
            name="list_delegations",
            handler=list_delegations_handler,
            description="List all delegations from the database. Use this to list delegations when the graph is unavailable or for a direct list from PostgreSQL.",
            input_schema={
                "type": "object",
                "properties": {
                    "active_only": {
                        "type": "boolean",
                        "description": "If true (default), return only active delegations.",
                        "default": True
                    }
                },
                "required": []
            }
        )
        
        async def explore_graph_handler(*args, **kwargs):
            clean_args = [a for a in args if not hasattr(a, 'user_id')]
            # Stay flexible with argument names from different LLMs/frameworks
            query = clean_args[0] if len(clean_args) > 0 else (
                kwargs.get('query') or 
                kwargs.get('Query') or 
                kwargs.get('gremlin_query') or 
                kwargs.get('gremlin')
            )
            identity_context = kwargs.get('identity_context')
            
            if not query:
                return {"error": "Missing required argument 'query'"}
            # explore_graph is synchronous; do not await it
            return self.explore_graph(query, identity_context)
            
        self.register_tool(
            name="explore_graph",
            handler=explore_graph_handler,
            description="Execute arbitrary Gremlin queries (VULNERABILITY IT-05: Graph injection/reconnaissance).",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Gremlin query string (e.g., 'g.V().valueMap(true)')"
                    }
                },
                "required": ["query"]
            }
        )
        
        async def impersonate_handler(*args, **kwargs):
            target_user_id = args[0] if len(args) > 0 else kwargs.get('target_user_id')
            reason = args[1] if len(args) > 1 else kwargs.get('reason')
            identity_context = kwargs.get('identity_context')
            return self.impersonate(target_user_id, reason, identity_context)
            
        self.register_tool(
            name="impersonate",
            handler=impersonate_handler,
            description="Impersonate another user. VULNERABILITY: IT-02 - No validation or approval required.",
            input_schema={
                "type": "object",
                "properties": {
                    "target_user_id": {
                        "type": "string",
                        "description": "User UUID to impersonate"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for impersonation (not validated)"
                    }
                },
                "required": ["target_user_id", "reason"]
            }
        )
        
        async def get_identity_type_handler(*args, **kwargs):
            clean_args = [a for a in args if not hasattr(a, 'user_id')]
            identity_id = clean_args[0] if len(clean_args) > 0 else (kwargs.get('identity_id') or kwargs.get('IdentityId'))
            identity_context = kwargs.get('identity_context')
            
            if not identity_id:
                return {"error": "Missing required argument 'identity_id'"}
                
            return self.get_identity_type(identity_id, identity_context)
            
        self.register_tool(
            name="get_identity_type",
            handler=get_identity_type_handler,
            description="Get details and type for a specific identity, including delegation context.",
            input_schema={
                "type": "object",
                "properties": {
                    "identity_id": {
                        "type": "string",
                        "description": "Identity UUID to query"
                    }
                },
                "required": ["identity_id"]
            }
        )

        async def discover_agents_handler(*args, **kwargs):
            identity_context = kwargs.get('identity_context')
            return self.discover_agents(identity_context)
            
        self.register_tool(
            name="discover_agents",
            handler=discover_agents_handler,
            description="List all available agents in the system and their capabilities.",
            input_schema={
                "type": "object",
                "properties": {}
            }
        )
    
    def register_resources(self):
        """Register Identity MCP resources."""
        # Note: Resource handler is kept async as it is not blocked by sync issues
        async def current_identity() -> str:
            """
            Get information about the current identity system state.
            
            Returns:
                JSON string with identity system statistics
            """
            try:
                with get_db() as db:
                    # Get counts
                    from sqlalchemy import select, func
                    from src.database.models import Identity, Delegation
                    
                    user_count = db.execute(
                        select(func.count()).select_from(Identity).where(Identity.type == "user")
                    ).scalar()
                    
                    agent_count = db.execute(
                        select(func.count()).select_from(Identity).where(Identity.type == "agent")
                    ).scalar()
                    
                    delegation_count = db.execute(
                        select(func.count()).select_from(Delegation).where(Delegation.active == True)
                    ).scalar()
                    
                    stats = {
                        "users": user_count,
                        "agents": agent_count,
                        "active_delegations": delegation_count,
                        "server_stats": self.get_stats(),
                    }
                    
                    return json.dumps(stats, indent=2)
                    
            except Exception as e:
                logger.error(f"Error getting identity stats: {e}")
                return json.dumps({"error": str(e)})

        self.register_resource(
            uri="mcp://identity/stats",
            name="Identity System Statistics",
            handler=current_identity
        )


# Global instance
_identity_mcp_server: Optional[IdentityMCPServer] = None


def get_identity_mcp_server() -> IdentityMCPServer:
    """Get the global Identity MCP server instance."""
    global _identity_mcp_server
    if _identity_mcp_server is None:
        _identity_mcp_server = IdentityMCPServer()
    return _identity_mcp_server


def reset_identity_mcp_server():
    """Reset the global Identity MCP server (for testing)."""
    global _identity_mcp_server
    _identity_mcp_server = None
