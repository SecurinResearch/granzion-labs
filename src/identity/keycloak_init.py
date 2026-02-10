"""
Keycloak initialization for Granzion Lab.
Sets up realm, clients, roles, and initial identities.
"""

from loguru import logger

from src.config import settings
from src.identity.keycloak_client import get_keycloak_client
from src.database.connection import get_db
from src.database.queries import get_identities_by_type, get_identity_by_keycloak_id


def initialize_keycloak():
    """
    Initialize Keycloak with realm, clients, roles, and identities.
    
    This function:
    1. Creates the Granzion Lab realm
    2. Creates clients for the lab application
    3. Creates service accounts for agents
    4. Creates roles for permissions
    5. Syncs identities from database to Keycloak
    """
    logger.info("Initializing Keycloak...")
    
    try:
        kc = get_keycloak_client()
        
        # Step 1: Create realm
        logger.info(f"Creating realm: {settings.keycloak_realm}")
        kc.create_realm(settings.keycloak_realm)
        
        # Step 2: Create main application client
        logger.info("Creating main application client...")
        kc.create_client(
            client_id=settings.keycloak_client_id,
            client_name="Granzion Lab Application",
            service_account_enabled=False,
            public_client=False
        )
        
        # Step 3: Create roles for permissions
        logger.info("Creating permission roles...")
        permissions = [
            ("read", "Read permission"),
            ("write", "Write permission"),
            ("execute", "Execute permission"),
            ("admin", "Admin permission"),
            ("delete", "Delete permission"),
            ("delegate", "Delegate permission"),
            ("coordinate", "Coordinate permission"),
            ("embed", "Embed permission"),
            ("search", "Search permission"),
            ("deploy", "Deploy permission"),
            ("monitor", "Monitor permission"),
            ("identity", "Identity management permission"),
            ("delegation", "Delegation management permission"),
            ("memory", "Memory management permission"),
            ("vector", "Vector operations permission"),
            ("data", "Data operations permission"),
            ("sql", "SQL execution permission"),
            ("communication", "Communication permission"),
            ("messaging", "Messaging permission"),
            ("infrastructure", "Infrastructure permission"),
            ("deployment", "Deployment permission"),
        ]
        
        for role_name, description in permissions:
            kc.create_role(role_name, description)
        
        # Step 4: Create service accounts for agents
        logger.info("Creating service accounts for agents...")
        
        agent_service_accounts = [
            ("sa-orchestrator", "Orchestrator Agent Service Account"),
            ("sa-researcher", "Researcher Agent Service Account"),
            ("sa-executor", "Executor Agent Service Account"),
            ("sa-monitor", "Monitor Agent Service Account"),
        ]
        
        for client_id, client_name in agent_service_accounts:
            try:
                sa_info = kc.create_service_account(client_id, client_name)
                logger.info(f"Created service account: {client_id}")
                logger.debug(f"  Client UUID: {sa_info['client_uuid']}")
                logger.debug(f"  Service Account User: {sa_info['service_account_username']}")
            except Exception as e:
                logger.warning(f"Service account {client_id} may already exist: {e}")
        
        # Step 5: Create service accounts for MCPs
        logger.info("Creating service accounts for MCP servers...")
        
        mcp_service_accounts = [
            ("svc-identity-mcp", "Identity MCP Service Account"),
            ("svc-memory-mcp", "Memory MCP Service Account"),
            ("svc-data-mcp", "Data MCP Service Account"),
            ("svc-comms-mcp", "Comms MCP Service Account"),
            ("svc-infra-mcp", "Infra MCP Service Account"),
        ]
        
        for client_id, client_name in mcp_service_accounts:
            try:
                sa_info = kc.create_service_account(client_id, client_name)
                logger.info(f"Created service account: {client_id}")
            except Exception as e:
                logger.warning(f"Service account {client_id} may already exist: {e}")
        
        # Step 6: Sync users from database to Keycloak
        logger.info("Syncing users from database to Keycloak...")
        sync_users_to_keycloak()
        
        logger.info("Keycloak initialization complete!")
        
    except Exception as e:
        logger.error(f"Failed to initialize Keycloak: {e}")
        raise


