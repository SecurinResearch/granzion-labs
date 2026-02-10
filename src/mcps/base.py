"""
Base MCP Server for Granzion Lab.

Provides common functionality for all MCP servers including:
- Identity context validation
- Request/response handling
- Error handling
- Logging
"""

from typing import Any, Dict, Optional, Callable
from uuid import UUID
from datetime import datetime
from abc import ABC, abstractmethod

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
from loguru import logger

from src.identity.context import IdentityContext
from src.database.connection import get_db
from src.database.queries import create_audit_log


class BaseMCPServer(ABC):
    """
    Base class for all MCP servers in Granzion Lab.
    
    Provides common functionality:
    - Identity context validation
    - Request/response handling
    - Audit logging
    - Error handling
    
    Subclasses must implement:
    - register_tools(): Register MCP tools
    - register_resources(): Register MCP resources (optional)
    - register_prompts(): Register MCP prompts (optional)
    """
    
    def __init__(self, name: str, version: str = "1.0.0"):
        """
        Initialize base MCP server.
        
        Args:
            name: Server name (e.g., "identity-mcp", "memory-mcp")
            version: Server version
        """
        self.name = name
        self.version = version
        self.server = Server(name)
        self._tools = {}
        self._resources = {}
        
        # Statistics
        self._request_count = 0
        self._error_count = 0
        
        logger.info(f"Initializing MCP server: {name} v{version}")
        
        # Set up handlers FIRST before registering tools
        self._setup_handlers()
        
        # Register tools, resources, and prompts
        self.register_tools()
        self.register_resources()
        self.register_prompts()
        
        logger.info(f"MCP server {name} initialized successfully with {len(self._tools)} tools")
    

    
    def _setup_handlers(self):
        """Set up MCP server handlers."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """List available tools."""
            return [
                types.Tool(
                    name=name,
                    description=tool_info.get("description", ""),
                    inputSchema=tool_info.get("inputSchema", {
                        "type": "object",
                        "properties": {},
                    }),
                )
                for name, tool_info in self._tools.items()
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: dict | None
        ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            """Handle tool calls."""
            if name not in self._tools:
                raise ValueError(f"Unknown tool: {name}")
            
            tool_info = self._tools[name]
            handler = tool_info["handler"]
            
            try:
                result = await handler(**(arguments or {}))
                return [types.TextContent(type="text", text=str(result))]
            except Exception as e:
                logger.error(f"Error calling tool {name}: {e}")
                raise

        @self.server.list_resources()
        async def handle_list_resources() -> list[types.Resource]:
            """List available resources."""
            return [
                types.Resource(
                    uri=res_info["uri"],
                    name=res_info["name"],
                    description=res_info.get("description", ""),
                    mimeType=res_info.get("mimeType", "application/json"),
                )
                for name, res_info in self._resources.items()
            ]

        @self.server.read_resource()
        async def handle_read_resource(uri: Any) -> str:
            """Read a resource."""
            uri_str = str(uri)
            for name, res_info in self._resources.items():
                if res_info["uri"] == uri_str:
                    handler = res_info["handler"]
                    return await handler()
            raise ValueError(f"Unknown resource: {uri_str}")
    
    def register_tool(
        self,
        name: str,
        handler: Callable,
        description: str,
        input_schema: Dict[str, Any]
    ):
        """
        Register a tool with the MCP server.
        
        Args:
            name: Tool name
            handler: Async function to handle tool calls
            description: Tool description
            input_schema: JSON schema for tool inputs
        """
        self._tools[name] = {
            "handler": handler,
            "description": description,
            "inputSchema": input_schema,
        }
        logger.debug(f"Registered tool: {name}")
    
    def register_resource(
        self,
        uri: str,
        name: str,
        handler: Callable,
        description: str = "",
        mime_type: str = "application/json"
    ):
        """
        Register a resource with the MCP server.
        
        Args:
            uri: Resource URI
            name: Resource name
            handler: Async function to return resource content
            description: Resource description
            mime_type: Resource MIME type
        """
        self._resources[name] = {
            "uri": uri,
            "name": name,
            "handler": handler,
            "description": description,
            "mimeType": mime_type,
        }
        logger.debug(f"Registered resource: {name} ({uri})")

    @abstractmethod
    def register_tools(self):
        """
        Register MCP tools for this server.
        
        Subclasses must implement this method to register their tools
        using self.register_tool().
        """
        pass
    
    def register_resources(self):
        """
        Register MCP resources for this server (optional).
        
        Subclasses can override this method to register resources.
        """
        pass
    
    def register_prompts(self):
        """
        Register MCP prompts for this server (optional).
        
        Subclasses can override this method to register prompts.
        """
        pass
    
    def validate_identity_context(
        self,
        identity_context: Optional[IdentityContext],
        required_permissions: Optional[list[str]] = None
    ) -> bool:
        """
        Validate identity context and permissions.
        
        Args:
            identity_context: Identity context to validate
            required_permissions: List of required permissions
            
        Returns:
            True if valid, False otherwise
            
        Raises:
            ValueError: If identity context is invalid
        """
        if identity_context is None:
            logger.warning("No identity context provided")
            return False
        
        # Check if required permissions are present
        if required_permissions:
            missing_permissions = set(required_permissions) - identity_context.permissions
            if missing_permissions:
                logger.warning(
                    f"Missing required permissions: {missing_permissions} "
                    f"for identity {identity_context.current_identity_id}"
                )
                return False
        
        logger.debug(
            f"Identity context validated: user={identity_context.user_id}, "
            f"agent={identity_context.agent_id}, "
            f"permissions={identity_context.permissions}"
        )
        
        return True
    
    def _make_serializable(self, obj: Any) -> Any:
        """Convert objects to JSON serializable format."""
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._make_serializable(i) for i in obj]
        return obj

    def log_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Any,
        identity_context: Optional[IdentityContext] = None,
        error: Optional[str] = None
    ):
        """
        Log tool call to audit log.
        
        Args:
            tool_name: Name of the tool called
            arguments: Tool arguments
            result: Tool result
            identity_context: Identity context
            error: Error message if failed
        """
        try:
            with get_db() as db:
                details = {
                    "mcp_server": self.name,
                    "tool_name": tool_name,
                    "arguments": self._make_serializable(arguments),
                    "timestamp": datetime.utcnow().isoformat(),
                }
                
                if result is not None:
                    details["result_type"] = type(result).__name__
                    # Don't log full result if it's large
                    if isinstance(result, (str, int, float, bool)):
                        details["result"] = result
                    elif isinstance(result, (list, dict)):
                        details["result_size"] = len(result)
                
                if error:
                    details["error"] = error
                
                if identity_context:
                    details.update({
                        "user_id": str(identity_context.user_id),
                        "agent_id": str(identity_context.agent_id) if identity_context.agent_id else None,
                        "delegation_depth": identity_context.delegation_depth,
                        "trust_level": identity_context.trust_level,
                    })
                
                create_audit_log(
                    db,
                    identity_id=identity_context.current_identity_id if identity_context else None,
                    action=f"mcp_tool_call:{tool_name}",
                    resource_type="mcp_tool",
                    resource_id=None,
                    details=details
                )
                
        except Exception as e:
            logger.error(f"Failed to log tool call: {e}")
    
    def handle_error(
        self,
        error: Exception,
        tool_name: str,
        identity_context: Optional[IdentityContext] = None
    ) -> Dict[str, Any]:
        """
        Handle and log errors from tool calls.
        
        Args:
            error: Exception that occurred
            tool_name: Name of the tool that failed
            identity_context: Identity context
            
        Returns:
            Error response dictionary
        """
        import traceback
        self._error_count += 1
        
        error_msg = f"{type(error).__name__}: {str(error)}"
        stack_trace = traceback.format_exc()
        logger.error(f"Error in {self.name}.{tool_name}: {error_msg}\n{stack_trace}")
        
        # Log error
        self.log_tool_call(
            tool_name=tool_name,
            arguments={},
            result=None,
            identity_context=identity_context,
            error=f"{error_msg}\n{stack_trace}"
        )
        
        return {
            "error": error_msg,
            "tool": tool_name,
            "server": self.name,
            "traceback": stack_trace
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get server statistics.
        
        Returns:
            Dictionary with server stats
        """
        return {
            "name": self.name,
            "version": self.version,
            "request_count": self._request_count,
            "error_count": self._error_count,
            "error_rate": self._error_count / max(self._request_count, 1),
        }
    
    def run(self):
        """
        Run the MCP server.
        
        This starts the server and listens for requests.
        """
        logger.info(f"Starting MCP server: {self.name}")
        self.server.run()
    
    async def arun(self):
        """
        Run the MCP server asynchronously.
        
        This starts the server and listens for requests asynchronously.
        """
        logger.info(f"Starting MCP server (async): {self.name}")
        await self.server.run_async()


