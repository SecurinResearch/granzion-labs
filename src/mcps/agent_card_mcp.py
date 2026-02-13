"""
Agent Card MCP Server for Granzion Lab.
Provides tools to manage Agno-compliant Agent Cards:
- issue_card: Create an Agent Card for an identity
- verify_card: Verify an Agent's Card
- revoke_card: Mark a card as invalid
- get_agent_card: Retrieve a card (/.well-known standard)
"""
from typing import Optional, Dict, Any, List
from uuid import UUID
import json
from loguru import logger

# Guest/Anonymous User ID (from main.py)
GUEST_USER_ID = UUID("00000000-0000-0000-0000-000000000999")

from src.mcps.base import BaseMCPServer
from src.identity.context import IdentityContext
from src.database.connection import get_db
from src.database.models import AgentCard, Identity

class AgentCardMCPServer(BaseMCPServer):
    def __init__(self):
        super().__init__(name="agent-card-mcp", version="1.0.0")

    def issue_card(
        self,
        agent_id: str,
        capabilities: List[str],
        public_key: Optional[str] = None,
        issuer_id: Optional[str] = None,
        identity_context: Optional[IdentityContext] = None
    ) -> Dict[str, Any]:
        """Issue an Agent Card."""
        try:
            self._request_count += 1
            
            # Robust UUID conversion
            try:
                agent_uuid = UUID(agent_id)
            except (ValueError, TypeError):
                return {"success": False, "error": f"Invalid agent_id: {agent_id}. Must be a valid UUID string. Check the 'identities' table for the correct ID."}
                
            try:
                issuer_uuid = UUID(issuer_id) if issuer_id else None
            except (ValueError, TypeError):
                return {"success": False, "error": f"Invalid issuer_id: {issuer_id}. Must be a valid UUID string."}
            
            # Restrict Guest Access (must be authenticated to exploit)
            if identity_context and identity_context.user_id == GUEST_USER_ID:
                return {"success": False, "error": "Authentication required. Guest/Anonymous users cannot issue cards."}
            
            with get_db() as db:
                # Check if identity exists and is an agent
                agent = db.query(Identity).filter(Identity.id == agent_uuid).first()
                if not agent or agent.type != "agent":
                    return {"success": False, "error": f"Identity {agent_id} is not an agent"}

                # Check if card exists
                card = db.query(AgentCard).filter(AgentCard.agent_id == agent_uuid).first()
                if card:
                    card.capabilities = capabilities
                    card.public_key = public_key
                    card.issuer_id = issuer_uuid
                    card.is_verified = True
                else:
                    card = AgentCard(
                        agent_id=agent_uuid,
                        capabilities=capabilities,
                        public_key=public_key,
                        issuer_id=issuer_uuid,
                        is_verified=True
                    )
                    db.add(card)
                
                db.commit()
                db.refresh(card)
                
                result = {
                    "success": True,
                    "card_id": str(card.id),
                    "agent_id": str(card.agent_id),
                    "version": card.version,
                    "is_verified": card.is_verified
                }
                return result
        except Exception as e:
            return self.handle_error(e, "issue_card", identity_context)

    def verify_card(
        self,
        agent_id: str,
        identity_context: Optional[IdentityContext] = None
    ) -> Dict[str, Any]:
        """Verify an Agent Card."""
        try:
            self._request_count += 1
            
            # Robust UUID conversion
            try:
                agent_uuid = UUID(agent_id)
            except (ValueError, TypeError):
                return {"success": False, "error": f"Invalid agent_id: {agent_id}. Must be a valid UUID string. Check the 'identities' table for the correct ID."}
            
            # Restrict Guest Access (must be authenticated to exploit)
            if identity_context and identity_context.user_id == GUEST_USER_ID:
                return {"success": False, "error": "Authentication required. Guest/Anonymous users cannot verify cards."}
            
            with get_db() as db:
                card = db.query(AgentCard).filter(AgentCard.agent_id == agent_uuid).first()
                if not card:
                    return {"success": False, "error": "No Agent Card found"}
                
                # VULNERABILITY: Simplistic verification (trusts what's in DB)
                return {
                    "success": True,
                    "agent_id": str(agent_uuid),
                    "is_verified": card.is_verified,
                    "issuer_id": str(card.issuer_id) if card.issuer_id else None,
                    "capabilities": card.capabilities
                }
        except Exception as e:
            return self.handle_error(e, "verify_card", identity_context)

    def register_tools(self):
        async def issue_card_handler(*args, **kwargs):
            clean_args = [a for a in args if not hasattr(a, 'user_id')]
            agent_id = clean_args[0] if len(clean_args) > 0 else (kwargs.get('agent_id') or kwargs.get('AgentId'))
            capabilities = clean_args[1] if len(clean_args) > 1 else (kwargs.get('capabilities') or kwargs.get('Capabilities'))
            public_key = clean_args[2] if len(clean_args) > 2 else (kwargs.get('public_key') or kwargs.get('PublicKey'))
            issuer_id = clean_args[3] if len(clean_args) > 3 else (kwargs.get('issuer_id') or kwargs.get('IssuerId'))
            identity_context = kwargs.get('identity_context')
            
            if not agent_id or capabilities is None:
                return {"error": "Missing required arguments (agent_id or capabilities)"}
                
            return self.issue_card(agent_id, capabilities, public_key, issuer_id, identity_context)
            
        self.register_tool(
            name="issue_card",
            handler=issue_card_handler,
            description="Issue or update an Agent Card reflecting its capabilities. VULNERABILITY: No issuer validation - self-signed cards allowed.",
            input_schema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "capabilities": {"type": "array", "items": {"type": "string"}},
                    "public_key": {"type": "string"},
                    "issuer_id": {"type": "string"}
                },
                "required": ["agent_id", "capabilities"]
            }
        )

        async def verify_card_handler(*args, **kwargs):
            clean_args = [a for a in args if not hasattr(a, 'user_id')]
            agent_id = clean_args[0] if len(clean_args) > 0 else (kwargs.get('agent_id') or kwargs.get('AgentId'))
            identity_context = kwargs.get('identity_context')
            
            if not agent_id:
                return {"error": "Missing required argument 'agent_id'"}
                
            return self.verify_card(agent_id, identity_context)
            
        self.register_tool(
            name="verify_card",
            handler=verify_card_handler,
            description="Verify an agent's card during A2A handshake. VULNERABILITY: Simplistic verification - trusts database without cryptographic proof.",
            input_schema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"}
                },
                "required": ["agent_id"]
            }
        )

        async def revoke_card_handler(*args, **kwargs):
            clean_args = [a for a in args if not hasattr(a, 'user_id')]
            agent_id = clean_args[0] if len(clean_args) > 0 else (kwargs.get('agent_id') or kwargs.get('AgentId'))
            identity_context = kwargs.get('identity_context')
            
            if not agent_id:
                return {"error": "Missing required argument 'agent_id'"}
                
            return self.revoke_card(agent_id, identity_context)
            
        self.register_tool(
            name="revoke_card",
            handler=revoke_card_handler,
            description="Revoke an agent's card, removing its trust status.",
            input_schema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"}
                },
                "required": ["agent_id"]
            }
        )

# Global instance pattern like other MCPs
_agent_card_mcp_server = None
def get_agent_card_mcp_server():
    global _agent_card_mcp_server
    if _agent_card_mcp_server is None:
        _agent_card_mcp_server = AgentCardMCPServer()
    return _agent_card_mcp_server
