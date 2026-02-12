#!/usr/bin/env python3
"""
Comprehensive Verification Script for Granzion Lab

This script tests all components:
1. Database connections (PostgreSQL, pgvector)
2. LiteLLM connectivity
3. Keycloak health
4. MCP servers and tools
5. Agents initialization
6. API endpoints
"""

import asyncio
import json
import sys
import os

# Ensure correct path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from typing import Dict, Any, List, Tuple


class VerificationReport:
    """Collects verification results."""
    
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
    
    def add(self, category: str, test: str, passed: bool, details: str = ""):
        """Add a test result."""
        self.results.append({
            "category": category,
            "test": test,
            "passed": passed,
            "details": details
        })
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} | {test}: {details if details else 'OK'}")
    
    def summary(self) -> Dict[str, Any]:
        """Generate summary."""
        passed = sum(1 for r in self.results if r["passed"])
        failed = sum(1 for r in self.results if not r["passed"])
        return {
            "total": len(self.results),
            "passed": passed,
            "failed": failed,
            "success_rate": f"{100 * passed / len(self.results):.1f}%" if self.results else "0%",
            "duration": str(datetime.now() - self.start_time)
        }


report = VerificationReport()


# ============================================================================
# 1. DATABASE VERIFICATION
# ============================================================================

async def verify_postgresql():
    """Test PostgreSQL connectivity and schema."""
    print("\n[1/6] PostgreSQL Database")
    print("-" * 40)
    
    try:
        from src.database.connection import check_db_connection
        from src.config import settings
        
        # Test connection (this is a sync function, not async)
        is_connected = check_db_connection()
        report.add("database", "PostgreSQL Connection", is_connected, 
                   f"Host: {settings.postgres_host}")
        
        if is_connected:
            # Check tables exist
            import asyncpg
            conn = await asyncpg.connect(
                host=settings.postgres_host,
                port=settings.postgres_port,
                database=settings.postgres_db,
                user=settings.postgres_user,
                password=settings.postgres_password
            )
            
            # Required tables
            tables = ["identities", "delegations", "audit_logs", "memory_documents", "agent_cards"]
            for table in tables:
                exists = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = $1)",
                    table
                )
                report.add("database", f"Table '{table}'", exists)
            
            # Check identity count
            try:
                count = await conn.fetchval("SELECT COUNT(*) FROM identities")
                report.add("database", "Identity seed data", count > 0, f"{count} identities found")
            except:
                report.add("database", "Identity seed data", False, "Query failed")
            
            await conn.close()
    except Exception as e:
        report.add("database", "PostgreSQL Connection", False, str(e))


async def verify_pgvector():
    """Test pgvector extension."""
    print("\n[2/6] pgvector Extension")
    print("-" * 40)
    
    try:
        from src.database.connection import check_pgvector_extension
        
        # This is a sync function, not async
        has_pgvector = check_pgvector_extension()
        report.add("database", "pgvector Extension", has_pgvector, 
                   "Vector operations available" if has_pgvector else "Not installed")
        
        if has_pgvector:
            # Test vector operations
            import asyncpg
            from src.config import settings
            
            conn = await asyncpg.connect(
                host=settings.postgres_host,
                port=settings.postgres_port,
                database=settings.postgres_db,
                user=settings.postgres_user,
                password=settings.postgres_password
            )
            
            # Check memory_documents table has vector column (embedding)
            has_vector = await conn.fetchval("""
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'memory_documents' AND column_name = 'embedding'
                )
            """)
            report.add("database", "Embeddings vector column", has_vector)
            
            await conn.close()
    except Exception as e:
        report.add("database", "pgvector Extension", False, str(e))


# ============================================================================
# 3. LITELLM VERIFICATION
# ============================================================================

async def verify_litellm():
    """Test LiteLLM connectivity."""
    print("\n[3/6] LiteLLM Connectivity")
    print("-" * 40)
    
    try:
        import httpx
        from src.config import settings
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Model Logic: Use settings.default_model
            # Header Logic: Use x-litellm-api-key for this specific proxy
            headers = {
                "x-litellm-api-key": settings.litellm_api_key,
                "Content-Type": "application/json"
            } if settings.litellm_api_key else {}
            
            # 1. Health check
            health_ok = False
            status_details = ""
            
            # Try standard health endpoints
            for endpoint in ["/health", "/", "/v1/models"]:
                try:
                    resp = await client.get(f"{settings.litellm_url}{endpoint}", headers=headers)
                    if resp.status_code in [200, 404, 401, 403]: # reachable
                        status_details = f"Reachable at {endpoint} ({resp.status_code})"
                        if resp.status_code == 200:
                            health_ok = True
                            break
                except:
                    continue

            # 3. Chat completion (Critical test)
            completion_ok = False
            try:
                # Use a very simple model request
                resp = await client.post(
                    f"{settings.litellm_url}/chat/completions",
                    headers=headers,
                    json={
                        "model": settings.default_model, 
                        "messages": [{"role": "user", "content": "hi"}],
                    }
                )
                
                # If we get a valid response (even 400/401 implies connectivity), it's reachable
                if resp.status_code == 200:
                    completion_ok = True
                    details = f"Model: {settings.default_model}"
                    # If completion works, health is effectively OK for our purpose
                    health_ok = True 
                else:
                    try:
                        error_text = resp.json()
                    except:
                        error_text = resp.text[:100]
                    details = f"Status: {resp.status_code}, Error: {error_text}"
            except Exception as e:
                details = str(e)
            
            report.add("litellm", "Health endpoint", health_ok, status_details if status_details else "Connection Failed")
            report.add("litellm", "Chat completion", completion_ok, details)
                
    except Exception as e:
        report.add("litellm", "Connection", False, str(e))


