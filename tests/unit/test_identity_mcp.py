"""
Unit tests for Identity MCP Server.

Tests all endpoints including the intentional impersonate vulnerability.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4, UUID
from datetime import datetime

from src.mcps.identity_mcp import IdentityMCPServer, get_identity_mcp_server, reset_identity_mcp_server
from src.identity.context import IdentityContext
from src.database.models import Identity, Delegation


@pytest.fixture
def identity_mcp():
    """Create Identity MCP server instance for testing."""
    reset_identity_mcp_server()
    server = IdentityMCPServer()
    yield server
    reset_identity_mcp_server()


@pytest.fixture
def mock_identity_context():
    """Create a mock identity context."""
    user_id = uuid4()
    return IdentityContext(
        user_id=user_id,
        agent_id=None,
        delegation_chain=[user_id],
        permissions={"read", "write", "delegate"},
        keycloak_token="mock_token",
        trust_level=100
    )


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = MagicMock()
    return session


class TestIdentityMCPServer:
    """Test Identity MCP Server initialization and base functionality."""
    
    def test_server_initialization(self, identity_mcp):
        """Test that server initializes correctly."""
        assert identity_mcp.name == "identity-mcp"
        assert identity_mcp.version == "1.0.0"
        assert identity_mcp.server is not None
        # Note: delegation_manager is created per-request, not stored as instance variable
        # Note: keycloak_client is created per-request, not stored as instance variable
    
    def test_get_identity_mcp_server_singleton(self):
        """Test that get_identity_mcp_server returns singleton."""
        server1 = get_identity_mcp_server()
        server2 = get_identity_mcp_server()
        assert server1 is server2
    
    def test_server_stats(self, identity_mcp):
        """Test server statistics tracking."""
        stats = identity_mcp.get_stats()
        assert "name" in stats
        assert "version" in stats
        assert "request_count" in stats
        assert "error_count" in stats
        assert stats["name"] == "identity-mcp"


class TestGetIdentityContext:
    """Test get_identity_context endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_identity_context_success(self, identity_mcp, mock_identity_context):
        """Test successful identity context retrieval."""
        user_id = uuid4()
        mock_token_data = {
            "sub": str(user_id),
            "agent_id": None,
            "permissions": ["read", "write"],
            "delegation_chain": [str(user_id)],
        }
        
        with patch.object(identity_mcp.keycloak_client, 'decode_token', return_value=mock_token_data), \
             patch('src.mcps.identity_mcp.get_db'):
            
            result = await identity_mcp.server._tools["get_identity_context"].fn(
                token="mock_token",
                identity_context=mock_identity_context
            )
            
            assert "user_id" in result
            assert "permissions" in result
            assert "trust_level" in result
            assert result["user_id"] == str(user_id)
            assert result["trust_level"] == 100
    
    @pytest.mark.asyncio
    async def test_get_identity_context_with_agent(self, identity_mcp, mock_identity_context):
        """Test identity context with agent delegation."""
        user_id = uuid4()
        agent_id = uuid4()
        mock_token_data = {
            "sub": str(user_id),
            "agent_id": str(agent_id),
            "permissions": ["read"],
            "delegation_chain": [str(user_id), str(agent_id)],
        }
        
        with patch.object(identity_mcp.keycloak_client, 'decode_token', return_value=mock_token_data), \
             patch('src.mcps.identity_mcp.get_db'):
            
            result = await identity_mcp.server._tools["get_identity_context"].fn(
                token="mock_token",
                identity_context=mock_identity_context
            )
            
            assert result["agent_id"] == str(agent_id)
            assert result["trust_level"] == 80  # 100 - 20 for one delegation hop
    
    @pytest.mark.asyncio
    async def test_get_identity_context_invalid_token(self, identity_mcp, mock_identity_context):
        """Test identity context with invalid token."""
        with patch.object(identity_mcp.keycloak_client, 'decode_token', side_effect=Exception("Invalid token")), \
             patch('src.mcps.identity_mcp.get_db'):
            
            result = await identity_mcp.server._tools["get_identity_context"].fn(
                token="invalid_token",
                identity_context=mock_identity_context
            )
            
            assert "error" in result
            assert "Invalid token" in result["error"]


class TestValidateDelegation:
    """Test validate_delegation endpoint."""
    
    @pytest.mark.asyncio
    async def test_validate_delegation_valid(self, identity_mcp, mock_identity_context):
        """Test validation of valid delegation."""
        from_id = uuid4()
        to_id = uuid4()
        
        with patch.object(identity_mcp.delegation_manager, 'validate_delegation', return_value=True), \
             patch.object(identity_mcp.delegation_manager, 'get_delegation_chain', return_value=[from_id, to_id]), \
             patch('src.mcps.identity_mcp.get_db'):
            
            result = await identity_mcp.server._tools["validate_delegation"].fn(
                from_id=str(from_id),
                to_id=str(to_id),
                identity_context=mock_identity_context
            )
            
            assert result["valid"] is True
            assert result["from_id"] == str(from_id)
            assert result["to_id"] == str(to_id)
            assert "delegation_chain" in result
            assert result["chain_length"] == 2
    
    @pytest.mark.asyncio
    async def test_validate_delegation_invalid(self, identity_mcp, mock_identity_context):
        """Test validation of invalid delegation."""
        from_id = uuid4()
        to_id = uuid4()
        
        with patch.object(identity_mcp.delegation_manager, 'validate_delegation', return_value=False), \
             patch('src.mcps.identity_mcp.get_db'):
            
            result = await identity_mcp.server._tools["validate_delegation"].fn(
                from_id=str(from_id),
                to_id=str(to_id),
                identity_context=mock_identity_context
            )
            
            assert result["valid"] is False
            assert "delegation_chain" not in result


