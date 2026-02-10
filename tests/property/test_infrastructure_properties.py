"""
Property-based tests for infrastructure attacks.

Feature: granzion-lab-simplified
Property 19: Infrastructure compromise observability
"""

import pytest
import os
from hypothesis import given, strategies as st, settings, assume
from uuid import UUID, uuid4
from datetime import datetime

from src.database.connection import get_db
from src.database.queries import (
    create_identity,
    create_audit_log,
    get_audit_logs_by_identity,
)
from src.identity.context import IdentityContext


# Feature: granzion-lab-simplified, Property 19: Infrastructure compromise observability
@given(
    agent_name=st.text(min_size=1, max_size=50),
    config_key=st.text(min_size=1, max_size=50),
    original_value=st.text(min_size=1, max_size=100),
    malicious_value=st.text(min_size=1, max_size=100),
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_infrastructure_config_tampering_observability(
    agent_name,
    config_key,
    original_value,
    malicious_value
):
    """
    Property 19: Infrastructure compromise observability (config tampering)
    
    For any infrastructure attack (config tampering, env var manipulation,
    deployment changes), the system should show the specific impact on
    agent behavior, including which agents were affected and how their
    behavior changed.
    
    Validates: Requirements 17.4
    """
    # Ensure values are different
    assume(original_value != malicious_value)
    
    with get_db() as db:
        # Create agent
        agent = create_identity(
            db,
            identity_type="agent",
            name=agent_name,
            permissions=["read", "write", "execute", "infra:modify"]
        )
        
        # Create identity context
        context = IdentityContext(
            user_id=uuid4(),
            agent_id=agent.id,
            delegation_chain=[uuid4(), agent.id],
            permissions=set(agent.permissions),
            keycloak_token="mock_token",
            trust_level=80
        )
        
        # Log original configuration state
        original_state_log = create_audit_log(
            db,
            identity_id=agent.id,
            action="read_config",
            resource_type="config",
            resource_id=None,
            details={
                "config_key": config_key,
                "config_value": original_value,
                "state": "original",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Agent performs config tampering attack
        attack_log = create_audit_log(
            db,
            identity_id=agent.id,
            action="modify_config",
            resource_type="config",
            resource_id=None,
            details={
                "config_key": config_key,
                "old_value": original_value,
                "new_value": malicious_value,
                "attack_type": "config_tampering",
                "vulnerability": "IF-02",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Log agent behavior change due to config tampering
        behavior_change_log = create_audit_log(
            db,
            identity_id=agent.id,
            action="behavior_change",
            resource_type="agent_behavior",
            resource_id=agent.id,
            details={
                "affected_agent_id": str(agent.id),
                "affected_agent_name": agent.name,
                "cause": "config_tampering",
                "config_key": config_key,
                "behavior_before": f"Using config: {original_value}",
                "behavior_after": f"Using config: {malicious_value}",
                "impact": "Agent behavior modified by malicious config",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Verify: Original state is observable
        assert original_state_log.details["config_value"] == original_value
        assert original_state_log.details["state"] == "original"
        
        # Verify: Attack is logged with before/after values
        assert attack_log.details["attack_type"] == "config_tampering"
        assert attack_log.details["old_value"] == original_value
        assert attack_log.details["new_value"] == malicious_value
        assert attack_log.details["vulnerability"] == "IF-02"
        
        # Verify: Behavior change is observable
        assert behavior_change_log.details["affected_agent_id"] == str(agent.id)
        assert behavior_change_log.details["cause"] == "config_tampering"
        assert original_value in behavior_change_log.details["behavior_before"]
        assert malicious_value in behavior_change_log.details["behavior_after"]
        
        # Verify: Can identify which agent was affected
        logs = get_audit_logs_by_identity(db, agent.id)
        assert len(logs) >= 3
        
        # Find the behavior change log
        behavior_log = next(
            (log for log in logs if log.action == "behavior_change"),
            None
        )
        assert behavior_log is not None
        assert behavior_log.details["affected_agent_name"] == agent.name
        
        # Verify: Can see the specific impact
        assert "impact" in behavior_log.details
        assert behavior_log.details["impact"] == "Agent behavior modified by malicious config"


# Feature: granzion-lab-simplified, Property 19: Infrastructure compromise observability (env vars)
@given(
    agent_name=st.text(min_size=1, max_size=50),
    env_var_name=st.text(min_size=1, max_size=50),
    original_env_value=st.text(min_size=1, max_size=100),
    malicious_env_value=st.text(min_size=1, max_size=100),
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_infrastructure_env_manipulation_observability(
    agent_name,
    env_var_name,
    original_env_value,
    malicious_env_value
):
    """
    Property 19: Infrastructure compromise observability (env var manipulation)
    
    For environment variable manipulation attacks, the system should show
    which agents were affected and how their behavior changed.
    
    Validates: Requirements 17.4
    """
    # Ensure values are different
    assume(original_env_value != malicious_env_value)
    # Ensure env var name is valid
    assume(env_var_name.replace("_", "").replace("-", "").isalnum())
    
    with get_db() as db:
        # Create agent
        agent = create_identity(
            db,
            identity_type="agent",
            name=agent_name,
            permissions=["read", "write", "execute", "infra:env"]
        )
        
        # Create identity context
        context = IdentityContext(
            user_id=uuid4(),
            agent_id=agent.id,
            delegation_chain=[uuid4(), agent.id],
            permissions=set(agent.permissions),
            keycloak_token="mock_token",
            trust_level=80
        )
        
        # Log original environment state
        original_state_log = create_audit_log(
            db,
            identity_id=agent.id,
            action="read_env",
            resource_type="environment",
            resource_id=None,
            details={
                "env_var_name": env_var_name,
                "env_var_value": original_env_value,
                "state": "original",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Agent performs environment variable manipulation
        attack_log = create_audit_log(
            db,
            identity_id=agent.id,
            action="write_env",
            resource_type="environment",
            resource_id=None,
            details={
                "env_var_name": env_var_name,
                "old_value": original_env_value,
                "new_value": malicious_env_value,
                "attack_type": "env_manipulation",
                "vulnerability": "IF-03",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Log agent behavior change due to env manipulation
        behavior_change_log = create_audit_log(
            db,
            identity_id=agent.id,
            action="behavior_change",
            resource_type="agent_behavior",
            resource_id=agent.id,
            details={
                "affected_agent_id": str(agent.id),
                "affected_agent_name": agent.name,
                "cause": "env_manipulation",
                "env_var_name": env_var_name,
                "behavior_before": f"Using env: {original_env_value}",
                "behavior_after": f"Using env: {malicious_env_value}",
                "impact": "Agent behavior modified by malicious environment variable",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Verify: Original state is observable
        assert original_state_log.details["env_var_value"] == original_env_value
        assert original_state_log.details["state"] == "original"
        
        # Verify: Attack is logged with before/after values
        assert attack_log.details["attack_type"] == "env_manipulation"
        assert attack_log.details["old_value"] == original_env_value
        assert attack_log.details["new_value"] == malicious_env_value
        assert attack_log.details["vulnerability"] == "IF-03"
        
        # Verify: Behavior change is observable
        assert behavior_change_log.details["affected_agent_id"] == str(agent.id)
        assert behavior_change_log.details["cause"] == "env_manipulation"
        assert original_env_value in behavior_change_log.details["behavior_before"]
        assert malicious_env_value in behavior_change_log.details["behavior_after"]
        
        # Verify: Can identify which agent was affected
        logs = get_audit_logs_by_identity(db, agent.id)
        assert len(logs) >= 3
        
        # Find the behavior change log
        behavior_log = next(
            (log for log in logs if log.action == "behavior_change"),
            None
        )
        assert behavior_log is not None
        assert behavior_log.details["affected_agent_name"] == agent.name


# Feature: granzion-lab-simplified, Property 19: Infrastructure compromise observability (deployment)
@given(
    agent_name=st.text(min_size=1, max_size=50),
    service_name=st.text(min_size=1, max_size=50),
    malicious_image=st.text(min_size=1, max_size=100),
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_infrastructure_deployment_manipulation_observability(
    agent_name,
    service_name,
    malicious_image
):
    """
    Property 19: Infrastructure compromise observability (deployment manipulation)
    
    For deployment manipulation attacks, the system should show which
    services were deployed and how they affect agent behavior.
    
    Validates: Requirements 17.4
    """
    with get_db() as db:
        # Create agent
        agent = create_identity(
            db,
            identity_type="agent",
            name=agent_name,
            permissions=["read", "write", "execute", "infra:deploy"]
        )
        
        # Create identity context
        context = IdentityContext(
            user_id=uuid4(),
            agent_id=agent.id,
            delegation_chain=[uuid4(), agent.id],
            permissions=set(agent.permissions),
            keycloak_token="mock_token",
            trust_level=80
        )
        
        # Agent deploys malicious service
        deployment_id = str(uuid4())
        attack_log = create_audit_log(
            db,
            identity_id=agent.id,
            action="deploy_service",
            resource_type="deployment",
            resource_id=UUID(deployment_id),
            details={
                "deployment_id": deployment_id,
                "service_name": service_name,
                "image": malicious_image,
                "attack_type": "malicious_deployment",
                "vulnerability": "IF-02",
                "config": {
                    "privileged": True,
                    "network_mode": "host"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Log impact on agent behavior
        behavior_change_log = create_audit_log(
            db,
            identity_id=agent.id,
            action="behavior_change",
            resource_type="agent_behavior",
            resource_id=agent.id,
            details={
                "affected_agent_id": str(agent.id),
                "affected_agent_name": agent.name,
                "cause": "malicious_deployment",
                "deployment_id": deployment_id,
                "service_name": service_name,
                "behavior_before": "Normal operation",
                "behavior_after": f"Communicating with malicious service: {service_name}",
                "impact": "Agent now uses compromised service",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Verify: Deployment is logged
        assert attack_log.details["attack_type"] == "malicious_deployment"
        assert attack_log.details["service_name"] == service_name
        assert attack_log.details["image"] == malicious_image
        assert attack_log.details["vulnerability"] == "IF-02"
        
        # Verify: Behavior change is observable
        assert behavior_change_log.details["affected_agent_id"] == str(agent.id)
        assert behavior_change_log.details["cause"] == "malicious_deployment"
        assert behavior_change_log.details["service_name"] == service_name
        assert service_name in behavior_change_log.details["behavior_after"]
        
        # Verify: Can identify which agent was affected
        logs = get_audit_logs_by_identity(db, agent.id)
        assert len(logs) >= 2
        
        # Find the behavior change log
        behavior_log = next(
            (log for log in logs if log.action == "behavior_change"),
            None
        )
        assert behavior_log is not None
        assert behavior_log.details["affected_agent_name"] == agent.name
        
        # Verify: Can see the specific impact
        assert "impact" in behavior_log.details
        assert "compromised service" in behavior_log.details["impact"]


# Additional property test for command execution impact
@given(
    agent_name=st.text(min_size=1, max_size=50),
    command=st.text(min_size=1, max_size=100),
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_infrastructure_command_execution_observability(
    agent_name,
    command
):
    """
    Property 19 (variant): Infrastructure compromise observability (command execution)
    
    For command execution attacks, the system should show which commands
    were executed and their impact on the system.
    
    Validates: Requirements 17.4
    """
    with get_db() as db:
        # Create agent
        agent = create_identity(
            db,
            identity_type="agent",
            name=agent_name,
            permissions=["read", "write", "execute", "infra:execute"]
        )
        
        # Create identity context
        context = IdentityContext(
            user_id=uuid4(),
            agent_id=agent.id,
            delegation_chain=[uuid4(), agent.id],
            permissions=set(agent.permissions),
            keycloak_token="mock_token",
            trust_level=80
        )
        
        # Agent executes command
        attack_log = create_audit_log(
            db,
            identity_id=agent.id,
            action="execute_command",
            resource_type="command",
            resource_id=None,
            details={
                "command": command,
                "attack_type": "command_injection",
                "vulnerability": "IF-02",
                "exit_code": 0,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Log system state change
        state_change_log = create_audit_log(
            db,
            identity_id=agent.id,
            action="system_state_change",
            resource_type="system",
            resource_id=None,
            details={
                "cause": "command_execution",
                "command": command,
                "executed_by": str(agent.id),
                "impact": f"System modified by command: {command}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Verify: Command execution is logged
        assert attack_log.details["attack_type"] == "command_injection"
        assert attack_log.details["command"] == command
        assert attack_log.details["vulnerability"] == "IF-02"
        
        # Verify: System state change is observable
        assert state_change_log.details["cause"] == "command_execution"
        assert state_change_log.details["command"] == command
        assert state_change_log.details["executed_by"] == str(agent.id)
        
        # Verify: Can identify the impact
        assert "impact" in state_change_log.details
        assert command in state_change_log.details["impact"]
        
        # Verify: Logs are retrievable
        logs = get_audit_logs_by_identity(db, agent.id)
        assert len(logs) >= 2
        
        # Find the command execution log
        cmd_log = next(
            (log for log in logs if log.action == "execute_command"),
            None
        )
        assert cmd_log is not None
        assert cmd_log.details["command"] == command
