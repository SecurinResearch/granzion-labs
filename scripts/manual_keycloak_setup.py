
import asyncio
import httpx
import os
import sys
import json
from loguru import logger

# Configuration
KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", "http://keycloak:8080")
ADMIN_USER = os.environ.get("KEYCLOAK_ADMIN", "admin")
ADMIN_PASS = os.environ.get("KEYCLOAK_ADMIN_PASSWORD", "admin_changeme")
REALM_NAME = os.environ.get("KEYCLOAK_REALM", "granzion-lab")

async def setup_keycloak():
  async with httpx.AsyncClient(timeout=10.0) as client:
    print(f"Connecting to {KEYCLOAK_URL} as {ADMIN_USER}")
    
    # 1. Get Admin Token
    try:
        resp = await client.post(
            f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
            data={
                "username": ADMIN_USER,
                "password": ADMIN_PASS,
                "grant_type": "password",
                "client_id": "admin-cli"
            }
        )
        if resp.status_code != 200:
            print(f"Failed to get admin token: {resp.status_code} {resp.text}")
            return False
            
        token = resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        print("Got admin token")
        
    except Exception as e:
        print(f"Error connecting to Keycloak: {e}")
        return False

    # 2. Check if realm exists
    try:
        resp = await client.get(f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}", headers=headers)
        if resp.status_code == 200:
            print(f"Realm {REALM_NAME} already exists")
            return True
    except Exception as e:
        print(f"Error checking realm: {e}")

    # 3. Create Realm
    try:
        realm_payload = {
            "realm": REALM_NAME,
            "enabled": True,
            "displayName": f"Granzion Lab - {REALM_NAME}",
            "registrationAllowed": False,
            "loginWithEmailAllowed": True
        }
        resp = await client.post(
            f"{KEYCLOAK_URL}/admin/realms",
            headers=headers,
            json=realm_payload
        )
        if resp.status_code == 201:
            print(f"Realm {REALM_NAME} created successfully")
            return True
        else:
            print(f"Failed to create realm: {resp.status_code} {resp.text}")
            return False
    except Exception as e:
        print(f"Error creating realm: {e}")
        return False

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(setup_keycloak())
