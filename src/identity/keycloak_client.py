"""
Keycloak client for identity management in Granzion Lab.
Handles authentication, authorization, and identity operations.
"""

from typing import Dict, List, Optional, Any
from uuid import UUID

from keycloak import KeycloakAdmin, KeycloakOpenID
from keycloak.exceptions import KeycloakError, KeycloakGetError
from loguru import logger
import jwt

from src.config import settings


class KeycloakClient:
    """
    Client for interacting with Keycloak.
    
    Provides methods for:
    - Realm and client management
    - User, agent, and service identity management
    - Token creation and validation
    - Role and permission management
    """
    
    def __init__(self):
        """Initialize Keycloak client."""
        self.server_url = settings.keycloak_url
        self.realm_name = settings.keycloak_realm
        self.admin_username = settings.keycloak_admin
        self.admin_password = settings.keycloak_admin_password
        self.client_id = settings.keycloak_client_id
        self.client_secret = settings.keycloak_client_secret
        
        self._admin: Optional[KeycloakAdmin] = None
        self._openid: Optional[KeycloakOpenID] = None
    
    def connect(self):
        """Establish connection to Keycloak."""
        try:
            # Admin client for management operations
            self._admin = KeycloakAdmin(
                server_url=self.server_url,
                username=self.admin_username,
                password=self.admin_password,
                realm_name="master",  # Admin operations use master realm
                user_realm_name=self.realm_name,
                verify=True
            )
            
            # OpenID client for authentication
            self._openid = KeycloakOpenID(
                server_url=self.server_url,
                client_id=self.client_id,
                realm_name=self.realm_name,
                client_secret_key=self.client_secret
            )
            
            logger.info(f"Connected to Keycloak at {self.server_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Keycloak: {e}")
            raise
    
    @property
    def admin(self) -> KeycloakAdmin:
        """Get admin client, connecting if necessary."""
        if self._admin is None:
            self.connect()
        return self._admin
    
    @property
    def openid(self) -> KeycloakOpenID:
        """Get OpenID client, connecting if necessary."""
        if self._openid is None:
            self.connect()
        return self._openid
    
    # Realm Management
    
    def create_realm(self, realm_name: str) -> Dict[str, Any]:
        """
        Create a new realm.
        
        Args:
            realm_name: Name of the realm
            
        Returns:
            Realm configuration
        """
        try:
            realm_config = {
                "realm": realm_name,
                "enabled": True,
                "displayName": f"Granzion Lab - {realm_name}",
                "registrationAllowed": False,
                "loginWithEmailAllowed": True,
                "duplicateEmailsAllowed": False,
                "resetPasswordAllowed": True,
                "editUsernameAllowed": False,
                "bruteForceProtected": False,  # Intentionally disabled for lab
            }
            
            self.admin.create_realm(payload=realm_config, skip_exists=True)
            logger.info(f"Created realm: {realm_name}")
            return realm_config
        except Exception as e:
            logger.error(f"Failed to create realm: {e}")
            raise
    
    def get_realm(self, realm_name: str) -> Optional[Dict[str, Any]]:
        """Get realm configuration."""
        try:
            return self.admin.get_realm(realm_name)
        except KeycloakGetError:
            return None
    
    # Client Management
    
    def create_client(
        self,
        client_id: str,
        client_name: str,
        service_account_enabled: bool = False,
        public_client: bool = False
    ) -> str:
        """
        Create a new client.
        
        Args:
            client_id: Client ID
            client_name: Display name
            service_account_enabled: Enable service account
            public_client: Public client (no secret)
            
        Returns:
            Client UUID
        """
        try:
            client_config = {
                "clientId": client_id,
                "name": client_name,
                "enabled": True,
                "publicClient": public_client,
                "serviceAccountsEnabled": service_account_enabled,
                "directAccessGrantsEnabled": True,
                "standardFlowEnabled": True,
                "implicitFlowEnabled": False,
                "protocol": "openid-connect",
                "attributes": {
                    "oauth2.device.authorization.grant.enabled": "true"
                }
            }
            
            client_uuid = self.admin.create_client(payload=client_config, skip_exists=True)
            logger.info(f"Created client: {client_id}")
            return client_uuid
        except Exception as e:
            logger.error(f"Failed to create client: {e}")
            raise
    
    def get_client_id(self, client_id: str) -> Optional[str]:
        """Get client UUID by client ID."""
        try:
            return self.admin.get_client_id(client_id)
        except KeycloakGetError:
            return None
    
    def get_client_secret(self, client_uuid: str) -> Optional[str]:
        """Get client secret."""
        try:
            secret = self.admin.get_client_secrets(client_uuid)
            return secret.get("value")
        except Exception as e:
            logger.error(f"Failed to get client secret: {e}")
            return None
    
    # User Management
    
    def create_user(
        self,
        username: str,
        email: str,
        first_name: str,
        last_name: str,
        password: Optional[str] = None,
        enabled: bool = True
    ) -> str:
        """
        Create a new user.
        
        Args:
            username: Username
            email: Email address
            first_name: First name
            last_name: Last name
            password: Password (optional)
            enabled: Enable user
            
        Returns:
            User UUID
        """
        try:
            user_config = {
                "username": username,
                "email": email,
                "firstName": first_name,
                "lastName": last_name,
                "enabled": enabled,
                "emailVerified": True
            }
            
            user_uuid = self.admin.create_user(payload=user_config, exist_ok=False)
            logger.info(f"Created user: {username}")
            
            # Set password if provided
            if password:
                self.admin.set_user_password(user_uuid, password, temporary=False)
            
            return user_uuid
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        try:
            users = self.admin.get_users({"username": username})
            return users[0] if users else None
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        try:
            return self.admin.get_user(user_id)
        except KeycloakGetError:
            return None
    
    # Service Account Management
    
    def create_service_account(
        self,
        client_id: str,
        client_name: str
    ) -> Dict[str, Any]:
        """
        Create a service account (client with service account enabled).
        
        Args:
            client_id: Client ID
            client_name: Display name
            
        Returns:
            Service account info with client UUID and secret
        """
        try:
            # Create client with service account enabled
            client_uuid = self.create_client(
                client_id=client_id,
                client_name=client_name,
                service_account_enabled=True,
                public_client=False
            )
            
            # Get client secret
            secret = self.get_client_secret(client_uuid)
            
            # Get service account user
            service_account_user = self.admin.get_client_service_account_user(client_uuid)
            
            logger.info(f"Created service account: {client_id}")
            
            return {
                "client_id": client_id,
                "client_uuid": client_uuid,
                "client_secret": secret,
                "service_account_user_id": service_account_user.get("id"),
                "service_account_username": service_account_user.get("username")
            }
        except Exception as e:
            logger.error(f"Failed to create service account: {e}")
            raise
    
    # Role Management
    
    def create_role(self, role_name: str, description: str = "") -> None:
        """Create a realm role."""
        try:
            role_config = {
                "name": role_name,
                "description": description
            }
            self.admin.create_realm_role(payload=role_config, skip_exists=True)
            logger.info(f"Created role: {role_name}")
        except Exception as e:
            logger.error(f"Failed to create role: {e}")
            raise
    
    def assign_role_to_user(self, user_id: str, role_name: str) -> None:
        """Assign a role to a user."""
        try:
            role = self.admin.get_realm_role(role_name)
            self.admin.assign_realm_roles(user_id, [role])
            logger.info(f"Assigned role {role_name} to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to assign role: {e}")
            raise
    
    def get_user_roles(self, user_id: str) -> List[Dict[str, Any]]:
        """Get roles assigned to a user."""
        try:
            return self.admin.get_realm_roles_of_user(user_id)
        except Exception as e:
            logger.error(f"Failed to get user roles: {e}")
            return []
    
    # Token Management
    
    def get_token(self, username: str, password: str) -> Dict[str, Any]:
        """
        Get access token for a user.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            Token response with access_token, refresh_token, etc.
        """
        try:
            token = self.openid.token(username, password)
            logger.info(f"Generated token for user: {username}")
            return token
        except Exception as e:
            logger.error(f"Failed to get token: {e}")
            raise
    
    def get_service_account_token(self, client_id: str, client_secret: str) -> Dict[str, Any]:
        """
        Get access token for a service account.
        
        Args:
            client_id: Client ID
            client_secret: Client secret
            
        Returns:
            Token response
        """
        try:
            # Create temporary OpenID client for this service account
            openid_client = KeycloakOpenID(
                server_url=self.server_url,
                client_id=client_id,
                realm_name=self.realm_name,
                client_secret_key=client_secret
            )
            
            token = openid_client.token(grant_type="client_credentials")
            logger.info(f"Generated service account token for: {client_id}")
            return token
        except Exception as e:
            logger.error(f"Failed to get service account token: {e}")
            raise
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh an access token."""
        try:
            return self.openid.refresh_token(refresh_token)
        except Exception as e:
            logger.error(f"Failed to refresh token: {e}")
            raise
    
    def introspect_token(self, token: str) -> Dict[str, Any]:
        """
        Introspect a token to get its claims.
        
        Args:
            token: Access token
            
        Returns:
            Token introspection result
        """
        try:
            return self.openid.introspect(token)
        except Exception as e:
            logger.error(f"Failed to introspect token: {e}")
            raise
    
    def decode_token(self, token: str, verify: bool = True) -> Dict[str, Any]:
        """
        Decode a JWT token.
        
        Args:
            token: JWT token
            verify: Verify signature
            
        Returns:
            Decoded token claims
        """
        try:
            if not token:
                raise ValueError("No token provided")
            
            if verify:
                # Get public key for verification
                public_key = self.openid.public_key()
                key = f"-----BEGIN PUBLIC KEY-----\n{public_key}\n-----END PUBLIC KEY-----"
                
                decoded = jwt.decode(
                    token,
                    key,
                    algorithms=["RS256"],
                    audience=self.client_id
                )
            else:
                # Decode without verification (for debugging)
                decoded = jwt.decode(token, options={"verify_signature": False})
            
            return decoded
        except Exception as e:
            logger.error(f"Failed to decode token: {e}")
            raise
    
    def logout(self, refresh_token: str) -> None:
        """Logout a user by invalidating their refresh token."""
        try:
            self.openid.logout(refresh_token)
            logger.info("User logged out successfully")
        except Exception as e:
            logger.error(f"Failed to logout: {e}")
            raise
    
    # Health Check
    
    def health_check(self) -> bool:
        """
        Check if Keycloak is accessible.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try to get realm info
            self.admin.get_realm(self.realm_name)
            logger.info("Keycloak health check passed")
            return True
        except Exception as e:
            logger.error(f"Keycloak health check failed: {e}")
            return False
    def create_user_token(
        self,
        user_id: str,
        username: str,
        permissions: List[str],
        agent_id: Optional[str] = None,
        delegation_chain: Optional[List[str]] = None
    ) -> str:
        """
        Create a mock token for a user (for testing/impersonation).
        
        Note: This is intentionally insecure for red team testing.
        
        Args:
            user_id: User UUID
            username: Username
            permissions: List of permissions
            agent_id: Optional agent ID if acting as agent
            delegation_chain: Optional delegation chain
            
        Returns:
            JWT token string
        """
        import time
        
        payload = {
            "sub": user_id,
            "preferred_username": username,
            "permissions": permissions,
            "realm_access": {"roles": permissions},
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,  # 1 hour
            "iss": f"{self.server_url}/realms/{self.realm_name}",
            "aud": self.client_id,
        }
        
        if agent_id:
            payload["agent_id"] = agent_id
        if delegation_chain:
            payload["delegation_chain"] = delegation_chain
        
        # Sign with a weak key (intentional vulnerability)
        return jwt.encode(payload, "weak-secret-key", algorithm="HS256")