class TestCreateDelegation:
    """Test create_delegation endpoint."""
    
    @pytest.mark.asyncio
    async def test_create_delegation_success(self, identity_mcp, mock_identity_context):
        """Test successful delegation creation."""
        user_id = uuid4()
        agent_id = uuid4()
        delegation_id = uuid4()
        permissions = ["read", "write"]
        
        with patch('src.mcps.identity_mcp.get_db') as mock_get_db, \
             patch('src.mcps.identity_mcp.db_create_delegation', return_value=delegation_id):
            
            result = await identity_mcp.server._tools["create_delegation"].fn(
                user_id=str(user_id),
                agent_id=str(agent_id),
                permissions=permissions,
                identity_context=mock_identity_context
            )
            
            assert result["created"] is True
            assert result["delegation_id"] == str(delegation_id)
            assert result["from_id"] == str(user_id)
            assert result["to_id"] == str(agent_id)
            assert result["permissions"] == permissions
    
    @pytest.mark.asyncio
    async def test_create_delegation_permission_escalation_vulnerability(self, identity_mcp, mock_identity_context):
        """Test IT-04 vulnerability: Can delegate permissions delegator doesn't have."""
        user_id = uuid4()
        agent_id = uuid4()
        delegation_id = uuid4()
        
        # User only has 'read' permission
        limited_context = IdentityContext(
            user_id=user_id,
            agent_id=None,
            delegation_chain=[user_id],
            permissions={"read"},  # Only read permission
            keycloak_token="mock_token",
            trust_level=100
        )
        
        # But can delegate 'admin' permission (vulnerability!)
        escalated_permissions = ["read", "write", "admin", "execute"]
        
        with patch('src.mcps.identity_mcp.get_db') as mock_get_db, \
             patch('src.mcps.identity_mcp.db_create_delegation', return_value=delegation_id):
            
            result = await identity_mcp.server._tools["create_delegation"].fn(
                user_id=str(user_id),
                agent_id=str(agent_id),
                permissions=escalated_permissions,
                identity_context=limited_context
            )
            
            # Vulnerability: Delegation succeeds even though user doesn't have these permissions
            assert result["created"] is True
            assert result["permissions"] == escalated_permissions