# ============================================================================
# 3. KEYCLOAK VERIFICATION
# ============================================================================

async def verify_keycloak():
    """Test Keycloak connectivity."""
    print("\n[4/6] Keycloak Identity")
    print("-" * 40)
    
    try:
        import httpx
        from src.config import settings
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Health check - try multiple paths
            try:
                # Keycloak health check paths vary by version and config
                paths = ["/health", "/health/ready", "/realms/master"]
                health_ok = False
                status_code = 0
                
                for path in paths:
                    try:
                        resp = await client.get(f"{settings.keycloak_url}{path}")
                        if resp.status_code in [200, 204]:
                            health_ok = True
                            status_code = resp.status_code
                            break
                        status_code = resp.status_code
                    except:
                        continue
                        
                report.add("keycloak", "Health endpoint", health_ok, f"Status: {status_code}")
            except Exception as e:
                report.add("keycloak", "Health endpoint", False, str(e))
            
            # Realm check
            try:
                resp = await client.get(f"{settings.keycloak_url}/realms/{settings.keycloak_realm}")
                realm_ok = resp.status_code == 200
                report.add("keycloak", f"Realm '{settings.keycloak_realm}'", realm_ok, 
                           "Exists" if realm_ok else "Not found")
            except Exception as e:
                report.add("keycloak", f"Realm check", False, str(e))
                
    except Exception as e:
        report.add("keycloak", "Connection", False, str(e))


# ============================================================================
# 4. MCP SERVERS VERIFICATION
# ============================================================================

# ============================================================================
# 5. PUPPYGRAPH VERIFICATION
# ============================================================================

async def verify_puppygraph():
    """Test PuppyGraph connectivity."""
    print("\n[5/7] PuppyGraph Graph Database")
    print("-" * 40)
    
    try:
        import httpx
        from src.config import settings
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            # 1. Check Web UI (port 8081)
            ui_url = f"http://{settings.puppygraph_host}:{settings.puppygraph_web_port}"
            try:
                resp = await client.get(ui_url)
                ui_ok = resp.status_code < 500
                report.add("puppygraph", "Web UI", ui_ok, f"Status: {resp.status_code}")
            except Exception as e:
                report.add("puppygraph", "Web UI", False, str(e))

            # 2. Check Gremlin Endpoint (port 8182) - via HTTP GET to verify it's listening
            # Note: Real graph queries happen via websocket, but we just check accessibility here
            gremlin_url = f"http://{settings.puppygraph_host}:{settings.puppygraph_port}"
            try:
                # Gremlin server might return 400 or 500 to a GET, but that means it's running
                resp = await client.get(gremlin_url)
                gremlin_ok = True 
                report.add("puppygraph", "Gremlin Endpoint", gremlin_ok, "Port accessible")
            except httpx.ConnectError:
                report.add("puppygraph", "Gremlin Endpoint", False, "Connection refused")
            except Exception:
                # Any other response means port is open
                report.add("puppygraph", "Gremlin Endpoint", True, "Port accessible")

    except Exception as e:
        report.add("puppygraph", "Connection", False, str(e))


# ============================================================================
# 6. MCP SERVERS VERIFICATION
# ============================================================================

def verify_mcp_servers():
    """Test MCP server initialization and tools."""
    print("\n[6/7] MCP Servers & Tools")
    print("-" * 40)
    
    mcp_tests = [
        ("identity_mcp", "IdentityMCPServer", ["get_identity_context", "validate_delegation", "impersonate"]),
        ("comms_mcp", "CommsMCPServer", ["send_message", "receive_message", "broadcast"]),
        ("data_mcp", "DataMCPServer", ["execute_sql", "create_data", "read_data"]),
        ("memory_mcp", "MemoryMCPServer", ["embed_document", "search_similar", "get_context"]),
        ("infra_mcp", "InfraMCPServer", ["deploy_service", "execute_command", "modify_config"]),
        ("agent_card_mcp", "AgentCardMCPServer", ["issue_card", "verify_card", "revoke_card"]),
    ]
    
    for module_name, class_name, expected_tools in mcp_tests:
        try:
            # Dynamic import
            if module_name == "identity_mcp":
                from src.mcps.identity_mcp import IdentityMCPServer
                server = IdentityMCPServer()
            elif module_name == "comms_mcp":
                from src.mcps.comms_mcp import CommsMCPServer
                server = CommsMCPServer()
            elif module_name == "data_mcp":
                from src.mcps.data_mcp import DataMCPServer
                server = DataMCPServer()
            elif module_name == "memory_mcp":
                from src.mcps.memory_mcp import MemoryMCPServer
                server = MemoryMCPServer()
            elif module_name == "infra_mcp":
                from src.mcps.infra_mcp import InfraMCPServer
                server = InfraMCPServer()
            elif module_name == "agent_card_mcp":
                from src.mcps.agent_card_mcp import AgentCardMCPServer
                server = AgentCardMCPServer()
            else:
                continue
            
            # Check server has _tools
            has_tools = hasattr(server, '_tools') and len(server._tools) > 0
            report.add("mcp", f"{class_name} initialized", has_tools, 
                       f"{len(server._tools)} tools" if has_tools else "No tools")
            
            # Check expected tools exist
            if has_tools:
                available = list(server._tools.keys())
                for tool in expected_tools:
                    found = tool in available
                    report.add("mcp", f"  - {tool}", found)
                    
        except Exception as e:
            report.add("mcp", f"{class_name}", False, str(e)[:50])


