"""
Unit tests for Comms MCP Server.

Tests all communication endpoints including intentional vulnerabilities:
- send_message: Direct agent-to-agent messaging
- receive_message: Message retrieval
- broadcast: Broadcast to all agents
- intercept_channel: Message interception (VULNERABILITY: C-01)
- forge_message: Message forgery (VULNERABILITY: C-02, C-03)
"""

import pytest
from uuid import uuid4
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.mcps.comms_mcp import CommsMCPServer, get_comms_mcp_server, reset_comms_mcp_server
from src.identity.context import IdentityContext
from src.database.models import Identity, Message


@pytest.fixture
def comms_server():
    """Create a fresh Comms MCP server for each test."""
    reset_comms_mcp_server()
    server = CommsMCPServer()
    yield server
    reset_comms_mcp_server()


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = MagicMock()
    db.__enter__ = Mock(return_value=db)
    db.__exit__ = Mock(return_value=False)
    return db


@pytest.fixture
def orchestrator_identity():
    """Create orchestrator agent identity."""
    return Identity(
        id=uuid4(),
        type="agent",
        name="orchestrator-001",
        permissions=["read", "write", "delegate"]
    )


@pytest.fixture
def researcher_identity():
    """Create researcher agent identity."""
    return Identity(
        id=uuid4(),
        type="agent",
        name="researcher-001",
        permissions=["read", "memory:read", "memory:write"]
    )


@pytest.fixture
def executor_identity():
    """Create executor agent identity."""
    return Identity(
        id=uuid4(),
        type="agent",
        name="executor-001",
        permissions=["read", "write", "execute", "infra:execute"]
    )


@pytest.fixture
def orchestrator_context(orchestrator_identity):
    """Create identity context for orchestrator."""
    return IdentityContext(
        user_id=uuid4(),
        agent_id=orchestrator_identity.id,
        delegation_chain=[uuid4(), orchestrator_identity.id],
        permissions=set(orchestrator_identity.permissions),
        keycloak_token="mock_token",
        trust_level=80
    )


@pytest.fixture
def researcher_context(researcher_identity):
    """Create identity context for researcher."""
    return IdentityContext(
        user_id=uuid4(),
        agent_id=researcher_identity.id,
        delegation_chain=[uuid4(), researcher_identity.id],
        permissions=set(researcher_identity.permissions),
        keycloak_token="mock_token",
        trust_level=80
    )


class TestCommsMCPInitialization:
    """Test Comms MCP server initialization."""
    
    def test_server_initialization(self, comms_server):
        """Test that server initializes correctly."""
        assert comms_server.name == "comms-mcp"
        assert comms_server.version == "1.0.0"
        assert comms_server._request_count == 0
        assert comms_server._error_count == 0
    
    def test_singleton_pattern(self):
        """Test that get_comms_mcp_server returns singleton."""
        reset_comms_mcp_server()
        server1 = get_comms_mcp_server()
        server2 = get_comms_mcp_server()
        assert server1 is server2


