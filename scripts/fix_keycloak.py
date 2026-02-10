
import sys
import os
from pathlib import Path

# Add project root to python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.identity.keycloak_client import auto_setup_keycloak
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")

def main():
    print("Starting Keycloak Fix...")
    try:
        # Run auto-setup
        results = auto_setup_keycloak(skip_if_exists=True)
        
        print("\n--- Setup Results ---")
        print(f"Realm Created: {results.get('realm_created')}")
        print(f"Roles Created: {len(results.get('roles_created', []))}")
        print(f"Users Created: {len(results.get('users_created', []))}")
        print(f"Service Accounts: {len(results.get('service_accounts_created', []))}")
        
        if results.get('errors'):
            print("\n!!! ERRORS !!!")
            for error in results['errors']:
                print(f"- {error}")
            sys.exit(1)
            
        print("\n✅ Keycloak setup completed successfully.")
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