# ============================================================================
# 7. AGENTS VERIFICATION
# ============================================================================

def verify_agents():
    """Test agent creation and tool wrapping."""
    print("\n[7/7] Agents & Integration")
    print("-" * 40)
    
    try:
        from src.agents import (
            create_orchestrator_agent,
            create_researcher_agent,
            create_executor_agent,
            create_monitor_agent,
            validate_mcp_tools
        )
        
        agents = [
            ("Orchestrator", create_orchestrator_agent),
            ("Researcher", create_researcher_agent),
            ("Executor", create_executor_agent),
            ("Monitor", create_monitor_agent),
        ]
        
        for name, creator in agents:
            try:
                agent = creator()
                has_agent = agent is not None
                tools_count = len(agent.tools) if hasattr(agent, 'tools') else 0
                report.add("agents", f"{name} Agent", has_agent, f"{tools_count} tools")
            except Exception as e:
                report.add("agents", f"{name} Agent", False, str(e)[:50])
        
        # Test validate_mcp_tools helper
        try:
            from src.mcps.comms_mcp import CommsMCPServer
            from src.mcps.identity_mcp import IdentityMCPServer
            
            servers = {
                "comms": CommsMCPServer(),
                "identity": IdentityMCPServer()
            }
            configs = [
                {"server": "comms", "tool": "send_message"},
                {"server": "identity", "tool": "get_identity_context"},
            ]
            result = validate_mcp_tools(servers, configs)
            report.add("agents", "validate_mcp_tools helper", result["valid"], 
                       f"Available: {list(result['available_tools'].keys())}")
        except Exception as e:
            report.add("agents", "validate_mcp_tools helper", False, str(e))
            
    except Exception as e:
        report.add("agents", "Agent imports", False, str(e))


# ============================================================================
# 8. API ENDPOINTS (if server running)
# ============================================================================

async def verify_api_endpoints():
    """Test API endpoints if server is running."""
    print("\n[Bonus] API Endpoints (if running)")
    print("-" * 40)
    
    try:
        import httpx
        from src.config import settings
        
        base_url = f"http://localhost:{settings.api_port}"
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            endpoints = [
                ("/health", "Health"),
                ("/services", "Services"),
                ("/agents", "Agents"),
                ("/scenarios", "Scenarios"),
                ("/threat-map", "Threat Map"),
                ("/a2a/agents/00000000-0000-0000-0000-000000000101/.well-known/agent-card.json", "A2A Discovery"),
            ]
            
            for path, name in endpoints:
                try:
                    resp = await client.get(f"{base_url}{path}")
                    ok = resp.status_code == 200
                    report.add("api", f"{name} endpoint", ok, 
                               f"Status: {resp.status_code}")
                except httpx.ConnectError:
                    report.add("api", f"{name} endpoint", False, "Server not running")
                    break
                except Exception as e:
                    report.add("api", f"{name} endpoint", False, str(e)[:30])
                    
    except Exception as e:
        report.add("api", "API check", False, str(e))


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run all verification tests."""
    print("=" * 60)
    print("  GRANZION LAB - COMPREHENSIVE VERIFICATION")
    print("=" * 60)
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Run all tests
    await verify_postgresql()
    await verify_pgvector()
    await verify_litellm()
    await verify_keycloak()
    await verify_puppygraph()
    verify_mcp_servers()
    verify_agents()
    await verify_api_endpoints()
    
    # Print summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    summary = report.summary()
    print(f"  Total Tests: {summary['total']}")
    print(f"  Passed: {summary['passed']}")
    print(f"  Failed: {summary['failed']}")
    print(f"  Success Rate: {summary['success_rate']}")
    print(f"  Duration: {summary['duration']}")
    print("=" * 60)
    
    # Detailed failures
    failures = [r for r in report.results if not r["passed"]]
    if failures:
        print("\nFAILED TESTS:")
        for f in failures:
            print(f"  - [{f['category']}] {f['test']}: {f['details']}")
    
    # Return exit code
    return 0 if summary['failed'] == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
