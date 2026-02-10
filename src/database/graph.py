"""
PuppyGraph client for graph queries over PostgreSQL.
Provides graph query capabilities for delegation chains and relationships.
When PuppyGraph is unreachable, get_graph_client() returns None; callers use SQL fallback.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID

from gremlin_python.driver import client, serializer
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.graph_traversal import __
from gremlin_python.process.traversal import T
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from loguru import logger

import nest_asyncio
nest_asyncio.apply()

from src.config import settings


class PuppyGraphClient:
    """
    Client for interacting with PuppyGraph.
    PuppyGraph provides graph query capabilities over PostgreSQL data.
    """
    def __init__(self):
        """Initialize PuppyGraph client."""
        self.url = settings.puppygraph_url
        self._client: Optional[client.Client] = None
        self._connection: Optional[DriverRemoteConnection] = None

    def connect(self):
        """Establish connection to PuppyGraph."""
        try:
            self._client = client.Client(
                self.url,
                'g',
                message_serializer=serializer.GraphSONSerializersV3d0()
            )
            self._connection = DriverRemoteConnection(self.url, 'g')
            logger.info(f"Connected to PuppyGraph at {self.url}")
        except Exception as e:
            logger.error(f"Failed to connect to PuppyGraph: {e}")
            raise
    
    def disconnect(self):
        """Close connection to PuppyGraph."""
        if self._client:
            self._client.close()
        if self._connection:
            self._connection.close()
        logger.info("Disconnected from PuppyGraph")
    
    def get_traversal(self):
        """Get a graph traversal source."""
        if not self._connection:
            self.connect()
        return traversal().withRemote(self._connection)
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute a raw Gremlin query.
        
        Args:
            query: Gremlin query string
            
        Returns:
            List of results
        """
        if not self._client:
            self.connect()
        
        try:
            result = self._client.submit(query).all().result()
            return result
        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            raise
    
    # Delegation Chain Queries
    
    def get_delegation_chain(self, agent_id: UUID) -> List[Dict[str, Any]]:
        """
        Get the complete delegation chain for an agent.
        
        Args:
            agent_id: Agent UUID
            
        Returns:
            List of identities in the delegation chain
        """
        query = f"""
        g.V().has('id', '{agent_id}')
          .repeat(__.in('DELEGATES_TO'))
          .until(__.not(__.in('DELEGATES_TO')))
          .path()
          .by(valueMap(true))
        """
        
        try:
            result = self.execute_query(query)
            logger.info(f"Retrieved delegation chain for agent {agent_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to get delegation chain: {e}")
            return []
    
    def get_delegation_depth(self, agent_id: UUID) -> int:
        """
        Get the delegation depth (chain length) for an agent.
        
        Args:
            agent_id: Agent UUID
            
        Returns:
            Delegation chain depth
        """
        query = f"""
        g.V().has('id', '{agent_id}')
          .repeat(__.in('DELEGATES_TO'))
          .until(__.not(__.in('DELEGATES_TO')))
          .path()
          .count(local)
        """
        
        try:
            result = self.execute_query(query)
            depth = result[0] if result else 0
            logger.info(f"Delegation depth for agent {agent_id}: {depth}")
            return depth
        except Exception as e:
            logger.error(f"Failed to get delegation depth: {e}")
            return 0
    
    def find_circular_delegations(self) -> List[Dict[str, Any]]:
        """
        Find circular delegation relationships (vulnerability).
        
        Returns:
            List of circular delegation paths
        """
        query = """
        g.V().hasLabel('Agent')
          .as('start')
          .repeat(__.out('DELEGATES_TO'))
          .until(__.where(eq('start')))
          .path()
          .by(valueMap(true))
        """
        
        try:
            result = self.execute_query(query)
            if result:
                logger.warning(f"Found {len(result)} circular delegations")
            return result
        except Exception as e:
            logger.error(f"Failed to find circular delegations: {e}")
            return []
    
    # Agent Relationship Queries
    
    def get_agents_acting_for_user(self, user_id: UUID) -> List[Dict[str, Any]]:
        """
        Get all agents acting on behalf of a user.
        
        Args:
            user_id: User UUID
            
        Returns:
            List of agents
        """
        query = f"""
        g.V().has('id', '{user_id}')
          .in('ACTS_FOR')
          .valueMap(true)
        """
        
        try:
            result = self.execute_query(query)
            logger.info(f"Found {len(result)} agents acting for user {user_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to get agents for user: {e}")
            return []
    
    def get_agents_with_multiple_users(self) -> List[Dict[str, Any]]:
        """
        Find agents acting for multiple users (identity confusion).
        
        Returns:
            List of agents with multiple user relationships
        """
        query = """
        g.V().hasLabel('Agent')
          .where(__.out('ACTS_FOR').count().is(gt(1)))
          .project('agent', 'users')
            .by(valueMap(true))
            .by(__.out('ACTS_FOR').valueMap(true).fold())
        """
        
        try:
            result = self.execute_query(query)
            if result:
                logger.warning(f"Found {len(result)} agents with multiple users")
            return result
        except Exception as e:
            logger.error(f"Failed to find agents with multiple users: {e}")
            return []
    
    # Communication Queries
    
    def get_agent_communication_graph(self, agent_id: UUID) -> Dict[str, Any]:
        """
        Get the communication graph for an agent.
        
        Args:
            agent_id: Agent UUID
            
        Returns:
            Communication graph data
        """
        query = f"""
        g.V().has('id', '{agent_id}')
          .project('agent', 'sends_to', 'receives_from')
            .by(valueMap(true))
            .by(__.out('COMMUNICATES_WITH').valueMap(true).fold())
            .by(__.in('COMMUNICATES_WITH').valueMap(true).fold())
        """
        
        try:
            result = self.execute_query(query)
            return result[0] if result else {}
        except Exception as e:
            logger.error(f"Failed to get communication graph: {e}")
            return {}
    
    def get_message_path(self, from_agent_id: UUID, to_agent_id: UUID) -> List[Dict[str, Any]]:
        """
        Get the shortest message path between two agents.
        
        Args:
            from_agent_id: Source agent UUID
            to_agent_id: Target agent UUID
            
        Returns:
            Shortest path
        """
        query = f"""
        g.V().has('id', '{from_agent_id}')
          .repeat(__.out('COMMUNICATES_WITH').simplePath())
          .until(__.has('id', '{to_agent_id}'))
          .path()
          .by(valueMap(true))
          .limit(1)
        """
        
        try:
            result = self.execute_query(query)
            return result
        except Exception as e:
            logger.error(f"Failed to get message path: {e}")
            return []
    
    # Permission Queries
    
    def get_agents_with_excessive_permissions(self, threshold: int = 10) -> List[Dict[str, Any]]:
        """
        Find agents with excessive permissions.
        
        Args:
            threshold: Permission count threshold
            
        Returns:
            List of agents with excessive permissions
        """
        query = f"""
        g.V().hasLabel('Agent')
          .where(__.values('permissions').count(local).is(gt({threshold})))
          .project('agent', 'permission_count')
            .by(valueMap(true))
            .by(__.values('permissions').count(local))
        """
        
        try:
            result = self.execute_query(query)
            if result:
                logger.warning(f"Found {len(result)} agents with excessive permissions")
            return result
        except Exception as e:
            logger.error(f"Failed to find agents with excessive permissions: {e}")
            return []
    
    # Tool Usage Queries
    
    def get_agent_tool_usage(self, agent_id: UUID) -> List[Dict[str, Any]]:
        """
        Get tool usage for an agent.
        
        Args:
            agent_id: Agent UUID
            
        Returns:
            List of tools used by the agent
        """
        query = f"""
        g.V().has('id', '{agent_id}')
          .out('USES_TOOL')
          .project('service', 'usage_count')
            .by(valueMap(true))
            .by(__.in('USES_TOOL').count())
        """
        
        try:
            result = self.execute_query(query)
            return result
        except Exception as e:
            logger.error(f"Failed to get tool usage: {e}")
            return []
    
    # Health Check
    
    def health_check(self) -> bool:
        """
        Check if PuppyGraph is accessible.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            query = "g.V().limit(1).count()"
            result = self.execute_query(query)
            logger.info("PuppyGraph health check passed")
            return True
        except Exception as e:
            logger.error(f"PuppyGraph health check failed: {e}")
            return False


# Global client instance; None when PuppyGraph is unreachable (fallback to SQL)
_graph_client: Optional[PuppyGraphClient] = None
_graph_client_tried: bool = False


def get_graph_client() -> Optional[PuppyGraphClient]:
    """Get the global PuppyGraph client instance, or None if unreachable (use SQL fallback)."""
    global _graph_client, _graph_client_tried
    if _graph_client_tried:
        return _graph_client
    _graph_client_tried = True
    try:
        _graph_client = PuppyGraphClient()
        _graph_client.connect()
        return _graph_client
    except Exception as e:
        logger.warning("PuppyGraph not available: %s. Graph queries will use SQL fallback.", e)
        _graph_client = None
        return None


def close_graph_client():
    """Close the global PuppyGraph client."""
    global _graph_client, _graph_client_tried
    if _graph_client:
        _graph_client.disconnect()
        _graph_client = None
    _graph_client_tried = False
