"""
Agno agents for Granzion Lab.

This module implements 4 agents using the Agno framework:
1. Orchestrator Agent - Coordinates multi-agent workflows
2. Researcher Agent - Performs RAG-based retrieval
3. Executor Agent - Executes actions via tools
4. Monitor Agent - Observes system activity (with intentional gaps)

Each agent has intentional vulnerabilities as specified in the design document.
"""

from .orchestrator import create_orchestrator_agent
from .researcher import create_researcher_agent
from .executor import create_executor_agent
from .monitor import create_monitor_agent
from .utils import create_mcp_tool_wrapper, get_all_agents, validate_mcp_tools
from .goals import get_goal_manager, Goal, GoalManager

__all__ = [
    "create_orchestrator_agent",
    "create_researcher_agent",
    "create_executor_agent",
    "create_monitor_agent",
    "create_mcp_tool_wrapper",
    "get_all_agents",
    "validate_mcp_tools",
    "get_goal_manager",
    "Goal",
    "GoalManager",
]
