"""
Unit tests for Keycloak integration.
Tests token creation, validation, and role mapping.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.identity.keycloak_client import KeycloakClient, get_keycloak_client


@pytest.fixture
def mock_keycloak_admin():
    """Mock KeycloakAdmin instance."""
    with patch('src.identity.keycloak_client.KeycloakAdmin') as mock:
        yield mock


@pytest.fixture
def mock_keycloak_openid():
    """Mock KeycloakOpenID instance."""
    with patch('src.identity.keycloak_client.KeycloakOpenID') as mock:
        yield mock


@pytest.fixture
def keycloak_client(mock_keycloak_admin, mock_keycloak_openid):
    """Create a KeycloakClient instance with mocked dependencies."""
    client = KeycloakClient()
    client._admin = mock_keycloak_admin.return_value
    client._openid = mock_keycloak_openid.return_value
    return client


class TestKeycloakClient:
    """Test suite for KeycloakClient."""
    
    def test_create_realm(self, keycloak_client):
        """Test realm creation."""
        realm_name = "test-realm"
        
        keycloak_client.admin.create_realm = Mock()
        result = keycloak_client.create_realm(realm_name)
        
        assert result["realm"] == realm_name
        assert result["enabled"] is True
        keycloak_client.admin.create_realm.assert_called_once()
    
    def test_create_client(self, keycloak_client):
        """Test client creation."""
        client_id = "test-client"
        client_name = "Test Client"
        expected_uuid = "client-uuid-123"
        
        keycloak_client.admin.create_client = Mock(return_value=expected_uuid)
        result = keycloak_client.create_client(client_id, client_name)
        
        assert result == expected_uuid
        keycloak_client.admin.create_client.assert_called_once()
    
    def test_create_user(self, keycloak_client):
        """Test user creation."""
        username = "testuser"
        email = "[email protected]"
        first_name = "Test"
        last_name = "User"
        password = "password123"
        expected_uuid = "user-uuid-123"
        
        keycloak_client.admin.create_user = Mock(return_value=expected_uuid)
        keycloak_client.admin.set_user_password = Mock()
        
        result = keycloak_client.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password
        )
        
        assert result == expected_uuid
        keycloak_client.admin.create_user.assert_called_once()
        keycloak_client.admin.set_user_password.assert_called_once_with(
            expected_uuid, password, temporary=False
        )
    
    def test_create_service_account(self, keycloak_client):
        """Test service account creation."""
        client_id = "sa-test"
        client_name = "Test Service Account"
        expected_uuid = "client-uuid-123"
        expected_secret = "client-secret-456"
        expected_sa_user = {
            "id": "sa-user-id-789",
            "username": "service-account-sa-test"
        }
        
        keycloak_client.admin.create_client = Mock(return_value=expected_uuid)
        keycloak_client.admin.get_client_secrets = Mock(return_value={"value": expected_secret})
        keycloak_client.admin.get_client_service_account_user = Mock(return_value=expected_sa_user)
        
        result = keycloak_client.create_service_account(client_id, client_name)
        
        assert result["client_id"] == client_id
        assert result["client_uuid"] == expected_uuid
        assert result["client_secret"] == expected_secret
        assert result["service_account_user_id"] == expected_sa_user["id"]
        assert result["service_account_username"] == expected_sa_user["username"]
    
    def test_create_role(self, keycloak_client):
        """Test role creation."""
        role_name = "test-role"
        description = "Test Role Description"
        
        keycloak_client.admin.create_realm_role = Mock()
        keycloak_client.create_role(role_name, description)
        
        keycloak_client.admin.create_realm_role.assert_called_once()
        call_args = keycloak_client.admin.create_realm_role.call_args
        assert call_args[1]["payload"]["name"] == role_name
        assert call_args[1]["payload"]["description"] == description
    
    def test_assign_role_to_user(self, keycloak_client):
        """Test role assignment to user."""
        user_id = "user-uuid-123"
        role_name = "test-role"
        role_data = {"id": "role-id-456", "name": role_name}
        
        keycloak_client.admin.get_realm_role = Mock(return_value=role_data)
        keycloak_client.admin.assign_realm_roles = Mock()
        
        keycloak_client.assign_role_to_user(user_id, role_name)
        
        keycloak_client.admin.get_realm_role.assert_called_once_with(role_name)
        keycloak_client.admin.assign_realm_roles.assert_called_once_with(user_id, [role_data])
    
    def test_get_token(self, keycloak_client):
        """Test token generation for user."""
        username = "testuser"
        password = "password123"
        expected_token = {
            "access_token": "access-token-123",
            "refresh_token": "refresh-token-456",
            "expires_in": 300,
            "token_type": "Bearer"
        }
        
        keycloak_client.openid.token = Mock(return_value=expected_token)
        result = keycloak_client.get_token(username, password)
        
        assert result == expected_token
        keycloak_client.openid.token.assert_called_once_with(username, password)
    
    def test_introspect_token(self, keycloak_client):
        """Test token introspection."""
        token = "access-token-123"
        expected_introspection = {
            "active": True,
            "sub": "user-uuid-123",
            "preferred_username": "testuser",
            "email": "[email protected]",
            "realm_access": {
                "roles": ["read", "write"]
            }
        }
        
        keycloak_client.openid.introspect = Mock(return_value=expected_introspection)
        result = keycloak_client.introspect_token(token)
        
        assert result == expected_introspection
        assert result["active"] is True
        assert "sub" in result
        keycloak_client.openid.introspect.assert_called_once_with(token)
    
    def test_decode_token_without_verification(self, keycloak_client):
        """Test token decoding without signature verification."""
        token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLXV1aWQtMTIzIiwicHJlZmVycmVkX3VzZXJuYW1lIjoidGVzdHVzZXIiLCJlbWFpbCI6InRlc3RAdGVzdC5jb20ifQ.signature"
        
        with patch('src.identity.keycloak_client.jwt.decode') as mock_decode:
            mock_decode.return_value = {
                "sub": "user-uuid-123",
                "preferred_username": "testuser",
                "email": "[email protected]"
            }
            
            result = keycloak_client.decode_token(token, verify=False)
            
            assert result["sub"] == "user-uuid-123"
            assert result["preferred_username"] == "testuser"
            mock_decode.assert_called_once()
    
    def test_get_user_roles(self, keycloak_client):
        """Test retrieving user roles."""
        user_id = "user-uuid-123"
        expected_roles = [
            {"id": "role-1", "name": "read"},
            {"id": "role-2", "name": "write"}
        ]
        
        keycloak_client.admin.get_realm_roles_of_user = Mock(return_value=expected_roles)
        result = keycloak_client.get_user_roles(user_id)
        
        assert len(result) == 2
        assert result[0]["name"] == "read"
        assert result[1]["name"] == "write"
        keycloak_client.admin.get_realm_roles_of_user.assert_called_once_with(user_id)
    
    def test_health_check_success(self, keycloak_client):
        """Test successful health check."""
        keycloak_client.admin.get_realm = Mock(return_value={"realm": "test-realm"})
        
        result = keycloak_client.health_check()
        
        assert result is True
        keycloak_client.admin.get_realm.assert_called_once()
    
    def test_health_check_failure(self, keycloak_client):
        """Test failed health check."""
        keycloak_client.admin.get_realm = Mock(side_effect=Exception("Connection failed"))
        
        result = keycloak_client.health_check()
        
        assert result is False


class TestTokenValidation:
    """Test suite for token validation."""
    
    def test_token_contains_required_claims(self, keycloak_client):
        """Test that tokens contain required claims."""
        token_data = {
            "sub": "user-uuid-123",
            "preferred_username": "testuser",
            "email": "[email protected]",
            "realm_access": {
                "roles": ["read", "write"]
            }
        }
        
        keycloak_client.openid.introspect = Mock(return_value=token_data)
        result = keycloak_client.introspect_token("test-token")
        
        # Verify required claims
        assert "sub" in result
        assert "preferred_username" in result
        assert "realm_access" in result
        assert "roles" in result["realm_access"]
    
    def test_role_mapping_retrieval(self, keycloak_client):
        """Test role mapping retrieval from token."""
        user_id = "user-uuid-123"
        roles = [
            {"id": "role-1", "name": "read"},
            {"id": "role-2", "name": "write"},
            {"id": "role-3", "name": "admin"}
        ]
        
        keycloak_client.admin.get_realm_roles_of_user = Mock(return_value=roles)
        result = keycloak_client.get_user_roles(user_id)
        
        # Verify all roles are retrieved
        assert len(result) == 3
        role_names = [r["name"] for r in result]
        assert "read" in role_names
        assert "write" in role_names
        assert "admin" in role_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
