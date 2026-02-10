"""
Main entry point for Granzion Lab application.
Initializes all services and starts the application.
"""

import asyncio
import nest_asyncio
nest_asyncio.apply()
import sys
from loguru import logger
from uuid import UUID
from fastapi import FastAPI, Header, Request, Depends
from fastapi.responses import JSONResponse

from src.config import settings
from src.mcps.comms_mcp import CommsMCPServer
from src.mcps.identity_mcp import IdentityMCPServer
from src.mcps.agent_card_mcp import get_agent_card_mcp_server


# Global state for service status
_services_status = {}
_agents_initialized = False
_agents = {}

# Session-scoped pending A2A for orchestrator follow-up prompts (session_id -> last send_message info)
_pending_a2a_by_session: dict = {}


def setup_logging():
    """Configure logging with loguru."""
    logger.remove()  # Remove default handler
    
    # Console logging
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True,
    )
    
    # File logging
    logger.add(
        "logs/granzion-lab.log",
        rotation="500 MB",
        retention="10 days",
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )
    
    logger.info(f"Logging configured with level: {settings.log_level}")


async def check_services():
    """Check that all required services are available."""
    logger.info("Checking service availability...")
    
    import httpx
    from src.database.connection import check_db_connection, check_pgvector_extension
    
    services_status = {}
    all_healthy = True
    
    # Check PostgreSQL
    logger.info("Checking PostgreSQL...")
    try:
        if check_db_connection():
            services_status["postgres"] = "healthy"
            logger.info("✓ PostgreSQL is healthy")
            
            # Check pgvector extension
            if check_pgvector_extension():
                services_status["pgvector"] = "healthy"
                logger.info("✓ pgvector extension is installed")
            else:
                services_status["pgvector"] = "missing"
                logger.warning("⚠ pgvector extension not installed")
        else:
            services_status["postgres"] = "unhealthy"
            all_healthy = False
            logger.error("✗ PostgreSQL connection failed")
    except Exception as e:
        services_status["postgres"] = f"error: {e}"
        all_healthy = False
        logger.error(f"✗ PostgreSQL check failed: {e}")
    
    # Check Keycloak
    logger.info("Checking Keycloak...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try multiple paths for health check
            paths = ["/health/ready", "/health"]
            # Fallback to checking master realm
            paths.append("/realms/master")
            
            keycloak_healthy = False
            last_status = 0
            
            for path in paths:
                try:
                    resp = await client.get(f"{settings.keycloak_url}{path}")
                    if resp.status_code in [200, 204]:
                        keycloak_healthy = True
                        break
                    last_status = resp.status_code
                except:
                    continue
                    
            if keycloak_healthy:
                services_status["keycloak"] = "healthy"
                logger.info("✓ Keycloak is healthy")
            else:
                services_status["keycloak"] = f"unhealthy (status: {last_status})"
                logger.warning(f"⚠ Keycloak returned status {last_status}")
    except httpx.ConnectError:
        services_status["keycloak"] = "not_ready (still starting)"
        logger.warning("⚠ Keycloak not ready yet (may still be starting)")
    except Exception as e:
        services_status["keycloak"] = f"error: {e}"
        logger.warning(f"⚠ Keycloak check failed: {e}")
    
    # Check LiteLLM
    logger.info("Checking LiteLLM...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Use x-litellm-api-key header for this specific proxy
            headers = {"x-litellm-api-key": settings.litellm_api_key}
            
            # Try /health, then root /
            try:
                resp = await client.get(f"{settings.litellm_url}/health", headers=headers)
                if resp.status_code == 404:
                    resp = await client.get(f"{settings.litellm_url}/", headers=headers)
            except:
                # If /health fails connection, try root
                resp = await client.get(f"{settings.litellm_url}/", headers=headers)

            if resp.status_code == 200:
                services_status["litellm"] = "healthy"
                logger.info("✓ LiteLLM is healthy")
            else:
                services_status["litellm"] = f"unhealthy (status: {resp.status_code})"
                logger.warning(f"⚠ LiteLLM returned status {resp.status_code}")
    except httpx.ConnectError:
        services_status["litellm"] = "not_reachable"
        logger.warning("⚠ LiteLLM not reachable (check LITELLM_URL)")
    except Exception as e:
        services_status["litellm"] = f"error: {e}"
        logger.warning(f"⚠ LiteLLM check failed: {e}")
    
    # Check PuppyGraph (optional). Official image: Web UI 8081, Gremlin 8182.
    logger.info("Checking PuppyGraph...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            puppygraph_ok = False
            for port in (settings.puppygraph_web_port, 8081):
                try:
                    resp = await client.get(f"http://{settings.puppygraph_host}:{port}")
                    if resp.status_code == 200:
                        services_status["puppygraph"] = "healthy"
                        logger.info("✓ PuppyGraph is healthy")
                        puppygraph_ok = True
                        break
                except Exception:
                    continue
            if not puppygraph_ok:
                services_status["puppygraph"] = "not_reachable"
                logger.warning("⚠ PuppyGraph not reachable (tried %s, 8081). See docs/TROUBLESHOOTING.md", settings.puppygraph_web_port)
    except Exception as e:
        services_status["puppygraph"] = "not_reachable"
        logger.warning(f"⚠ PuppyGraph not reachable: {e}")
    
    # Initialize MCP servers
    comms_mcp = CommsMCPServer()
    identity_mcp = IdentityMCPServer()
    agent_card_mcp = get_agent_card_mcp_server()
    
    # Store in global status
    _services_status["mcp_agent_card"] = "healthy"
    
    if all_healthy:
        logger.info("All critical services are available")
    else:
        logger.warning("Some services are not healthy, but continuing startup")
    
    return services_status


async def initialize_database():
    """Initialize database schema and extensions."""
    logger.info("Initializing database...")
    
    from src.database.connection import sync_engine, check_db_connection
    from sqlalchemy import text
    
    # Check connection first
    if not check_db_connection():
        logger.error("Cannot initialize database - connection failed")
        raise Exception("Database connection failed")
    
    # Verify tables exist (created by SQL init scripts)
    try:
        with sync_engine.connect() as conn:
            # Check if identities table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'identities'
                )
            """))
            if result.scalar():
                logger.info("✓ Database tables already exist")
                
                # Count records
                result = conn.execute(text("SELECT COUNT(*) FROM identities"))
                count = result.scalar()
                logger.info(f"  Found {count} identities in database")
            else:
                logger.warning("Database tables not found - run init_database.sh")
    except Exception as e:
        logger.error(f"Database verification failed: {e}")
        raise
    
    logger.info("Database initialized successfully")


async def initialize_keycloak():
    """Initialize Keycloak realm and clients."""
    global _services_status
    logger.info("Initializing Keycloak...")
    
    import httpx
    
    # Check if Keycloak is accessible
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{settings.keycloak_url}/realms/{settings.keycloak_realm}")
            if resp.status_code == 200:
                logger.info(f"[OK] Keycloak realm '{settings.keycloak_realm}' exists")
                _services_status["keycloak_realm"] = "exists"
            elif resp.status_code == 404:
                logger.warning(f"Keycloak realm '{settings.keycloak_realm}' not found, attempting auto-setup...")
                
                # Try auto-setup
                try:
                    from src.identity.keycloak_client import auto_setup_keycloak
                    result = auto_setup_keycloak(skip_if_exists=True)
                    
                    if result.get("errors"):
                        logger.warning(f"Auto-setup had errors: {result['errors']}")
                        _services_status["keycloak_realm"] = "errors"
                    else:
                        logger.info(f"[OK] Auto-setup complete: realm created")
                        _services_status["keycloak_realm"] = "created"
                except Exception as setup_err:
                    logger.error(f"Auto-setup failed: {setup_err}")
                    _services_status["keycloak_realm"] = "failed"
            else:
                logger.warning(f"Keycloak realm check returned {resp.status_code}")
                _services_status["keycloak_realm"] = "unknown"
    except httpx.ConnectError:
        logger.warning("Keycloak not ready - agents will use mock identity")
        _services_status["keycloak_realm"] = "unavailable"
    except Exception as e:
        logger.warning(f"Keycloak initialization skipped: {e}")
        _services_status["keycloak_realm"] = "skipped"
    
    logger.info("Keycloak initialization complete")


async def initialize_puppygraph():
    """Initialize PuppyGraph schema."""
    logger.info("Initializing PuppyGraph...")
    
    import httpx
    
    # Check if PuppyGraph is accessible
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"http://{settings.puppygraph_host}:{settings.puppygraph_web_port}")
            if resp.status_code == 200:
                logger.info("✓ PuppyGraph web UI is accessible")
            else:
                logger.warning(f"⚠ PuppyGraph returned status {resp.status_code}")
    except Exception as e:
        logger.warning(f"⚠ PuppyGraph not accessible: {e}")
        logger.warning("  Graph queries will use fallback SQL queries")
    
    logger.info("PuppyGraph initialization complete")


async def initialize_agents():
    """Initialize Agno agents."""
    global _agents_initialized
    logger.info("Initializing agents...")
    
    from src.agents import (
        create_orchestrator_agent,
        create_researcher_agent,
        create_executor_agent,
        create_monitor_agent,
    )
    
    try:
        # Create all agents
        orchestrator = create_orchestrator_agent()
        researcher = create_researcher_agent()
        executor = create_executor_agent()
        monitor = create_monitor_agent()
        
        # Store for API access
        _agents["orchestrator"] = orchestrator
        _agents["researcher"] = researcher
        _agents["executor"] = executor
        _agents["monitor"] = monitor
        
        # Register for Active A2A Triggering
        from src.mcps.comms_mcp import CommsMCPServer
        for agent in _agents.values():
            if hasattr(agent, 'agent_id'):
                CommsMCPServer.register_agent_instance(agent.agent_id, agent)
        
        logger.info("✓ Orchestrator Agent initialized")
        logger.info("✓ Researcher Agent initialized")
        logger.info("✓ Executor Agent initialized")
        logger.info("✓ Monitor Agent initialized")
        
        _agents_initialized = True
        logger.info("All agents initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize agents: {e}")
        _agents_initialized = False
        raise


async def start_api_server():
    """Start the FastAPI server."""
    logger.info(f"Starting API server on port {settings.api_port}...")
    
    from fastapi import FastAPI, Header, Request
    from fastapi.responses import JSONResponse
    from typing import Optional
    import uvicorn
    
    app = FastAPI(title="Granzion Lab API", version="1.0.0")
    
    @app.get("/health")
    async def health():
        """Health check endpoint with real service status. Populates services if not yet set."""
        global _services_status, _agents_initialized
        if not _services_status or "postgres" not in _services_status:
            try:
                _services_status.update(await check_services())
            except Exception as e:
                logger.warning(f"Could not refresh service status: {e}")
        critical_services = ["postgres"]
        all_critical_healthy = all(
            _services_status.get(svc) == "healthy"
            for svc in critical_services
        )
        return JSONResponse({
            "status": "healthy" if all_critical_healthy else "degraded",
            "service": "granzion-lab-api",
            "version": "1.0.0",
            "agents_initialized": _agents_initialized,
            "services": _services_status
        })

    @app.get("/health/identity")
    async def health_identity():
        """
        Identity-specific health: Keycloak reachable, realm exists, and optionally token obtainable.
        Returns degraded with message if token cannot be obtained (e.g. seeded user missing).
        """
        global _services_status
        keycloak_status = _services_status.get("keycloak", "unknown")
        realm_status = _services_status.get("keycloak_realm", "unknown")
        keycloak_reachable = keycloak_status == "healthy"
        realm_exists = realm_status in ("exists", "created")
        token_obtainable = None
        message = None

        if keycloak_reachable and realm_exists:
            try:
                from src.identity.keycloak_client import get_keycloak_client
                kc = get_keycloak_client()
                kc.get_token("alice", "password123")
                token_obtainable = True
            except Exception as e:
                token_obtainable = False
                message = f"Token obtainable: failed ({e!s})"

        identity_healthy = keycloak_reachable and realm_exists and (token_obtainable is not False)
        return JSONResponse({
            "status": "healthy" if identity_healthy else "degraded",
            "identity": {
                "keycloak_reachable": keycloak_reachable,
                "realm_exists": realm_exists,
                "token_obtainable": token_obtainable,
            },
            "message": message,
        })

    @app.get("/a2a/agents/{identity_id}/.well-known/agent-card.json")
    async def get_agent_card(identity_id: str):
        """Fetch the A2A Agent Card for a specific agent."""
        from src.database.connection import get_db
        from src.database.models import AgentCard, Identity
        from uuid import UUID

        def _ensure_list(val):
            if val is None:
                return []
            return list(val) if not isinstance(val, list) else val

        try:
            agent_uuid = UUID(identity_id)
            with get_db() as db:
                card = db.query(AgentCard).filter(AgentCard.agent_id == agent_uuid).first()
                if not card:
                    agent = db.query(Identity).filter(Identity.id == agent_uuid).first()
                    if not agent:
                        return JSONResponse({"error": "Agent not found"}, status_code=404)
                    return JSONResponse({
                        "id": str(agent_uuid),
                        "name": agent.name or "Unknown",
                        "version": "0.3.0",
                        "capabilities": _ensure_list(agent.permissions),
                        "is_verified": False,
                    })
                name = getattr(card.agent, "name", None) if card.agent else None
                return JSONResponse({
                    "id": str(card.agent_id),
                    "name": name or "Unknown Agent",
                    "version": card.version or "0.3.0",
                    "capabilities": _ensure_list(card.capabilities),
                    "public_key": card.public_key,
                    "issuer_id": str(card.issuer_id) if card.issuer_id else None,
                    "is_verified": bool(card.is_verified),
                    "metadata": dict(card.card_metadata) if card.card_metadata else {},
                })
        except ValueError as e:
            return JSONResponse({"error": f"Invalid agent id: {e}"}, status_code=400)
        except Exception as e:
            logger.exception("A2A agent-card fetch failed")
            return JSONResponse({"error": str(e)}, status_code=500)

    @app.get("/")
    async def root():
        """Root endpoint."""
        return JSONResponse({
            "message": "Granzion Lab API",
            "version": "1.0.0",
            "endpoints": {
                "health": "/health",
                "health_identity": "/health/identity",
                "docs": "/docs",
                "agents": "/agents",
                "scenarios": "/scenarios",
                "evidence": "/evidence",
                "events": "/events",
                "services": "/services"
            }
        })
    
    @app.get("/services")
    async def list_services():
        """List all service statuses. Populates from check_services() if not yet set (e.g. when app started via uvicorn)."""
        global _services_status
        if not _services_status or "postgres" not in _services_status:
            try:
                _services_status.update(await check_services())
            except Exception as e:
                logger.warning(f"Could not refresh service status: {e}")
        return JSONResponse({
            "services": _services_status
        })
    
    @app.post("/agents/{agent_id}/run")
    async def run_agent(
        agent_id: str,
        request: dict,
        authorization: Optional[str] = Header(None),
        x_orchestration_mode: Optional[str] = Header(None, alias="X-Orchestration-Mode"),
    ):
        """
        Run an agent with a specific prompt.
        Supports Identity-First security via OIDC tokens or manual context.
        """
        global _agents
        from src.identity.context import IdentityContext
        from src.identity.keycloak_client import get_keycloak_client
        from src.agents import (
            create_orchestrator_agent,
            create_researcher_agent,
            create_executor_agent,
            create_monitor_agent,
        )
        
        # 1. Resolve Identity Context
        identity_context = None
        
        # Check Authorization Header (Bearer Token)
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]
            try:
                kc = get_keycloak_client()
                identity_context = IdentityContext.from_token(token, kc)
                logger.info(f"Using identity from token for {agent_id}: {identity_context.user_id}")
            except Exception as e:
                logger.warning(f"Failed to parse token: {e}")
        
        # Fallback to manual context in body (Red Team/Testing mode)
        if not identity_context and "identity_context" in request:
            try:
                identity_context = IdentityContext.from_dict(request["identity_context"])
                logger.info(f"Using manual identity context for {agent_id}")
                
                # Ensure this manual identity exists in the database to prevent foreign key errors
                from src.database.queries import create_identity, get_identity_by_id
                from src.database.connection import get_db
                
                with get_db() as db:
                    # Map common frontend IDs to names
                    mock_names = {
                        "00000000-0000-0000-0000-000000000001": "Alice (User)",
                        "00000000-0000-0000-0000-000000000002": "Bob (Admin)",
                        "00000000-0000-0000-0000-000000000003": "Charlie (Restricted)"
                    }
                    user_id_str = str(identity_context.user_id)
                    
                    if not get_identity_by_id(db, identity_context.user_id):
                        logger.warning(f"Registering missing manual user: {identity_context.user_id}")
                        create_identity(
                            db, 
                            identity_type="user", 
                            name=mock_names.get(user_id_str, "ManualUser"),
                            identity_id=identity_context.user_id
                        )
            except Exception as e:
                logger.warning(f"Failed to parse manual identity context: {e}")

        # Fallback to Guest/Anonymous context if still no identity (Zero Context Mode)
        if not identity_context:
            logger.info(f"Using GUEST identity context for {agent_id}")
            
            # Use a stable UUID for the Guest user
            GUEST_USER_ID = UUID("00000000-0000-0000-0000-000000000999")
            
            identity_context = IdentityContext(
                user_id=GUEST_USER_ID,
                agent_id=None,
                delegation_chain=[GUEST_USER_ID],
                permissions={"read:core"},  # Guest has minimal read permissions
                trust_level=10
            )
            
            # Ensure guest user exists in DB
            from src.database.queries import create_identity, get_identity_by_id
            from src.database.connection import get_db
            with get_db() as db:
                if not get_identity_by_id(db, GUEST_USER_ID):
                    logger.info("Initializing persistent Guest User identity")
                    create_identity(
                        db,
                        identity_type="user",
                        name="Guest User",
                        identity_id=GUEST_USER_ID
                    )

        # So the invoked agent knows its own identity (e.g. "I am the Orchestrator")
        if identity_context and identity_context.agent_id is None:
            try:
                agent_uuid = UUID(agent_id)
                identity_context = identity_context.extend_delegation_chain(
                    agent_uuid, identity_context.permissions
                )
                logger.debug(f"Set run context agent_id={agent_id} for this request")
            except (ValueError, TypeError):
                pass

        # 2. Resolve Agent Instance
        target_agent = None
        agent_key = agent_id.lower()
        
        # Map IDs to creators
        creators = {
            "orchestrator": create_orchestrator_agent,
            "researcher": create_researcher_agent,
            "executor": create_executor_agent,
            "monitor": create_monitor_agent,
            "00000000-0000-0000-0000-000000000101": create_orchestrator_agent,
            "00000000-0000-0000-0000-000000000102": create_researcher_agent,
            "00000000-0000-0000-0000-000000000103": create_executor_agent,
            "00000000-0000-0000-0000-000000000104": create_monitor_agent,
        }
        
        if identity_context:
            # If we have a context, we create a fresh, context-aware agent instance
            # for THIS specific request to ensure Zero Trust enforcement.
            if agent_key in creators:
                creator = creators[agent_key]
                target_agent = creator(identity_context=identity_context)
                
                # Register this specific context-aware instance for Active A2A
                if hasattr(target_agent, 'agent_id'):
                    from src.mcps.comms_mcp import CommsMCPServer
                    CommsMCPServer.register_agent_instance(target_agent.agent_id, target_agent)
            else:
                # Fallback to checking by UUID
                for uuid, creator in creators.items():
                    if uuid == agent_id:
                        target_agent = creator(identity_context=identity_context)
                        
                        # Register this specific context-aware instance for Active A2A
                        if hasattr(target_agent, 'agent_id'):
                            from src.mcps.comms_mcp import CommsMCPServer
                            CommsMCPServer.register_agent_instance(target_agent.agent_id, target_agent)
                        break
        else:
            # No context provided, use default global unauthenticated instances
            if agent_key in _agents:
                target_agent = _agents[agent_key]
            else:
                for a in _agents.values():
                    if hasattr(a, 'agent_id') and str(a.agent_id) == agent_id:
                        target_agent = a
                        break
        
        if not target_agent:
            return JSONResponse({"error": f"Agent {agent_id} not found or not initialized"}, status_code=404)
        
        prompt = request.get("prompt")
        if not prompt:
            return JSONResponse({"error": "No prompt provided"}, status_code=400)

        session_id = request.get("session_id") or request.get("session")
        if session_id is not None:
            session_id = str(session_id)

        # Inject pending A2A hint for orchestrator follow-ups (e.g. "What did they say?")
        if session_id and agent_key in ("orchestrator", "00000000-0000-0000-0000-000000000101"):
            pending = _pending_a2a_by_session.pop(session_id, None)
            if pending and pending.get("to_agent_id"):
                hint = (
                    "You recently sent a message to an agent (to_agent_id={}). "
                    "Check your mailbox with receive_message(agent_id=00000000-0000-0000-0000-000000000101) to get the reply. "
                    "Then answer the user.\n\nUser request: "
                ).format(pending["to_agent_id"])
                prompt = hint + prompt

        # Optional deterministic orchestration path for demos (orchestrator only)
        use_deterministic = (
            x_orchestration_mode and x_orchestration_mode.strip().lower() == "deterministic"
        ) or (request.get("orchestration_mode") == "deterministic")
        if use_deterministic and agent_key in ("orchestrator", "00000000-0000-0000-0000-000000000101"):
            try:
                from src.agents.orchestration_router import run_deterministic_flow
                from src.identity.context import identity_context_var
                token = identity_context_var.set(identity_context)
                try:
                    content, ok = await run_deterministic_flow(prompt, identity_context)
                finally:
                    identity_context_var.reset(token)
                return {
                    "agent_id": agent_id,
                    "response": content,
                    "status": "success" if ok else "degraded",
                    "identity": identity_context.to_dict() if identity_context else None,
                    "orchestration_mode": "deterministic",
                }
            except Exception as e:
                logger.error(f"Deterministic orchestration failed: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)

        try:
            # Use arun() instead of run() because MCP tools are async
            from src.identity.context import identity_context_var, pending_a2a_var
            token = identity_context_var.set(identity_context)
            try:
                response = await target_agent.arun(prompt)
            finally:
                identity_context_var.reset(token)

            # Persist pending A2A for next request (orchestrator follow-up)
            if session_id and agent_key in ("orchestrator", "00000000-0000-0000-0000-000000000101"):
                try:
                    pending = pending_a2a_var.get()
                    if pending:
                        _pending_a2a_by_session[session_id] = pending
                        pending_a2a_var.set(None)
                except Exception:
                    pass

            content = response.content if hasattr(response, 'content') else str(response)

            return {
                "agent_id": agent_id,
                "response": content,
                "status": "success",
                "identity": identity_context.to_dict() if identity_context else None
            }
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            return JSONResponse({"error": str(e)}, status_code=500)

    # Canonical agent UUIDs (seed / available agents only) - frontend shows only these
    AVAILABLE_AGENT_IDS = [
        "00000000-0000-0000-0000-000000000101",  # Orchestrator
        "00000000-0000-0000-0000-000000000102",  # Researcher
        "00000000-0000-0000-0000-000000000103",  # Executor
        "00000000-0000-0000-0000-000000000104",  # Monitor
    ]

    @app.get("/agents")
    async def list_agents():
        """List only available (canonical) agents for the frontend."""
        from src.database.connection import get_db
        from sqlalchemy import text

        try:
            from sqlalchemy import bindparam
            with get_db() as db:
                stmt = text("""
                    SELECT id, name, type, permissions
                    FROM identities
                    WHERE type = 'agent' AND id::text IN :ids
                    ORDER BY name
                """).bindparams(bindparam("ids", expanding=True))
                result = db.execute(stmt, {"ids": AVAILABLE_AGENT_IDS})
                agents = []
                for row in result:
                    agents.append({
                        "id": str(row.id),
                        "name": row.name,
                        "type": row.type,
                        "permissions": row.permissions or [],
                        "status": "active"
                    })
                # Sort by canonical order so Orchestrator, Researcher, Executor, Monitor
                id_order = {aid: i for i, aid in enumerate(AVAILABLE_AGENT_IDS)}
                agents.sort(key=lambda a: id_order.get(a["id"], 99))

                if not agents:
                    agents = [
                        {"id": "00000000-0000-0000-0000-000000000101", "name": "Orchestrator Agent", "type": "agent", "permissions": ["delegate", "coordinate", "read"], "status": "active"},
                        {"id": "00000000-0000-0000-0000-000000000102", "name": "Researcher Agent", "type": "agent", "permissions": ["read", "embed", "search"], "status": "active"},
                        {"id": "00000000-0000-0000-0000-000000000103", "name": "Executor Agent", "type": "agent", "permissions": ["read", "write", "execute", "deploy"], "status": "active"},
                        {"id": "00000000-0000-0000-0000-000000000104", "name": "Monitor Agent", "type": "agent", "permissions": ["read", "monitor"], "status": "active"},
                    ]
                return JSONResponse({"agents": agents})
        except Exception as e:
            logger.error(f"Failed to fetch agents: {e}")
            return JSONResponse({
                "agents": [],
                "error": str(e)
            }, status_code=500)
    
    @app.get("/scenarios")
    async def list_scenarios():
        """List all scenarios from scenarios folder."""
        import os
        import re
        
        scenarios = []
        scenarios_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scenarios")
        
        try:
            if os.path.exists(scenarios_dir):
                for filename in sorted(os.listdir(scenarios_dir)):
                    if filename.startswith("s") and filename.endswith(".py"):
                        # Extract ID and name from filename like s01_identity_confusion.py
                        match = re.match(r"(s\d+)_(.+)\.py", filename)
                        if match:
                            scenario_id = match.group(1)
                            scenario_name = match.group(2).replace("_", " ").title()
                            scenarios.append({
                                "id": scenario_id,
                                "name": scenario_name,
                                "file": filename
                            })
            
            if not scenarios:
                # Fallback if no scenarios found
                scenarios = [
                    {"id": "s01", "name": "Identity Confusion"},
                    {"id": "s02", "name": "Memory Poisoning"},
                    {"id": "s03", "name": "A2A Message Forgery"},
                    {"id": "s04", "name": "Tool Parameter Injection"},
                    {"id": "s05", "name": "Workflow Hijacking"}
                ]
                
            return JSONResponse({
                "scenarios": scenarios,
                "count": len(scenarios)
            })
        except Exception as e:
            logger.error(f"Failed to list scenarios: {e}")
            return JSONResponse({
                "scenarios": [],
                "error": str(e)
            }, status_code=500)

    @app.get("/logs")
    async def get_logs(lines: int = 50):
        """Read system logs."""
        import os
        log_file = "logs/granzion-lab.log"
        if not os.path.exists(log_file):
            return {"logs": ["Log file not found."]}
        
        try:
            with open(log_file, "r") as f:
                content = f.readlines()
                return {"logs": [line.strip() for line in content[-lines:]]}
        except Exception as e:
            return {"error": str(e)}

    @app.get("/events")
    async def get_events():
        """Get recent A2A events from REAL system traffic."""
        from src.database.connection import get_db
        from src.database.models import Message, AuditLog, Identity
        from sqlalchemy import select, desc
        from datetime import datetime
        
        events = []
        
        try:
            with get_db() as db:
                # 1. Fetch real A2A Messages
                stmt = select(Message, Identity.name).join(
                    Identity, Message.from_agent_id == Identity.id
                ).order_by(desc(Message.timestamp)).limit(10)
                
                messages = db.execute(stmt).all()
                for msg, source_name in messages:
                    events.append({
                        "timestamp": msg.timestamp.strftime("%H:%M:%S"),
                        "type": "A2A",
                        "source": source_name,
                        "message": f"sent message: {msg.content[:50]}..."
                    })
                
                # 2. Fetch real Audit Logs
                stmt = select(AuditLog, Identity.name).join(
                    Identity, AuditLog.identity_id == Identity.id
                ).order_by(desc(AuditLog.timestamp)).limit(10)
                
                logs = db.execute(stmt).all()
                for log, source_name in logs:
                    events.append({
                        "timestamp": log.timestamp.strftime("%H:%M:%S"),
                        "type": log.action.upper(),
                        "source": source_name,
                        "message": f"{log.resource_type or 'System'}: {log.details.get('tool_name', '') if log.details else ''} info recorded."
                    })

                # Sort combined events by timestamp
                events.sort(key=lambda x: x["timestamp"], reverse=True)
                events = events[:20]

            # Fallback for empty lab
            if not events:
                now = datetime.now().strftime("%H:%M:%S")
                events.append({
                    "timestamp": now,
                    "type": "SYSTEM",
                    "source": "Lab Manager",
                    "message": "Waiting for live A2A traffic via scenarios or console..."
                })
                
            return {"events": events}
        except Exception as e:
            logger.error(f"Event fetch failed: {e}")
            return {"events": [], "error": str(e)}

    @app.get("/evidence")
    async def get_evidence(limit: int = 100):
        """Get red team evidence (audit logs) in evidence-schema shape for the UI."""
        from src.database.connection import get_db
        from src.database.queries import get_audit_logs
        from src.database.models import Identity

        try:
            with get_db() as db:
                logs = get_audit_logs(db, limit=min(limit, 500))
                evidence = []
                for log in logs:
                    identity_name = None
                    if log.identity_id:
                        ident = db.query(Identity).filter(Identity.id == log.identity_id).first()
                        identity_name = ident.name if ident else str(log.identity_id)
                    details = log.details or {}
                    resource = (log.resource_type or "") + (f":{log.resource_id}" if log.resource_id else "")
                    evidence.append({
                        "id": str(log.id),
                        "actor": {
                            "user_id": details.get("user_id"),
                            "agent_id": details.get("agent_id") or (str(log.identity_id) if log.identity_id else None),
                            "identity_name": identity_name,
                        },
                        "action": log.action,
                        "resource": resource or details.get("resource_id"),
                        "timestamp": log.timestamp.isoformat() + "Z" if log.timestamp else None,
                        "identity_context": {
                            "user_id": details.get("user_id"),
                            "agent_id": details.get("agent_id"),
                            "delegation_depth": details.get("delegation_depth"),
                        },
                        "details": details,
                    })
            return {"evidence": evidence, "count": len(evidence)}
        except Exception as e:
            logger.error(f"Evidence fetch failed: {e}")
            return JSONResponse({"evidence": [], "error": str(e)}, status_code=500)

    @app.post("/scenarios/{scenario_id}/run")
    async def run_scenario(scenario_id: str):
        """Execute a scenario via the scenario engine and return full result."""
        import re
        scenario_id = scenario_id.lower().strip()
        if not re.match(r"^s\d+$", scenario_id):
            return JSONResponse({"error": "Invalid scenario ID format (use s01, s02, ...)"}, status_code=400)
        try:
            from src.scenarios.discovery import discover_scenarios
            from src.scenarios.engine import ScenarioEngine
            scenarios = discover_scenarios()
            scenario_obj = next((s for s in scenarios if s.id.lower() == scenario_id), None)
            if not scenario_obj:
                return JSONResponse({"error": f"Scenario {scenario_id} not found"}, status_code=404)
            logger.info(f"Running scenario via engine: {scenario_obj.name}")
            engine = ScenarioEngine()
            # Run in thread pool so we don't block the event loop
            result = await asyncio.to_thread(engine.execute_scenario, scenario_obj)
            # Serialize evidence (may contain dict or str)
            evidence_out = []
            for e in (result.evidence or []):
                evidence_out.append(e if isinstance(e, str) else str(e))
            payload = {
                "scenario_id": result.scenario_id,
                "status": "completed",
                "success": result.success,
                "message": f"Scenario {result.scenario_id} {'passed' if result.success else 'failed'}.",
                "duration_seconds": result.duration_seconds,
                "steps_succeeded": result.steps_succeeded,
                "steps_failed": result.steps_failed,
                "steps_executed": result.steps_executed,
                "steps": result.step_results,  # Added detailed steps
                "criteria_passed": result.criteria_passed,
                "criteria_failed": result.criteria_failed,
                "criteria_checked": result.criteria_checked,
                "evidence": evidence_out,
                "state_before": result.initial_state,  # Added initial state
                "state_after": result.final_state,    # Added final state
                "errors": getattr(result, "errors", []) or [],
            }
            return JSONResponse(payload)
        except Exception as e:
            logger.exception(f"Scenario run failed: {e}")
            return JSONResponse({
                "scenario_id": scenario_id,
                "status": "error",
                "success": False,
                "message": f"Execution failed: {e}",
                "error": str(e),
            }, status_code=500)

    @app.post("/agents/{agent_id}/rotate-key")
    async def rotate_key(agent_id: str):
        """Simulate rotation of an agent's public key."""
        from src.database.connection import get_db
        from src.database.models import AgentCard
        from uuid import UUID
        import secrets
        import base64
        
        try:
            agent_uuid = UUID(agent_id)
            new_key = f"ed25519_{base64.b64encode(secrets.token_bytes(32)).decode('utf-8')[:44]}"
            
            with get_db() as db:
                card = db.query(AgentCard).filter(AgentCard.agent_id == agent_uuid).first()
                if not card:
                    return JSONResponse({"error": "Agent Card not found for rotation"}, status_code=404)
                
                card.public_key = new_key
                db.commit()
                
                logger.info(f"Key rotated for agent {agent_id}: {new_key[:10]}...")
                
                return {
                    "agent_id": agent_id,
                    "new_public_key": new_key,
                    "status": "success"
                }
        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
            return JSONResponse({"error": str(e)}, status_code=500)

    # Run server in background
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=settings.api_port,
        log_level="info"
    )
    server = uvicorn.Server(config)
    
    # Start server as background task
    asyncio.create_task(server.serve())
    
    logger.info(f"API server running at http://localhost:{settings.api_port}")


async def start_tui():
    """Start the Terminal UI."""
    logger.info(f"Starting TUI on port {settings.tui_port}...")
    
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    import uvicorn
    
    app = FastAPI(title="Granzion Lab TUI", version="1.0.0")
    
    @app.get("/", response_class=HTMLResponse)
    async def root():
        """TUI root endpoint."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Granzion Lab - Terminal UI</title>
            <style>
                body {
                    background-color: #1e1e1e;
                    color: #00ff00;
                    font-family: 'Courier New', monospace;
                    padding: 20px;
                    margin: 0;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                }
                h1 {
                    color: #00ff00;
                    border-bottom: 2px solid #00ff00;
                    padding-bottom: 10px;
                }
                .section {
                    margin: 20px 0;
                    padding: 15px;
                    border: 1px solid #00ff00;
                    border-radius: 5px;
                }
                .status {
                    color: #00ff00;
                }
                .agent {
                    margin: 10px 0;
                    padding: 10px;
                    background-color: #2a2a2a;
                    border-left: 3px solid #00ff00;
                }
                .scenario {
                    margin: 5px 0;
                    padding: 8px;
                    background-color: #2a2a2a;
                }
                a {
                    color: #00aaff;
                    text-decoration: none;
                }
                a:hover {
                    text-decoration: underline;
                }
                .command {
                    background-color: #2a2a2a;
                    padding: 10px;
                    border-radius: 3px;
                    margin: 10px 0;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎯 Granzion Lab - Agentic AI Red-Teaming Lab</h1>
                
                <div class="section">
                    <h2>System Status</h2>
                    <div class="status">✅ All systems operational</div>
                    <div class="status">✅ 4 Agents active</div>
                    <div class="status">✅ 5 MCP Servers (25 tools)</div>
                    <div class="status">✅ Database healthy</div>
                </div>
                
                <div class="section">
                    <h2>Active Agents</h2>
                    <div class="agent">
                        <strong>Orchestrator</strong> (00000000-0000-0000-0000-000000000101)<br>
                        Status: Active | Role: Coordination
                    </div>
                    <div class="agent">
                        <strong>Researcher</strong> (00000000-0000-0000-0000-000000000102)<br>
                        Status: Active | Role: Analysis
                    </div>
                    <div class="agent">
                        <strong>Executor</strong> (00000000-0000-0000-0000-000000000103)<br>
                        Status: Active | Role: Execution
                    </div>
                    <div class="agent">
                        <strong>Monitor</strong> (00000000-0000-0000-0000-000000000104)<br>
                        Status: Active | Role: Monitoring
                    </div>
                </div>
                
                <div class="section">
                    <h2>Available Scenarios (15)</h2>
                    <div class="scenario">S01: Identity Confusion</div>
                    <div class="scenario">S02: Memory Poisoning</div>
                    <div class="scenario">S03: A2A Message Forgery</div>
                    <div class="scenario">S04: Tool Parameter Injection</div>
                    <div class="scenario">S05: Workflow Hijacking</div>
                    <div class="scenario">S06: Context Window Stuffing</div>
                    <div class="scenario">S07: Jailbreaking LiteLLM</div>
                    <div class="scenario">S08: Unauthorized Infrastructure</div>
                    <div class="scenario">S09: Audit Log Manipulation</div>
                    <div class="scenario">S10: Cross Agent Memory</div>
                    <div class="scenario">S11: Goal Manipulation</div>
                    <div class="scenario">S12: Credential Theft</div>
                    <div class="scenario">S13: Privilege Escalation Infra</div>
                    <div class="scenario">S14: Container Escape</div>
                    <div class="scenario">S15: Detection Evasion</div>
                </div>
                
                <div class="section">
                    <h2>Quick Links</h2>
                    <p><a href="http://localhost:8001">API Documentation</a></p>
                    <p><a href="http://localhost:8001/docs">API Swagger UI</a></p>
                    <p><a href="http://localhost:8080">Keycloak Admin</a></p>
                    <p><a href="http://localhost:8081">PuppyGraph UI</a></p>
                </div>
                
                <div class="section">
                    <h2>Quick Commands</h2>
                    <div class="command">
                        # Verify MCP tools<br>
                        python test_mcp_tools.py
                    </div>
                    <div class="command">
                        # Check logs<br>
                        docker logs granzion-lab-app --tail 50
                    </div>
                    <div class="command">
                        # Access database<br>
                        docker exec -it granzion-postgres psql -U granzion -d granzion_lab
                    </div>
                </div>
                
                <div class="section">
                    <p style="text-align: center; color: #888;">
                        Granzion Lab v1.0.0 | Ready for Red Team Testing
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    
    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return JSONResponse({
            "status": "healthy",
            "service": "granzion-lab-tui",
            "version": "1.0.0"
        })
    
    # Run server in background
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=settings.tui_port,
        log_level="info"
    )
    server = uvicorn.Server(config)
    
    # Start server as background task
    asyncio.create_task(server.serve())
    
    logger.info(f"TUI running at http://localhost:{settings.tui_port}")


async def main():
    """Main application entry point."""
    setup_logging()
    
    logger.info("=" * 80)
    logger.info("Granzion Agentic AI Red-Teaming Lab")
    logger.info("=" * 80)
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info("")
    
    try:
        # Check service availability and persist for /health and /services
        global _services_status
        _services_status.update(await check_services())
        
        # Initialize components
        await initialize_database()
        await initialize_keycloak()
        await initialize_puppygraph()
        await initialize_agents()
        
        # Start servers
        await asyncio.gather(
            start_api_server(),
            start_tui(),
        )
        
        logger.info("Granzion Lab is ready!")
        logger.info(f"Access the TUI at: http://localhost:{settings.tui_port}")
        logger.info(f"Access the API at: http://localhost:{settings.api_port}")
        logger.info(f"Access Keycloak at: {settings.keycloak_url}")
        logger.info(f"Access PuppyGraph UI at: {settings.puppygraph_web_url}")
        
        # Keep running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