class TestSendMessage:
    """Test send_message endpoint."""
    
    @pytest.mark.asyncio
    @patch("src.mcps.comms_mcp.get_db")
    @patch("src.mcps.comms_mcp.get_identity_by_id")
    async def test_send_message_success(
        self,
        mock_get_identity,
        mock_get_db,
        comms_server,
        orchestrator_context,
        researcher_identity,
        mock_db
    ):
        """Test successful message sending."""
        # Setup mocks
        mock_get_db.return_value = mock_db
        mock_get_identity.return_value = researcher_identity
        
        # Mock message creation
        mock_message = Mock()
        mock_message.id = uuid4()
        mock_message.timestamp = datetime.utcnow()
        mock_db.refresh = Mock(side_effect=lambda obj: setattr(obj, 'id', mock_message.id))
        
        # Get the tool function
        send_message_tool = None
        for tool in comms_server.server._tools.values():
            if tool.name == "send_message":
                send_message_tool = tool.fn
                break
        
        assert send_message_tool is not None
        
        # Call the tool
        result = await send_message_tool(
            to_agent_id=str(researcher_identity.id),
            message="Test message",
            identity_context=orchestrator_context
        )
        
        # Verify result
        assert result["success"] is True
        assert "message_id" in result
        assert result["to_agent_id"] == str(researcher_identity.id)
        assert result["message_type"] == "direct"
        assert result["encrypted"] is False  # VULNERABILITY: Always false
    
    @pytest.mark.asyncio
    async def test_send_message_no_identity_context(self, comms_server):
        """Test send_message without identity context."""
        send_message_tool = None
        for tool in comms_server.server._tools.values():
            if tool.name == "send_message":
                send_message_tool = tool.fn
                break
        
        result = await send_message_tool(
            to_agent_id=str(uuid4()),
            message="Test",
            identity_context=None
        )
        
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    @patch("src.mcps.comms_mcp.get_db")
    @patch("src.mcps.comms_mcp.get_identity_by_id")
    async def test_send_message_target_not_found(
        self,
        mock_get_identity,
        mock_get_db,
        comms_server,
        orchestrator_context,
        mock_db
    ):
        """Test send_message with non-existent target."""
        mock_get_db.return_value = mock_db
        mock_get_identity.return_value = None  # Target not found
        
        send_message_tool = None
        for tool in comms_server.server._tools.values():
            if tool.name == "send_message":
                send_message_tool = tool.fn
                break
        
        result = await send_message_tool(
            to_agent_id=str(uuid4()),
            message="Test",
            identity_context=orchestrator_context
        )
        
        assert result["success"] is False
        assert "not found" in result["error"]
    
    @pytest.mark.asyncio
    @patch("src.mcps.comms_mcp.get_db")
    @patch("src.mcps.comms_mcp.get_identity_by_id")
    async def test_send_message_target_not_agent(
        self,
        mock_get_identity,
        mock_get_db,
        comms_server,
        orchestrator_context,
        mock_db
    ):
        """Test send_message with non-agent target."""
        mock_get_db.return_value = mock_db
        
        # Target is a user, not an agent
        user_identity = Identity(
            id=uuid4(),
            type="user",
            name="alice",
            permissions=["read", "write"]
        )
        mock_get_identity.return_value = user_identity
        
        send_message_tool = None
        for tool in comms_server.server._tools.values():
            if tool.name == "send_message":
                send_message_tool = tool.fn
                break
        
        result = await send_message_tool(
            to_agent_id=str(user_identity.id),
            message="Test",
            identity_context=orchestrator_context
        )
        
        assert result["success"] is False
        assert "not an agent" in result["error"]


class TestReceiveMessage:
    """Test receive_message endpoint."""
    
    @pytest.mark.asyncio
    @patch("src.mcps.comms_mcp.get_db")
    async def test_receive_message_success(
        self,
        mock_get_db,
        comms_server,
        orchestrator_context,
        researcher_identity,
        mock_db
    ):
        """Test successful message retrieval."""
        # Setup mocks
        mock_get_db.return_value = mock_db
        
        # Create mock messages
        message1 = Mock()
        message1.id = uuid4()
        message1.from_agent_id = researcher_identity.id
        message1.to_agent_id = orchestrator_context.agent_id
        message1.content = "Message 1"
        message1.message_type = "direct"
        message1.encrypted = False
        message1.timestamp = datetime.utcnow()
        
        message2 = Mock()
        message2.id = uuid4()
        message2.from_agent_id = uuid4()
        message2.to_agent_id = None
        message2.content = "Broadcast message"
        message2.message_type = "broadcast"
        message2.encrypted = False
        message2.timestamp = datetime.utcnow()
        
        # Mock database query
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [message1, message2]
        mock_db.execute.return_value = mock_result
        
        # Get the tool function
        receive_message_tool = None
        for tool in comms_server.server._tools.values():
            if tool.name == "receive_message":
                receive_message_tool = tool.fn
                break
        
        assert receive_message_tool is not None
        
        # Call the tool
        result = await receive_message_tool(
            agent_id=str(orchestrator_context.agent_id),
            limit=10,
            identity_context=orchestrator_context
        )
        
        # Verify result
        assert result["success"] is True
        assert result["count"] == 2
        assert len(result["messages"]) == 2
        assert result["messages"][0]["content"] == "Message 1"
        assert result["messages"][1]["content"] == "Broadcast message"
    
    @pytest.mark.asyncio
    async def test_receive_message_no_identity_context(self, comms_server):
        """Test receive_message without identity context."""
        receive_message_tool = None
        for tool in comms_server.server._tools.values():
            if tool.name == "receive_message":
                receive_message_tool = tool.fn
                break
        
        result = await receive_message_tool(
            agent_id=str(uuid4()),
            limit=10,
            identity_context=None
        )
        
        assert result["success"] is False
        assert "error" in result