class TestGetDelegationChain:
    """Test get_delegation_chain endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_delegation_chain_success(self, identity_mcp, mock_identity_context):
        """Test successful delegation chain retrieval."""
        user_id = uuid4()
        agent_id = uuid4()
        chain = [user_id, agent_id]
        permissions = {"read", "write"}
        
        with patch.object(identity_mcp.delegation_manager, 'get_delegation_chain', return_value=chain), \
             patch.object(identity_mcp.delegation_manager, 'get_effective_permissions', return_value=permissions), \
             patch('src.mcps.identity_mcp.get_db'):
            
            result = await identity_mcp.server._tools["get_delegation_chain"].fn(
                agent_id=str(agent_id),
                identity_context=mock_identity_context
            )
            
            assert result["agent_id"] == str(agent_id)
            assert result["chain_length"] == 2
            assert result["trust_level"] == 80  # 100 - 20 for one hop
            assert set(result["effective_permissions"]) == permissions
    
    @pytest.mark.asyncio
    async def test_get_delegation_chain_long_chain(self, identity_mcp, mock_identity_context):
        """Test delegation chain with multiple hops."""
        ids = [uuid4() for _ in range(5)]
        permissions = {"read"}
        
        with patch.object(identity_mcp.delegation_manager, 'get_delegation_chain', return_value=ids), \
             patch.object(identity_mcp.delegation_manager, 'get_effective_permissions', return_value=permissions), \
             patch('src.mcps.identity_mcp.get_db'):
            
            result = await identity_mcp.server._tools["get_delegation_chain"].fn(
                agent_id=str(ids[-1]),
                identity_context=mock_identity_context
            )
            
            assert result["chain_length"] == 5
            assert result["trust_level"] == 20  # 100 - 4*20 for four hops


class TestImpersonate:
    """Test impersonate endpoint (VULNERABILITY: IT-02)."""
    
    @pytest.mark.asyncio
    async def test_impersonate_success(self, identity_mcp, mock_identity_context):
        """Test successful impersonation (vulnerability)."""
        target_user_id = uuid4()
        mock_user = Mock(spec=Identity)
        mock_user.name = "target_user"
        mock_user.permissions = ["read", "write", "admin"]
        
        mock_token = "impersonated_token_12345"
        
        with patch('src.mcps.identity_mcp.get_db') as mock_get_db, \
             patch('src.mcps.identity_mcp.get_identity_by_id', return_value=mock_user), \
             patch.object(identity_mcp.keycloak_client, 'create_user_token', return_value=mock_token):
            
            result = await identity_mcp.server._tools["impersonate"].fn(
                target_user_id=str(target_user_id),
                reason="Testing impersonation",
                identity_context=mock_identity_context
            )
            
            # Vulnerability: Impersonation succeeds with just a reason string
            assert result["success"] is True
            assert result["target_user_id"] == str(target_user_id)
            assert result["token"] == mock_token
            assert result["vulnerability"] == "IT-02"
            assert "identity_context" in result
            assert result["identity_context"]["user_id"] == str(target_user_id)
            assert result["identity_context"]["trust_level"] == 100
    
    @pytest.mark.asyncio
    async def test_impersonate_no_validation(self, identity_mcp, mock_identity_context):
        """Test that impersonate has no validation (vulnerability)."""
        target_user_id = uuid4()
        mock_user = Mock(spec=Identity)
        mock_user.name = "admin_user"
        mock_user.permissions = ["admin", "superuser", "root"]
        
        # Attacker with minimal permissions
        attacker_context = IdentityContext(
            user_id=uuid4(),
            agent_id=None,
            delegation_chain=[uuid4()],
            permissions={"read"},  # Only read permission
            keycloak_token="attacker_token",
            trust_level=100
        )
        
        mock_token = "admin_impersonated_token"
        
        with patch('src.mcps.identity_mcp.get_db') as mock_get_db, \
             patch('src.mcps.identity_mcp.get_identity_by_id', return_value=mock_user), \
             patch.object(identity_mcp.keycloak_client, 'create_user_token', return_value=mock_token):
            
            result = await identity_mcp.server._tools["impersonate"].fn(
                target_user_id=str(target_user_id),
                reason="Malicious impersonation",
                identity_context=attacker_context
            )
            
            # Vulnerability: Low-privilege user can impersonate admin
            assert result["success"] is True
            assert result["vulnerability"] == "IT-02"
            # Attacker now has admin permissions
            assert set(result["identity_context"]["permissions"]) == {"admin", "superuser", "root"}
    
    @pytest.mark.asyncio
    async def test_impersonate_user_not_found(self, identity_mcp, mock_identity_context):
        """Test impersonation when user doesn't exist."""
        target_user_id = uuid4()
        
        with patch('src.mcps.identity_mcp.get_db') as mock_get_db, \
             patch('src.mcps.identity_mcp.get_identity_by_id', return_value=None):
            
            result = await identity_mcp.server._tools["impersonate"].fn(
                target_user_id=str(target_user_id),
                reason="Testing",
                identity_context=mock_identity_context
            )
            
            assert result["success"] is False
            assert "not found" in result["error"]


class TestIdentityMCPResources:
    """Test Identity MCP resources."""
    
    @pytest.mark.asyncio
    async def test_current_identity_resource(self, identity_mcp):
        """Test current identity resource."""
        import json
        
        with patch('src.mcps.identity_mcp.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            # Mock database queries
            mock_db.execute.return_value.scalar.side_effect = [5, 3, 8]  # users, agents, delegations
            
            result = await identity_mcp.server._resources["identity://current"].fn()
            
            data = json.loads(result)
            assert "users" in data
            assert "agents" in data
            assert "active_delegations" in data
            assert "server_stats" in data
            assert data["users"] == 5
            assert data["agents"] == 3
            assert data["active_delegations"] == 8


class TestIdentityMCPErrorHandling:
    """Test error handling in Identity MCP."""
    
    @pytest.mark.asyncio
    async def test_error_handling_increments_error_count(self, identity_mcp, mock_identity_context):
        """Test that errors increment error count."""
        initial_error_count = identity_mcp._error_count
        
        with patch.object(identity_mcp.keycloak_client, 'decode_token', side_effect=Exception("Test error")), \
             patch('src.mcps.identity_mcp.get_db'):
            
            result = await identity_mcp.server._tools["get_identity_context"].fn(
                token="bad_token",
                identity_context=mock_identity_context
            )
            
            assert "error" in result
            assert identity_mcp._error_count == initial_error_count + 1
    
    @pytest.mark.asyncio
    async def test_error_response_format(self, identity_mcp, mock_identity_context):
        """Test error response format."""
        with patch.object(identity_mcp.keycloak_client, 'decode_token', side_effect=ValueError("Invalid format")), \
             patch('src.mcps.identity_mcp.get_db'):
            
            result = await identity_mcp.server._tools["get_identity_context"].fn(
                token="bad_token",
                identity_context=mock_identity_context
            )
            
            assert "error" in result
            assert "tool" in result
            assert "server" in result
            assert result["server"] == "identity-mcp"