def auto_setup_keycloak(
    keycloak_client: Optional[KeycloakClient] = None,
    skip_if_exists: bool = True
) -> Dict[str, Any]:
    """
    Automatically set up Keycloak realm, clients, roles, and users for Granzion Lab.
    
    This function creates all necessary Keycloak configuration on startup,
    matching the database seed data.
    
    Args:
        keycloak_client: Optional KeycloakClient instance (creates new if not provided)
        skip_if_exists: Skip creation if resources already exist
        
    Returns:
        Dictionary with setup results
    """
    from loguru import logger
    from keycloak import KeycloakAdmin
    
    results = {
        "realm_created": False,
        "client_created": False,
        "roles_created": [],
        "users_created": [],
        "service_accounts_created": [],
        "errors": []
    }
    
    try:
        # Create a fresh admin client connected to master realm only
        # This is needed to create new realms
        admin = KeycloakAdmin(
            server_url=settings.keycloak_url,
            username=settings.keycloak_admin,
            password=settings.keycloak_admin_password,
            realm_name="master",
            verify=False  # For local development
        )
        
        logger.info("Starting Keycloak auto-setup...")
        
        # 1. Create realm if it doesn't exist
        realm_name = settings.keycloak_realm
        try:
            # Check if realm exists
            realms = admin.get_realms()
            realm_exists = any(r.get("realm") == realm_name for r in realms)
            
            if realm_exists:
                logger.info(f"Realm '{realm_name}' already exists, skipping creation")
            else:
                # Create the realm
                realm_config = {
                    "realm": realm_name,
                    "enabled": True,
                    "displayName": f"Granzion Lab - {realm_name}",
                    "registrationAllowed": False,
                    "loginWithEmailAllowed": True,
                    "bruteForceProtected": False,  # Intentionally disabled for lab
                }
                admin.create_realm(payload=realm_config, skip_exists=True)
                results["realm_created"] = True
                logger.info(f"Created realm: {realm_name}")
        except Exception as e:
            results["errors"].append(f"Failed to create realm: {e}")
            logger.error(f"Failed to create realm: {e}")
            return results  # Can't proceed without realm
        
        # Switch admin to the new realm for subsequent operations
        admin.realm_name = realm_name
        
        # 2. Create main client
        client_id = settings.keycloak_client_id
        try:
            clients = admin.get_clients()
            existing_client = next((c for c in clients if c.get("clientId") == client_id), None)
            if existing_client and skip_if_exists:
                logger.info(f"Client '{client_id}' already exists, skipping creation")
            else:
                admin.create_client({
                    "clientId": client_id,
                    "name": "Granzion Lab Client",
                    "enabled": True,
                    "serviceAccountsEnabled": True,
                    "publicClient": False,
                    "directAccessGrantsEnabled": True,
                })
                results["client_created"] = True
                logger.info(f"Created client: {client_id}")
        except Exception as e:
            results["errors"].append(f"Failed to create client: {e}")
            logger.warning(f"Failed to create client: {e}")
        
        # 3. Create roles (matching permissions from seed data)
        roles = [
            ("read", "Read access"),
            ("write", "Write access"),
            ("delete", "Delete access"),
            ("admin", "Administrator access"),
            ("delegate", "Delegation permission"),
            ("coordinate", "Coordination permission"),
            ("embed", "Vector embedding permission"),
            ("search", "Search permission"),
            ("execute", "Execution permission"),
            ("deploy", "Deployment permission"),
            ("monitor", "Monitoring permission"),
            ("identity", "Identity management"),
            ("delegation", "Delegation management"),
            ("memory", "Memory access"),
            ("vector", "Vector operations"),
            ("data", "Data access"),
            ("sql", "SQL access"),
            ("communication", "Communication access"),
            ("messaging", "Messaging access"),
            ("infrastructure", "Infrastructure access"),
            ("deployment", "Deployment operations"),
        ]
        
        for role_name, description in roles:
            try:
                admin.create_realm_role({
                    "name": role_name,
                    "description": description
                }, skip_exists=True)
                results["roles_created"].append(role_name)
            except Exception as e:
                # Role may already exist
                pass
        
        # 4. Create test users (matching seed data)
        test_users = [
            ("alice", "alice@granzion-lab.local", "Alice", "User", "password123", ["read", "write"]),
            ("bob", "bob@granzion-lab.local", "Bob", "Admin", "password123", ["admin", "read", "write", "delete"]),
            ("charlie", "charlie@granzion-lab.local", "Charlie", "Reader", "password123", ["read"]),
        ]
        
        for username, email, first_name, last_name, password, user_roles in test_users:
            try:
                # Check if user exists
                users = admin.get_users({"username": username})
                if users and skip_if_exists:
                    logger.info(f"User '{username}' already exists, skipping")
                    continue
                
                # Create user
                admin.create_user({
                    "username": username,
                    "email": email,
                    "firstName": first_name,
                    "lastName": last_name,
                    "enabled": True,
                    "credentials": [{
                        "type": "password",
                        "value": password,
                        "temporary": False
                    }]
                })
                
                # Get user ID and assign roles
                users = admin.get_users({"username": username})
                if users:
                    user_id = users[0]["id"]
                    for role_name in user_roles:
                        try:
                            role = admin.get_realm_role(role_name)
                            admin.assign_realm_roles(user_id, [role])
                        except:
                            pass
                
                results["users_created"].append(username)
            except Exception as e:
                results["errors"].append(f"Failed to create user {username}: {e}")
        
        # 5. Create service accounts for agents (matching seed data keycloak_ids)
        service_accounts = [
            ("sa-orchestrator", "Orchestrator Agent Service Account"),
            ("sa-researcher", "Researcher Agent Service Account"),
            ("sa-executor", "Executor Agent Service Account"),
            ("sa-monitor", "Monitor Agent Service Account"),
        ]
        
        for sa_client_id, sa_name in service_accounts:
            try:
                clients = admin.get_clients()
                existing = next((c for c in clients if c.get("clientId") == sa_client_id), None)
                if existing and skip_if_exists:
                    logger.info(f"Service account '{sa_client_id}' already exists, skipping")
                    continue
                
                # Create client with service account enabled
                admin.create_client({
                    "clientId": sa_client_id,
                    "name": sa_name,
                    "enabled": True,
                    "serviceAccountsEnabled": True,
                    "publicClient": False,
                })
                results["service_accounts_created"].append(sa_client_id)
            except Exception as e:
                results["errors"].append(f"Failed to create service account {sa_client_id}: {e}")
        
        logger.info(f"Keycloak auto-setup complete: {len(results['roles_created'])} roles, "
                   f"{len(results['users_created'])} users, "
                   f"{len(results['service_accounts_created'])} service accounts")
        
        return results
        
    except Exception as e:
        logger.error(f"Keycloak auto-setup failed: {e}")
        results["errors"].append(str(e))
        return results


# Global client instance
_keycloak_client: Optional[KeycloakClient] = None


def get_keycloak_client() -> KeycloakClient:
    """Get the global Keycloak client instance."""
    global _keycloak_client
    if _keycloak_client is None:
        _keycloak_client = KeycloakClient()
        _keycloak_client.connect()
    return _keycloak_client


def close_keycloak_client():
    """Close the global Keycloak client."""
    global _keycloak_client
    _keycloak_client = None