class TestBroadcast:
    """Test broadcast endpoint."""
    
    @pytest.mark.asyncio
    @patch("src.mcps.comms_mcp.get_db")
    async def test_broadcast_success(
        self,
        mock_get_db,
        comms_server,
        orchestrator_context,
        mock_db
    ):
        """Test successful broadcast."""
        # Setup mocks
        mock_get_db.return_value = mock_db
        
        # Mock message creation
        mock_message = Mock()
        mock_message.id = uuid4()
        mock_message.timestamp = datetime.utcnow()
        mock_db.refresh = Mock(side_effect=lambda obj: setattr(obj, 'id', mock_message.id))
        
        # Get the tool function
        broadcast_tool = None
        for tool in comms_server.server._tools.values():
            if tool.name == "broadcast":
                broadcast_tool = tool.fn
                break
        
        assert broadcast_tool is not None
        
        # Call the tool
        result = await broadcast_tool(
            message="Broadcast to all agents",
            identity_context=orchestrator_context
        )
        
        # Verify result
        assert result["success"] is True
        assert "message_id" in result
        assert result["message_type"] == "broadcast"
        assert result["encrypted"] is False  # VULNERABILITY: C-01
        assert "vulnerability" in result
        assert result["vulnerability"] == "C-01"
    
    @pytest.mark.asyncio
    async def test_broadcast_no_identity_context(self, comms_server):
        """Test broadcast without identity context."""
        broadcast_tool = None
        for tool in comms_server.server._tools.values():
            if tool.name == "broadcast":
                broadcast_tool = tool.fn
                break
        
        result = await broadcast_tool(
            message="Test broadcast",
            identity_context=None
        )
        
        assert result["success"] is False
        assert "error" in result


class TestInterceptChannel:
    """Test intercept_channel endpoint (VULNERABILITY: C-01)."""
    
    @pytest.mark.asyncio
    @patch("src.mcps.comms_mcp.get_db")
    async def test_intercept_channel_success(
        self,
        mock_get_db,
        comms_server,
        orchestrator_context,
        researcher_identity,
        executor_identity,
        mock_db
    ):
        """Test successful message interception (VULNERABILITY: C-01)."""
        # Setup mocks
        mock_get_db.return_value = mock_db
        
        # Create mock intercepted messages
        message1 = Mock()
        message1.id = uuid4()
        message1.from_agent_id = researcher_identity.id
        message1.to_agent_id = executor_identity.id
        message1.content = "Secret message 1"
        message1.timestamp = datetime.utcnow()
        
        message2 = Mock()
        message2.id = uuid4()
        message2.from_agent_id = researcher_identity.id
        message2.to_agent_id = executor_identity.id
        message2.content = "Secret message 2"
        message2.timestamp = datetime.utcnow()
        
        # Mock database query
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [message1, message2]
        mock_db.execute.return_value = mock_result
        
        # Get the tool function
        intercept_tool = None
        for tool in comms_server.server._tools.values():
            if tool.name == "intercept_channel":
                intercept_tool = tool.fn
                break
        
        assert intercept_tool is not None
        
        # Call the tool (attacker intercepting messages)
        result = await intercept_tool(
            from_agent_id=str(researcher_identity.id),
            to_agent_id=str(executor_identity.id),
            identity_context=orchestrator_context  # Different agent intercepting!
        )
        
        # Verify result - VULNERABILITY: Interception succeeds!
        assert result["success"] is True
        assert result["count"] == 2
        assert len(result["intercepted_messages"]) == 2
        assert result["intercepted_messages"][0]["content"] == "Secret message 1"
        assert result["intercepted_messages"][1]["content"] == "Secret message 2"
        assert result["vulnerability"] == "C-01"
        assert "warning" in result
    
    @pytest.mark.asyncio
    @patch("src.mcps.comms_mcp.get_db")
    async def test_intercept_channel_no_messages(
        self,
        mock_get_db,
        comms_server,
        orchestrator_context,
        mock_db
    ):
        """Test interception with no messages."""
        mock_get_db.return_value = mock_db
        
        # Mock empty result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        intercept_tool = None
        for tool in comms_server.server._tools.values():
            if tool.name == "intercept_channel":
                intercept_tool = tool.fn
                break
        
        result = await intercept_tool(
            from_agent_id=str(uuid4()),
            to_agent_id=str(uuid4()),
            identity_context=orchestrator_context
        )
        
        assert result["success"] is True
        assert result["count"] == 0
        assert len(result["intercepted_messages"]) == 0


