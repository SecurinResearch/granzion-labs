"""
MCP (Model Context Protocol) servers for Granzion Lab.

This module contains all MCP server implementations:
- Identity MCP: Identity and delegation management
- Memory MCP: RAG and vector memory
- Data MCP: CRUD operations and SQL
- Comms MCP: Agent-to-agent communication
- Infra MCP: Infrastructure and deployment
"""

from src.mcps.base import BaseMCPServer, create_tool_wrapper
from src.mcps.identity_mcp import IdentityMCPServer, get_identity_mcp_server, reset_identity_mcp_server
from src.mcps.memory_mcp import MemoryMCPServer, get_memory_mcp_server, reset_memory_mcp_server
from src.mcps.data_mcp import DataMCPServer, get_data_mcp_server, reset_data_mcp_server
from src.mcps.comms_mcp import CommsMCPServer, get_comms_mcp_server, reset_comms_mcp_server
from src.mcps.infra_mcp import InfraMCPServer, get_infra_mcp_server, reset_infra_mcp_server

__all__ = [
    "BaseMCPServer",
    "create_tool_wrapper",
    "IdentityMCPServer",
    "get_identity_mcp_server",
    "reset_identity_mcp_server",
    "MemoryMCPServer",
    "get_memory_mcp_server",
    "reset_memory_mcp_server",
    "DataMCPServer",
    "get_data_mcp_server",
    "reset_data_mcp_server",
    "CommsMCPServer",
    "get_comms_mcp_server",
    "reset_comms_mcp_server",
    "InfraMCPServer",
    "get_infra_mcp_server",
    "reset_infra_mcp_server",
]