def create_tool_wrapper(
    func: Callable,
    server: BaseMCPServer,
    required_permissions: Optional[list[str]] = None
) -> Callable:
    """
    Create a wrapper for MCP tool functions that adds:
    - Identity context validation
    - Audit logging
    - Error handling
    
    Args:
        func: Tool function to wrap
        server: MCP server instance
        required_permissions: Required permissions for this tool
        
    Returns:
        Wrapped function
    """
    async def wrapper(*args, identity_context: Optional[IdentityContext] = None, **kwargs):
        server._request_count += 1
        tool_name = func.__name__
        
        try:
            # Validate identity context
            if not server.validate_identity_context(identity_context, required_permissions):
                error_msg = "Invalid identity context or insufficient permissions"
                server.log_tool_call(
                    tool_name=tool_name,
                    arguments=kwargs,
                    result=None,
                    identity_context=identity_context,
                    error=error_msg
                )
                return {"error": error_msg}
            
            # Call the actual tool function
            result = await func(*args, identity_context=identity_context, **kwargs)
            
            # Log successful call
            server.log_tool_call(
                tool_name=tool_name,
                arguments=kwargs,
                result=result,
                identity_context=identity_context
            )
            
            return result
            
        except Exception as e:
            return server.handle_error(e, tool_name, identity_context)
    
    return wrapper