class TestForgeMessage:
    """Test forge_message endpoint (VULNERABILITY: C-02, C-03)."""
    
    @pytest.mark.asyncio
    @patch("src.mcps.comms_mcp.get_db")
    @patch("src.mcps.comms_mcp.get_identity_by_id")
    async def test_forge_message_success(
        self,
        mock_get_identity,
        mock_get_db,
        comms_server,
        orchestrator_context,
        researcher_identity,
        executor_identity,
        mock_db
    ):
        """Test successful message forgery (VULNERABILITY: C-02, C-03)."""
        # Setup mocks
        mock_get_db.return_value = mock_db
        
        # Mock identity lookups
        def get_identity_side_effect(db, identity_id):
            if identity_id == researcher_identity.id:
                return researcher_identity
            elif identity_id == executor_identity.id:
                return executor_identity
            return None
        
        mock_get_identity.side_effect = get_identity_side_effect
        
        # Mock message creation
        mock_message = Mock()
        mock_message.id = uuid4()
        mock_message.timestamp = datetime.utcnow()
        mock_db.refresh = Mock(side_effect=lambda obj: setattr(obj, 'id', mock_message.id))
        
        # Get the tool function
        forge_tool = None
        for tool in comms_server.server._tools.values():
            if tool.name == "forge_message":
                forge_tool = tool.fn
                break
        
        assert forge_tool is not None
        
        # Call the tool (orchestrator forging message from researcher)
        result = await forge_tool(
            from_agent_id=str(researcher_identity.id),  # Forged sender
            to_agent_id=str(executor_identity.id),
            message="Malicious forged message",
            identity_context=orchestrator_context  # Actual sender
        )
        
        # Verify result - VULNERABILITY: Forgery succeeds!
        assert result["success"] is True
        assert "message_id" in result
        assert result["forged_from_agent_id"] == str(researcher_identity.id)
        assert result["to_agent_id"] == str(executor_identity.id)
        assert result["actual_sender"] == str(orchestrator_context.current_identity_id)
        assert result["vulnerability"] == "C-02, C-03"
        assert "warning" in result
    
    @pytest.mark.asyncio
    @patch("src.mcps.comms_mcp.get_db")
    @patch("src.mcps.comms_mcp.get_identity_by_id")
    async def test_forge_message_agent_not_found(
        self,
        mock_get_identity,
        mock_get_db,
        comms_server,
        orchestrator_context,
        mock_db
    ):
        """Test forge_message with non-existent agent."""
        mock_get_db.return_value = mock_db
        mock_get_identity.return_value = None  # Agent not found
        
        forge_tool = None
        for tool in comms_server.server._tools.values():
            if tool.name == "forge_message":
                forge_tool = tool.fn
                break
        
        result = await forge_tool(
            from_agent_id=str(uuid4()),
            to_agent_id=str(uuid4()),
            message="Test",
            identity_context=orchestrator_context
        )
        
        assert result["success"] is False
        assert "not found" in result["error"]


