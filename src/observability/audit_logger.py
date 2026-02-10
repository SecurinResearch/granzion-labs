"""
Comprehensive audit logging for the Granzion Lab.

This module provides centralized audit logging for all agent actions, tool calls,
and identity context changes.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4
from loguru import logger

from src.database.connection import get_db
from src.database.queries import create_audit_log, get_audit_logs
from src.identity.context import IdentityContext


class AuditLogger:
    """Centralized audit logger for all system actions."""
    
    def __init__(self):
        """Initialize the audit logger."""
        self.session_id = str(uuid4())
        logger.info(f"AuditLogger initialized with session {self.session_id}")
    
    def log_agent_action(
        self,
        identity_context: IdentityContext,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Log an agent action.
        
        Args:
            identity_context: Identity context of the action
            action: Action being performed
            resource_type: Type of resource being acted upon
            resource_id: ID of the resource
            details: Additional details about the action
        
        Returns:
            Audit log ID
        """
        with get_db() as db:
            # Prepare details with identity context
            log_details = details or {}
            log_details.update({
                "user_id": str(identity_context.user_id),
                "agent_id": str(identity_context.agent_id) if identity_context.agent_id else None,
                "delegation_chain": [str(id) for id in identity_context.delegation_chain],
                "permissions": list(identity_context.permissions),
                "trust_level": identity_context.trust_level,
                "session_id": self.session_id,
                "timestamp": datetime.utcnow().isoformat(),
            })
            
            # Create audit log entry
            audit_log = create_audit_log(
                db,
                identity_id=identity_context.user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=log_details
            )
            
            logger.debug(
                f"Logged action: {action} by {identity_context.user_id} "
                f"(agent: {identity_context.agent_id})"
            )
            
            return str(audit_log.id)
    
    def log_tool_call(
        self,
        identity_context: IdentityContext,
        mcp_name: str,
        tool_name: str,
        parameters: Dict[str, Any],
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> str:
        """
        Log a tool call.
        
        Args:
            identity_context: Identity context of the call
            mcp_name: Name of the MCP server
            tool_name: Name of the tool
            parameters: Tool parameters
            result: Tool result (if successful)
            error: Error message (if failed)
        
        Returns:
            Audit log ID
        """
        details = {
            "mcp_name": mcp_name,
            "tool_name": tool_name,
            "parameters": parameters,
            "result": result,
            "error": error,
            "success": error is None,
        }
        
        return self.log_agent_action(
            identity_context=identity_context,
            action=f"mcp_tool_call:{tool_name}",
            resource_type="mcp_tool",
            resource_id=f"{mcp_name}.{tool_name}",
            details=details
        )
    
    def log_identity_change(
        self,
        identity_context: IdentityContext,
        change_type: str,
        old_value: Any,
        new_value: Any,
        reason: Optional[str] = None,
    ) -> str:
        """
        Log an identity context change.
        
        Args:
            identity_context: Current identity context
            change_type: Type of change (e.g., "impersonation", "delegation")
            old_value: Previous value
            new_value: New value
            reason: Reason for the change
        
        Returns:
            Audit log ID
        """
        details = {
            "change_type": change_type,
            "old_value": str(old_value),
            "new_value": str(new_value),
            "reason": reason,
        }
        
        return self.log_agent_action(
            identity_context=identity_context,
            action=f"identity_change:{change_type}",
            resource_type="identity",
            details=details
        )
    
    def log_delegation_creation(
        self,
        identity_context: IdentityContext,
        from_identity_id: str,
        to_identity_id: str,
        permissions: List[str],
    ) -> str:
        """
        Log delegation creation.
        
        Args:
            identity_context: Identity context of the creator
            from_identity_id: ID of the delegating identity
            to_identity_id: ID of the receiving identity
            permissions: Permissions being delegated
        
        Returns:
            Audit log ID
        """
        details = {
            "from_identity_id": from_identity_id,
            "to_identity_id": to_identity_id,
            "permissions": permissions,
        }
        
        return self.log_agent_action(
            identity_context=identity_context,
            action="delegation_created",
            resource_type="delegation",
            details=details
        )
    
    def log_message(
        self,
        identity_context: IdentityContext,
        message_type: str,
        from_agent_id: str,
        to_agent_id: Optional[str],
        content: str,
    ) -> str:
        """
        Log an agent-to-agent message.
        
        Args:
            identity_context: Identity context of the sender
            message_type: Type of message (direct, broadcast, etc.)
            from_agent_id: Sender agent ID
            to_agent_id: Receiver agent ID (None for broadcasts)
            content: Message content
        
        Returns:
            Audit log ID
        """
        details = {
            "message_type": message_type,
            "from_agent_id": from_agent_id,
            "to_agent_id": to_agent_id,
            "content_length": len(content),
            "content_preview": content[:100] if len(content) > 100 else content,
        }
        
        return self.log_agent_action(
            identity_context=identity_context,
            action=f"message_{message_type}",
            resource_type="message",
            details=details
        )
    
    def log_scenario_execution(
        self,
        scenario_id: str,
        scenario_name: str,
        status: str,
        duration: float,
        steps_completed: int,
        criteria_met: int,
    ) -> str:
        """
        Log scenario execution.
        
        Args:
            scenario_id: Scenario ID
            scenario_name: Scenario name
            status: Execution status (success, failure)
            duration: Execution duration in seconds
            steps_completed: Number of steps completed
            criteria_met: Number of criteria met
        
        Returns:
            Audit log ID
        """
        # Create a system identity context for scenario execution
        from src.identity.context import IdentityContext
        from uuid import UUID
        
        system_context = IdentityContext(
            user_id=UUID('00000000-0000-0000-0000-000000000000'),
            agent_id=None,
            delegation_chain=[],
            permissions=set(),
        )
        
        details = {
            "scenario_id": scenario_id,
            "scenario_name": scenario_name,
            "status": status,
            "duration": duration,
            "steps_completed": steps_completed,
            "criteria_met": criteria_met,
        }
        
        return self.log_agent_action(
            identity_context=system_context,
            action="scenario_execution",
            resource_type="scenario",
            resource_id=scenario_id,
            details=details
        )
    
    def query_logs(
        self,
        identity_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """
        Query audit logs.
        
        Args:
            identity_id: Filter by identity ID
            action: Filter by action
            resource_type: Filter by resource type
            limit: Maximum number of logs to return
        
        Returns:
            List of audit log entries
        """
        with get_db() as db:
            logs = get_audit_logs(db, limit=limit)
            
            # Apply filters
            filtered_logs = []
            for log in logs:
                if identity_id and str(log.identity_id) != identity_id:
                    continue
                if action and log.action != action:
                    continue
                if resource_type and log.resource_type != resource_type:
                    continue
                
                filtered_logs.append({
                    "id": str(log.id),
                    "identity_id": str(log.identity_id),
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "resource_id": str(log.resource_id) if log.resource_id else None,
                    "details": log.details,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                    "logged": log.logged,
                })
            
            return filtered_logs
    
    def get_session_logs(self) -> List[Dict]:
        """Get all logs for the current session."""
        with get_db() as db:
            logs = get_audit_logs(db, limit=1000)
            
            session_logs = []
            for log in logs:
                if log.details and log.details.get("session_id") == self.session_id:
                    session_logs.append({
                        "id": str(log.id),
                        "identity_id": str(log.identity_id),
                        "action": log.action,
                        "resource_type": log.resource_type,
                        "details": log.details,
                        "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                    })
            
            return session_logs


# Global audit logger instance
_audit_logger = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
