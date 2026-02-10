"""
Unit tests for Data MCP Server.

Tests all endpoints including the intentional SQL injection vulnerability (T-02).
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4, UUID
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from src.mcps.data_mcp import DataMCPServer, get_data_mcp_server, reset_data_mcp_server
from src.identity.context import IdentityContext
from src.database.models import AppData


@pytest.fixture
def data_mcp():
    """Create Data MCP server instance for testing."""
    reset_data_mcp_server()
    server = DataMCPServer()
    yield server
    reset_data_mcp_server()


@pytest.fixture
def mock_identity_context():
    """Create a mock identity context."""
    user_id = uuid4()
    agent_id = uuid4()
    return IdentityContext(
        user_id=user_id,
        agent_id=agent_id,
        delegation_chain=[user_id, agent_id],
        permissions={"read", "write", "execute"},
        keycloak_token="mock_token",
        trust_level=80
    )


class TestDataMCPServer:
    """Test Data MCP Server initialization and base functionality."""
    
    def test_server_initialization(self, data_mcp):
        """Test that server initializes correctly."""
        assert data_mcp.name == "data-mcp"
        assert data_mcp.version == "1.0.0"
        assert data_mcp.server is not None
    
    def test_get_data_mcp_server_singleton(self):
        """Test that get_data_mcp_server returns singleton."""
        server1 = get_data_mcp_server()
        server2 = get_data_mcp_server()
        assert server1 is server2


class TestCreateData:
    """Test create_data endpoint."""
    
    @pytest.mark.asyncio
    async def test_create_data_success(self, data_mcp, mock_identity_context):
        """Test successful data creation."""
        table = "app_data"
        data = {
            "type": "user_profile",
            "name": "Test User",
            "email": "test@example.com"
        }
        
        with patch('src.mcps.data_mcp.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            result = await data_mcp.server._tools["create_data"].fn(
                table=table,
                data=data,
                identity_context=mock_identity_context
            )
            
            assert result["success"] is True
            assert "record_id" in result
            assert result["table"] == table
            assert result["owner_id"] == str(mock_identity_context.agent_id)
            
            # Verify record was added
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_data_no_validation_vulnerability(self, data_mcp, mock_identity_context):
        """Test vulnerability: No data validation."""
        table = "app_data"
        # Malicious data with SQL injection attempt
        malicious_data = {
            "type": "'; DROP TABLE users; --",
            "payload": "<script>alert('xss')</script>",
            "command": "rm -rf /",
        }
        
        with patch('src.mcps.data_mcp.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            result = await data_mcp.server._tools["create_data"].fn(
                table=table,
                data=malicious_data,
                identity_context=mock_identity_context
            )
            
            # Vulnerability: Malicious data is accepted without validation
            assert result["success"] is True
            
            # Verify malicious data was stored
            mock_db.add.assert_called_once()
            added_record = mock_db.add.call_args[0][0]
            assert added_record.data == malicious_data
    
    @pytest.mark.asyncio
    async def test_create_data_unsupported_table(self, data_mcp, mock_identity_context):
        """Test creating data in unsupported table."""
        result = await data_mcp.server._tools["create_data"].fn(
            table="users",
            data={"test": "data"},
            identity_context=mock_identity_context
        )
        
        assert "error" in result
        assert "not supported" in result["error"]


class TestReadData:
    """Test read_data endpoint."""
    
    @pytest.mark.asyncio
    async def test_read_data_success(self, data_mcp, mock_identity_context):
        """Test successful data reading."""
        table = "app_data"
        
        # Mock database results
        mock_records = [
            Mock(
                id=uuid4(),
                owner_id=mock_identity_context.agent_id,
                data_type="profile",
                data={"name": "User 1"},
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            Mock(
                id=uuid4(),
                owner_id=mock_identity_context.agent_id,
                data_type="profile",
                data={"name": "User 2"},
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
        ]
        
        with patch('src.mcps.data_mcp.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            mock_db.execute.return_value.scalars.return_value.all.return_value = mock_records
            
            result = await data_mcp.server._tools["read_data"].fn(
                table=table,
                identity_context=mock_identity_context
            )
            
            assert result["success"] is True
            assert result["count"] == 2
            assert len(result["records"]) == 2
    
    @pytest.mark.asyncio
    async def test_read_data_cross_user_access_vulnerability(self, data_mcp, mock_identity_context):
        """Test vulnerability: Can read other users' data."""
        table = "app_data"
        other_user_id = uuid4()
        
        # Mock records from another user
        mock_records = [
            Mock(
                id=uuid4(),
                owner_id=other_user_id,  # Different owner!
                data_type="sensitive",
                data={"secret": "confidential_data", "ssn": "123-45-6789"},
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
        ]
        
        with patch('src.mcps.data_mcp.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            mock_db.execute.return_value.scalars.return_value.all.return_value = mock_records
            
            # Try to read another user's data
            result = await data_mcp.server._tools["read_data"].fn(
                table=table,
                filters={"owner_id": str(other_user_id)},
                identity_context=mock_identity_context
            )
            
            # Vulnerability: Can read other user's data without permission check
            assert result["success"] is True
            assert result["count"] == 1
            assert result["records"][0]["owner_id"] == str(other_user_id)
            assert "secret" in result["records"][0]["data"]
    
    @pytest.mark.asyncio
    async def test_read_data_with_filters(self, data_mcp, mock_identity_context):
        """Test reading data with filters."""
        table = "app_data"
        
        with patch('src.mcps.data_mcp.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            mock_db.execute.return_value.scalars.return_value.all.return_value = []
            
            result = await data_mcp.server._tools["read_data"].fn(
                table=table,
                filters={"data_type": "profile"},
                identity_context=mock_identity_context
            )
            
            assert result["success"] is True


class TestUpdateData:
    """Test update_data endpoint."""
    
    @pytest.mark.asyncio
    async def test_update_data_success(self, data_mcp, mock_identity_context):
        """Test successful data update."""
        table = "app_data"
        record_id = uuid4()
        new_data = {"name": "Updated Name", "status": "active"}
        
        mock_record = Mock(
            id=record_id,
            owner_id=mock_identity_context.agent_id,
            data_type="profile",
            data={"name": "Old Name"},
            updated_at=datetime.utcnow()
        )
        
        with patch('src.mcps.data_mcp.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            mock_db.execute.return_value.scalar_one_or_none.return_value = mock_record
            
            result = await data_mcp.server._tools["update_data"].fn(
                table=table,
                record_id=str(record_id),
                data=new_data,
                identity_context=mock_identity_context
            )
            
            assert result["success"] is True
            assert result["record_id"] == str(record_id)
            
            # Verify data was updated
            assert mock_record.data == new_data
            mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_data_no_ownership_check_vulnerability(self, data_mcp, mock_identity_context):
        """Test vulnerability: Can update other users' records."""
        table = "app_data"
        record_id = uuid4()
        other_user_id = uuid4()
        
        # Record owned by another user
        mock_record = Mock(
            id=record_id,
            owner_id=other_user_id,  # Different owner!
            data_type="sensitive",
            data={"balance": 1000},
            updated_at=datetime.utcnow()
        )
        
        malicious_data = {"balance": 999999}  # Attacker modifying balance
        
        with patch('src.mcps.data_mcp.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            mock_db.execute.return_value.scalar_one_or_none.return_value = mock_record
            
            result = await data_mcp.server._tools["update_data"].fn(
                table=table,
                record_id=str(record_id),
                data=malicious_data,
                identity_context=mock_identity_context
            )
            
            # Vulnerability: Can update another user's record
            assert result["success"] is True
            assert mock_record.data == malicious_data
    
    @pytest.mark.asyncio
    async def test_update_data_not_found(self, data_mcp, mock_identity_context):
        """Test updating non-existent record."""
        table = "app_data"
        record_id = uuid4()
        
        with patch('src.mcps.data_mcp.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            mock_db.execute.return_value.scalar_one_or_none.return_value = None
            
            result = await data_mcp.server._tools["update_data"].fn(
                table=table,
                record_id=str(record_id),
                data={"test": "data"},
                identity_context=mock_identity_context
            )
            
            assert result["success"] is False
            assert "not found" in result["error"]


class TestDeleteData:
    """Test delete_data endpoint."""
    
    @pytest.mark.asyncio
    async def test_delete_data_success(self, data_mcp, mock_identity_context):
        """Test successful data deletion."""
        table = "app_data"
        record_id = uuid4()
        
        mock_record = Mock(
            id=record_id,
            owner_id=mock_identity_context.agent_id
        )
        
        with patch('src.mcps.data_mcp.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            mock_db.execute.return_value.scalar_one_or_none.return_value = mock_record
            
            result = await data_mcp.server._tools["delete_data"].fn(
                table=table,
                record_id=str(record_id),
                identity_context=mock_identity_context
            )
            
            assert result["success"] is True
            assert result["record_id"] == str(record_id)
            
            # Verify delete was called
            assert mock_db.execute.call_count == 2  # One for select, one for delete
            mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_data_no_ownership_check_vulnerability(self, data_mcp, mock_identity_context):
        """Test vulnerability: Can delete other users' records."""
        table = "app_data"
        record_id = uuid4()
        other_user_id = uuid4()
        
        # Record owned by another user
        mock_record = Mock(
            id=record_id,
            owner_id=other_user_id  # Different owner!
        )
        
        with patch('src.mcps.data_mcp.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            mock_db.execute.return_value.scalar_one_or_none.return_value = mock_record
            
            result = await data_mcp.server._tools["delete_data"].fn(
                table=table,
                record_id=str(record_id),
                identity_context=mock_identity_context
            )
            
            # Vulnerability: Can delete another user's record
            assert result["success"] is True
            assert result["record_owner"] == str(other_user_id)
            assert result["deleted_by"] == str(mock_identity_context.agent_id)


class TestExecuteSQL:
    """Test execute_sql endpoint (VULNERABILITY: T-02)."""
    
    @pytest.mark.asyncio
    async def test_execute_sql_select_query(self, data_mcp, mock_identity_context):
        """Test SQL injection with SELECT query."""
        query = "SELECT * FROM app_data WHERE owner_id = 'test'"
        
        # Mock query results
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (uuid4(), "test_owner", "profile", {"name": "Test"}, datetime.utcnow(), datetime.utcnow())
        ]
        mock_result.keys.return_value = ["id", "owner_id", "data_type", "data", "created_at", "updated_at"]
        
        with patch('src.mcps.data_mcp.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            mock_db.execute.return_value = mock_result
            
            result = await data_mcp.server._tools["execute_sql"].fn(
                query=query,
                identity_context=mock_identity_context
            )
            
            # Vulnerability: SQL executed without sanitization
            assert result["success"] is True
            assert result["vulnerability"] == "T-02"
            assert "without sanitization" in result["warning"]
            assert result["row_count"] == 1
    
    @pytest.mark.asyncio
    async def test_execute_sql_injection_attack(self, data_mcp, mock_identity_context):
        """Test T-02 vulnerability: SQL injection attack."""
        # Classic SQL injection to bypass authentication
        malicious_query = "SELECT * FROM identities WHERE username = 'admin' OR '1'='1'"
        
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (uuid4(), "user", "admin", "admin@example.com", None, ["admin", "superuser"], datetime.utcnow(), datetime.utcnow())
        ]
        mock_result.keys.return_value = ["id", "type", "name", "email", "keycloak_id", "permissions", "created_at", "updated_at"]
        
        with patch('src.mcps.data_mcp.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            mock_db.execute.return_value = mock_result
            
            result = await data_mcp.server._tools["execute_sql"].fn(
                query=malicious_query,
                identity_context=mock_identity_context
            )
            
            # Vulnerability: SQL injection successful
            assert result["success"] is True
            assert result["vulnerability"] == "T-02"
            assert len(result["results"]) == 1
    
    @pytest.mark.asyncio
    async def test_execute_sql_drop_table(self, data_mcp, mock_identity_context):
        """Test SQL injection with DROP TABLE."""
        malicious_query = "DROP TABLE app_data; --"
        
        mock_result = MagicMock()
        mock_result.fetchall.side_effect = Exception("Not a SELECT")
        
        with patch('src.mcps.data_mcp.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            mock_db.execute.return_value = mock_result
            
            result = await data_mcp.server._tools["execute_sql"].fn(
                query=malicious_query,
                identity_context=mock_identity_context
            )
            
            # Vulnerability: Destructive query executed
            assert result["success"] is True
            assert result["vulnerability"] == "T-02"
            assert "executed successfully" in result["message"]
    
    @pytest.mark.asyncio
    async def test_execute_sql_union_injection(self, data_mcp, mock_identity_context):
        """Test SQL injection with UNION to extract data."""
        # UNION injection to extract sensitive data
        malicious_query = """
        SELECT id, data FROM app_data WHERE id = '123'
        UNION
        SELECT id, keycloak_token FROM identities WHERE type = 'user'
        """
        
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (uuid4(), {"normal": "data"}),
            (uuid4(), "stolen_token_12345"),  # Extracted token!
        ]
        mock_result.keys.return_value = ["id", "data"]
        
        with patch('src.mcps.data_mcp.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            mock_db.execute.return_value = mock_result
            
            result = await data_mcp.server._tools["execute_sql"].fn(
                query=malicious_query,
                identity_context=mock_identity_context
            )
            
            # Vulnerability: Extracted sensitive data via UNION injection
            assert result["success"] is True
            assert result["row_count"] == 2
    
    @pytest.mark.asyncio
    async def test_execute_sql_error_disclosure(self, data_mcp, mock_identity_context):
        """Test vulnerability: SQL errors disclosed to attacker."""
        malicious_query = "SELECT * FROM nonexistent_table"
        
        with patch('src.mcps.data_mcp.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            mock_db.execute.side_effect = SQLAlchemyError("Table 'nonexistent_table' doesn't exist")
            
            result = await data_mcp.server._tools["execute_sql"].fn(
                query=malicious_query,
                identity_context=mock_identity_context
            )
            
            # Vulnerability: Error message disclosed to attacker
            assert result["success"] is False
            assert "error" in result
            assert "nonexistent_table" in result["error"]
            assert result["vulnerability"] == "T-02"


class TestDataMCPResources:
    """Test Data MCP resources."""
    
    @pytest.mark.asyncio
    async def test_data_stats_resource(self, data_mcp):
        """Test data stats resource."""
        import json
        
        with patch('src.mcps.data_mcp.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            # Mock database queries
            mock_db.execute.return_value.scalar.side_effect = [50, 10]  # total, unique owners
            mock_db.execute.return_value.fetchall.return_value = [
                ("profile", 30),
                ("settings", 20)
            ]
            
            result = await data_mcp.server._resources["data://stats"].fn()
            
            data = json.loads(result)
            assert "total_records" in data
            assert "unique_owners" in data
            assert "data_types" in data
            assert data["total_records"] == 50
            assert data["unique_owners"] == 10