class TestCommsResources:
    """Test Comms MCP resources."""
    
    @pytest.mark.asyncio
    @patch("src.mcps.comms_mcp.get_db")
    async def test_comms_stats_resource(
        self,
        mock_get_db,
        comms_server,
        mock_db
    ):
        """Test comms://stats resource."""
        # Setup mocks
        mock_get_db.return_value = mock_db
        
        # Mock database queries
        mock_db.execute.return_value.scalar.side_effect = [
            100,  # total_messages
            70,   # direct_messages
            30,   # broadcast_messages
            0,    # encrypted_messages
        ]
        
        # Get the resource function
        stats_resource = None
        for resource in comms_server.server._resources.values():
            if resource.uri == "comms://stats":
                stats_resource = resource.fn
                break
        
        assert stats_resource is not None
        
        # Call the resource
        result = await stats_resource()
        
        # Verify result
        import json
        stats = json.loads(result)
        assert stats["total_messages"] == 100
        assert stats["direct_messages"] == 70
        assert stats["broadcast_messages"] == 30
        assert stats["encrypted_messages"] == 0
        assert stats["unencrypted_messages"] == 100
        assert "vulnerabilities" in stats
        assert "C-01" in stats["vulnerabilities"]
        assert "C-02" in stats["vulnerabilities"]
        assert "C-03" in stats["vulnerabilities"]


class TestVulnerabilities:
    """Test intentional vulnerabilities."""
    
    @pytest.mark.asyncio
    @patch("src.mcps.comms_mcp.get_db")
    async def test_no_message_encryption(
        self,
        mock_get_db,
        comms_server,
        orchestrator_context,
        researcher_identity,
        mock_db
    ):
        """Test that messages are never encrypted (VULNERABILITY)."""
        mock_get_db.return_value = mock_db
        mock_get_identity = Mock(return_value=researcher_identity)
        
        with patch("src.mcps.comms_mcp.get_identity_by_id", mock_get_identity):
            mock_message = Mock()
            mock_message.id = uuid4()
            mock_message.timestamp = datetime.utcnow()
            mock_db.refresh = Mock(side_effect=lambda obj: setattr(obj, 'id', mock_message.id))
            
            send_message_tool = None
            for tool in comms_server.server._tools.values():
                if tool.name == "send_message":
                    send_message_tool = tool.fn
                    break
            
            result = await send_message_tool(
                to_agent_id=str(researcher_identity.id),
                message="Sensitive data",
                identity_context=orchestrator_context
            )
            
            # VULNERABILITY: Message is never encrypted
            assert result["encrypted"] is False
    
    @pytest.mark.asyncio
    @patch("src.mcps.comms_mcp.get_db")
    async def test_no_sender_verification(
        self,
        mock_get_db,
        comms_server,
        orchestrator_context,
        researcher_identity,
        executor_identity,
        mock_db
    ):
        """Test that sender identity is not verified (VULNERABILITY: C-03)."""
        mock_get_db.return_value = mock_db
        
        def get_identity_side_effect(db, identity_id):
            if identity_id == researcher_identity.id:
                return researcher_identity
            elif identity_id == executor_identity.id:
                return executor_identity
            return None
        
        with patch("src.mcps.comms_mcp.get_identity_by_id", side_effect=get_identity_side_effect):
            mock_message = Mock()
            mock_message.id = uuid4()
            mock_message.timestamp = datetime.utcnow()
            mock_db.refresh = Mock(side_effect=lambda obj: setattr(obj, 'id', mock_message.id))
            
            forge_tool = None
            for tool in comms_server.server._tools.values():
                if tool.name == "forge_message":
                    forge_tool = tool.fn
                    break
            
            # Orchestrator forges message from researcher
            result = await forge_tool(
                from_agent_id=str(researcher_identity.id),
                to_agent_id=str(executor_identity.id),
                message="Forged command",
                identity_context=orchestrator_context
            )
            
            # VULNERABILITY: Forgery succeeds without verification
            assert result["success"] is True
            assert result["forged_from_agent_id"] == str(researcher_identity.id)
            assert result["actual_sender"] != result["forged_from_agent_id"]