def sync_users_to_keycloak():
    """
    Sync user identities from database to Keycloak.
    
    Creates Keycloak users for all user identities in the database
    that don't already exist in Keycloak.
    """
    kc = get_keycloak_client()
    
    with get_db() as db:
        # Get all user identities from database
        users = get_identities_by_type(db, "user")
        
        for user in users:
            # Check if user already exists in Keycloak
            if user.keycloak_id:
                kc_user = kc.get_user_by_username(user.keycloak_id)
                if kc_user:
                    logger.debug(f"User {user.name} already exists in Keycloak")
                    continue
            
            # Create user in Keycloak
            try:
                # Use a default password for lab users
                default_password = "password123"  # Intentionally weak for lab
                
                user_uuid = kc.create_user(
                    username=user.keycloak_id or user.name.lower().replace(" ", "_"),
                    email=user.email or f"{user.name.lower().replace(' ', '_')}@granzion-lab.local",
                    first_name=user.name.split()[0] if " " in user.name else user.name,
                    last_name=user.name.split()[-1] if " " in user.name else "User",
                    password=default_password,
                    enabled=True
                )
                
                # Assign roles based on permissions
                for permission in user.permissions:
                    try:
                        kc.assign_role_to_user(user_uuid, permission)
                    except Exception as e:
                        logger.warning(f"Failed to assign role {permission} to user {user.name}: {e}")
                
                logger.info(f"Synced user to Keycloak: {user.name}")
                
            except Exception as e:
                logger.error(f"Failed to sync user {user.name} to Keycloak: {e}")


def create_test_users():
    """
    Create additional test users in Keycloak for scenarios.
    
    These users are used in attack scenarios and testing.
    """
    kc = get_keycloak_client()
    
    test_users = [
        {
            "username": "alice",
            "email": "[email protected]",
            "first_name": "Alice",
            "last_name": "Anderson",
            "password": "alice123",
            "roles": ["read", "write"]
        },
        {
            "username": "bob",
            "email": "[email protected]",
            "first_name": "Bob",
            "last_name": "Brown",
            "password": "bob123",
            "roles": ["admin", "read", "write", "delete"]
        },
        {
            "username": "charlie",
            "email": "[email protected]",
            "first_name": "Charlie",
            "last_name": "Chen",
            "password": "charlie123",
            "roles": ["read"]
        },
    ]
    
    for user_data in test_users:
        try:
            # Check if user exists
            existing_user = kc.get_user_by_username(user_data["username"])
            if existing_user:
                logger.debug(f"Test user {user_data['username']} already exists")
                continue
            
            # Create user
            user_uuid = kc.create_user(
                username=user_data["username"],
                email=user_data["email"],
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                password=user_data["password"],
                enabled=True
            )
            
            # Assign roles
            for role in user_data["roles"]:
                kc.assign_role_to_user(user_uuid, role)
            
            logger.info(f"Created test user: {user_data['username']}")
            
        except Exception as e:
            logger.error(f"Failed to create test user {user_data['username']}: {e}")


def verify_keycloak_setup():
    """
    Verify that Keycloak is properly set up.
    
    Returns:
        bool: True if setup is valid, False otherwise
    """
    try:
        kc = get_keycloak_client()
        
        # Check realm exists
        realm = kc.get_realm(settings.keycloak_realm)
        if not realm:
            logger.error(f"Realm {settings.keycloak_realm} does not exist")
            return False
        
        # Check main client exists
        client_uuid = kc.get_client_id(settings.keycloak_client_id)
        if not client_uuid:
            logger.error(f"Client {settings.keycloak_client_id} does not exist")
            return False
        
        # Check service accounts exist
        for sa_id in ["sa-orchestrator", "sa-researcher", "sa-executor", "sa-monitor"]:
            sa_uuid = kc.get_client_id(sa_id)
            if not sa_uuid:
                logger.warning(f"Service account {sa_id} does not exist")
        
        logger.info("Keycloak setup verification passed")
        return True
        
    except Exception as e:
        logger.error(f"Keycloak setup verification failed: {e}")
        return False


if __name__ == "__main__":
    # Run initialization
    initialize_keycloak()
    create_test_users()
    verify_keycloak_setup()
