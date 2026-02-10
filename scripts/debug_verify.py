
import asyncio
import httpx
import os
import sys

# Load env manually or use simple values since we know them
LITELLM_URL = "https://llmproxy.securin.io"
LITELLM_API_KEY = "sk-qHmJE6p1q4GDbYFCrwhNkA"
KEYCLOAK_URL = "http://keycloak:8080"
KEYCLOAK_REALM = "granzion-lab"

async def check_litellm():
    print(f"Checking LiteLLM: {LITELLM_URL}")
    async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
        headers = {"x-litellm-api-key": LITELLM_API_KEY}
        
        # Check /health
        try:
            resp = await client.get(f"{LITELLM_URL}/health", headers=headers)
            print(f"/health status: {resp.status_code}")
            print(f"/health content: {resp.text[:200]}")
        except Exception as e:
            print(f"/health failed: {e}")

        # Check /
        try:
            resp = await client.get(f"{LITELLM_URL}/", headers=headers)
            print(f"/ status: {resp.status_code}")
        except Exception as e:
            print(f"/ failed: {e}")
            
        # Check /models
        try:
            resp = await client.get(f"{LITELLM_URL}/models", headers=headers)
            print(f"/models status: {resp.status_code}")
        except Exception as e:
            print(f"/models failed: {e}")

async def check_keycloak():
    print(f"Checking Keycloak: {KEYCLOAK_URL}")
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Check health
        try:
            resp = await client.get(f"{KEYCLOAK_URL}/health")
            print(f"/health status: {resp.status_code}")
        except Exception as e:
            print(f"/health failed: {e}")
            
        # Check realm
        try:
            resp = await client.get(f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}")
            print(f"Realm {KEYCLOAK_REALM} status: {resp.status_code}")
            if resp.status_code != 200:
                print(f"Realm response: {resp.text[:500]}")
        except Exception as e:
            print(f"Realm check failed: {e}")

        # List realms (if possible with public access, likely not, but try master)
        try:
            resp = await client.get(f"{KEYCLOAK_URL}/realms/master")
            print(f"Realm master status: {resp.status_code}")
        except Exception as e:
            print(f"Realm master check failed: {e}")

async def main():
    await check_litellm()
    await check_keycloak()

if __name__ == "__main__":
    asyncio.run(main())
