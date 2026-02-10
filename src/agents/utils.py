"""
Utility functions for Agno agent integration.

Provides helper functions to:
- Wrap MCP tools as Agno-compatible functions
- Create agent instances
- Manage agent lifecycle
"""

from typing import Callable, Any, Dict, Optional
from uuid import UUID
from loguru import logger

from src.identity.context import IdentityContext


def _normalize_comms_tool_args(tool_name: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure send_message and receive_message always receive correctly named arguments
    when Agno passes them under parameters/arguments or with different key names.
    """
    result = dict(kwargs)
    if tool_name == "send_message":
        to_agent_id = (
            result.get("to_agent_id")
            or result.get("ToAgentId")
            or result.get("to")
            or result.get("To")
            or result.get("destination")
            or result.get("recipient")
        )
        message = (
            result.get("message")
            or result.get("Message")
            or result.get("content")
            or result.get("body")
        )
        if to_agent_id is not None:
            result["to_agent_id"] = str(to_agent_id)
        if message is not None:
            if isinstance(message, dict):
                import json
                result["message"] = json.dumps(message)
            else:
                result["message"] = str(message)
    elif tool_name == "receive_message":
        agent_id = (
            result.get("agent_id")
            or result.get("AgentId")
            or result.get("agent")
            or result.get("Agent")
        )
        limit = result.get("limit") or result.get("Limit")
        if agent_id is not None:
            result["agent_id"] = str(agent_id)
        if limit is not None:
            try:
                result["limit"] = int(limit)
            except (ValueError, TypeError):
                result["limit"] = 10
    return result


def create_mcp_tool_wrapper(
    mcp_server,
    tool_name: str,
    identity_context: Optional[IdentityContext] = None
) -> Callable:
    """
    Wrap an MCP tool as an Agno-compatible function.
    
    This allows us to use our Python-based MCP servers directly with Agno
    agents without needing CLI wrappers.
    
    Args:
        mcp_server: MCP server instance (BaseMCPServer subclass)
        tool_name: Name of the tool to wrap
        identity_context: Optional identity context to pass to tool
        
    Returns:
        Async function that can be used as an Agno tool
    """
    # Validate tool exists at creation time
    if not hasattr(mcp_server, '_tools'):
        logger.error(f"MCP server {mcp_server.name if hasattr(mcp_server, 'name') else 'unknown'} has no _tools attribute")
        raise ValueError(f"Invalid MCP server - no _tools found")
    
    if tool_name not in mcp_server._tools:
        logger.error(f"Tool {tool_name} not found in {mcp_server.name}. Available: {list(mcp_server._tools.keys())}")
        raise ValueError(f"Tool {tool_name} not found in {mcp_server.name}")
    
    import inspect
    from inspect import Parameter, Signature

    tool_info = mcp_server._tools[tool_name]
    handler = tool_info["handler"]
    input_schema = tool_info.get("input_schema", {})
    
    async def tool_wrapper(*args, **kwargs) -> Any:
        """Wrapped tool function."""
        try:
            logger.info(f"DEBUG TOOL WRAPPER [{tool_name}]: args={args}, kwargs={kwargs}")
            
            # 1. Flatten nested 'args' or 'kwargs' from Agno
            if not args:
                if "args" in kwargs:
                    nested_args = kwargs.get("args")
                    if isinstance(nested_args, list):
                        args = tuple(nested_args)
                    elif isinstance(nested_args, dict):
                        # Treat dict as the new root for arguments
                        inner_kwargs = kwargs.get("kwargs", {})
                        if isinstance(inner_kwargs, str):
                            try:
                                import json
                                inner_kwargs = json.loads(inner_kwargs)
                            except:
                                inner_kwargs = {}
                        kwargs = {**nested_args, **inner_kwargs}
                elif "kwargs" in kwargs:
                    # Agno sometimes passes arguments under 'kwargs' key directly
                    inner = kwargs.get("kwargs")
                    if isinstance(inner, dict):
                        id_ctx = kwargs.get("identity_context")
                        kwargs = inner
                        if id_ctx:
                            kwargs["identity_context"] = id_ctx

            # 2. Extreme flattening for common orchestration keys
            if not args and len(kwargs) == 1 and list(kwargs.keys())[0] in ["parameters", "arguments", "data", "args"]:
                key = list(kwargs.keys())[0]
                if isinstance(kwargs[key], dict):
                    id_context = kwargs.get("identity_context")
                    kwargs = dict(kwargs[key])
                    if id_context:
                        kwargs["identity_context"] = id_context

            # 2b. Explicit extraction for send_message / receive_message so Agno always passes correct params
            kwargs = _normalize_comms_tool_args(tool_name, kwargs)

            # 3. Resolve Identity Context (Closure -> ContextVar -> Passed in Kwargs)
            from src.identity.context import identity_context_var
            task_context = identity_context_var.get()
            
            # Priority: 
            # 1. Manually passed in kwargs (for explicit delegation/attacks)
            # 2. task-local context (from A2A bridge or API)
            # 3. closure context (from agent creation)
            resolved_context = kwargs.get("identity_context") or task_context or identity_context
            
            if resolved_context:
                kwargs["identity_context"] = resolved_context
            
            # Standardize: remove IdentityContext object from positional args if it leaked in
            args = tuple([a for a in args if not hasattr(a, 'user_id')])

            # Dispatch to original handler
            result = await handler(*args, **kwargs)

            # Record pending A2A for follow-up prompts (orchestrator session context)
            if tool_name == "send_message" and isinstance(result, dict) and result.get("success"):
                try:
                    from src.identity.context import pending_a2a_var
                    pending_a2a_var.set({
                        "to_agent_id": result.get("to_agent_id") or kwargs.get("to_agent_id"),
                        "message_id": result.get("message_id"),
                    })
                except Exception:
                    pass
            return result

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {"error": str(e)}
    
    # --- Dynamic Metadata for Agno/LLM Discovery ---
    # 1. Set Function Name
    tool_wrapper.__name__ = tool_name
    
    # 2. Build Docstring with Parameter Descriptions
    doc = tool_info.get("description", f"MCP tool: {tool_name}")
    if input_schema and "properties" in input_schema:
        doc += "\n\nArgs:"
        for prop_name, prop_details in input_schema["properties"].items():
            prop_desc = prop_details.get("description", "No description provided.")
            doc += f"\n    {prop_name}: {prop_desc}"
    tool_wrapper.__doc__ = doc
    
    # 3. Dynamic Signature Generation
    # This ensures Agno's inspection 'sees' the required arguments
    # and generates the correct JSON schema for the LLM.
    params = []
    if input_schema and "properties" in input_schema:
        required = input_schema.get("required", [])
        for prop_name in input_schema["properties"]:
            default = Parameter.empty if prop_name in required else None
            # We treat all as keyword-only or positional (Agno handles both)
            params.append(Parameter(
                prop_name, 
                Parameter.POSITIONAL_OR_KEYWORD, 
                default=default
            ))
    
    # Add **kwargs to be safe for any framework extras
    params.append(Parameter("kwargs", Parameter.VAR_KEYWORD))
    
    try:
        tool_wrapper.__signature__ = Signature(params)
    except Exception as sig_err:
        logger.warning(f"Failed to set signature for {tool_name}: {sig_err}")

    return tool_wrapper


def create_agent_tools(
    mcp_servers: Dict[str, Any],
    tool_configs: list[Dict[str, str]],
    identity_context: Optional[IdentityContext] = None
) -> list[Callable]:
    """
    Create a list of Agno tools from MCP server configurations.
    
    Args:
        mcp_servers: Dictionary of MCP server instances
        tool_configs: List of tool configurations with 'server' and 'tool' keys
        identity_context: Optional identity context
        
    Returns:
        List of wrapped tool functions
    """
    tools = []
    
    for config in tool_configs:
        server_name = config["server"]
        tool_name = config["tool"]
        
        if server_name not in mcp_servers:
            logger.warning(f"MCP server {server_name} not found")
            continue
        
        mcp_server = mcp_servers[server_name]
        
        try:
            tool = create_mcp_tool_wrapper(mcp_server, tool_name, identity_context)
            tools.append(tool)
            logger.debug(f"Added tool {tool_name} from {server_name}")
        except ValueError as e:
            logger.error(f"Failed to wrap tool {tool_name} from {server_name}: {e}")
            continue
    
    return tools


def validate_mcp_tools(mcp_servers: Dict[str, Any], tool_configs: list[Dict[str, str]]) -> Dict[str, Any]:
    """
    Validate that all required tools exist in the MCP servers.
    
    Args:
        mcp_servers: Dictionary of MCP server instances
        tool_configs: List of tool configurations to validate
        
    Returns:
        Dictionary with validation results:
        - valid: bool - True if all tools exist
        - missing_servers: list of missing server names
        - missing_tools: list of {server, tool} dicts for missing tools
        - available_tools: dict mapping server names to available tool lists
    """
    results = {
        "valid": True,
        "missing_servers": [],
        "missing_tools": [],
        "available_tools": {}
    }
    
    # Collect available tools per server
    for server_name, mcp_server in mcp_servers.items():
        if hasattr(mcp_server, '_tools'):
            results["available_tools"][server_name] = list(mcp_server._tools.keys())
        else:
            results["available_tools"][server_name] = []
    
    # Validate each config
    for config in tool_configs:
        server_name = config["server"]
        tool_name = config["tool"]
        
        if server_name not in mcp_servers:
            results["missing_servers"].append(server_name)
            results["valid"] = False
            continue
        
        mcp_server = mcp_servers[server_name]
        if not hasattr(mcp_server, '_tools') or tool_name not in mcp_server._tools:
            results["missing_tools"].append({"server": server_name, "tool": tool_name})
            results["valid"] = False
    
    # Remove duplicates
    results["missing_servers"] = list(set(results["missing_servers"]))
    
    return results


def get_all_agents() -> Dict[str, Any]:
    """
    Get all agent instances.
    
    Returns:
        Dictionary mapping agent names to agent instances
    """
    from .orchestrator import create_orchestrator_agent
    from .researcher import create_researcher_agent
    from .executor import create_executor_agent
    from .monitor import create_monitor_agent
    
    return {
        "orchestrator": create_orchestrator_agent(),
        "researcher": create_researcher_agent(),
        "executor": create_executor_agent(),
        "monitor": create_monitor_agent(),
    }


def get_agent_by_id(agent_id: UUID) -> Optional[Any]:
    """
    Get an agent instance by its UUID.
    
    Args:
        agent_id: Agent UUID
        
    Returns:
        Agent instance or None if not found
    """
    # Map known agent IDs to agent names
    agent_map = {
        "00000000-0000-0000-0000-000000000101": "orchestrator",
        "00000000-0000-0000-0000-000000000102": "researcher",
        "00000000-0000-0000-0000-000000000103": "executor",
        "00000000-0000-0000-0000-000000000104": "monitor",
    }
    
    agent_name = agent_map.get(str(agent_id))
    if not agent_name:
        logger.warning(f"Agent {agent_id} not found")
        return None
    
    agents = get_all_agents()
    return agents.get(agent_name)
