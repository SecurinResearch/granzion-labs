"""
Execution tests for all attack scenarios (S01-S16).

These tests verify that each scenario can be executed successfully and that
success criteria are met. Also validates threat ID consistency with the taxonomy.
"""

import re
import pytest
from loguru import logger

from src.scenarios.discovery import discover_scenarios
from src.scenarios.engine import ScenarioEngine

# Taxonomy uses numeric IDs 1-54; scenarios may also use legacy codes (e.g. IT-01, M-02).
VALID_TAXONOMY_RANGE = (1, 54)
LEGACY_THREAT_ID_PATTERN = re.compile(r"^[A-Z]{1,3}-\d{2}$")


@pytest.fixture
def scenario_engine():
    """Create a scenario engine for testing."""
    return ScenarioEngine()


@pytest.fixture
def all_scenarios():
    """Discover all scenarios as a dict keyed by scenario id (e.g. S01, S17)."""
    scenarios = discover_scenarios()
    return {s.id: s for s in scenarios}


# Tests for scenarios S01-S05

def test_s01_identity_confusion_execution(scenario_engine, all_scenarios):
    """Test that S01 (Identity Confusion) executes successfully."""
    scenario = all_scenarios.get("S01")
    assert scenario is not None, "Scenario S01 not found"
    
    logger.info(f"Executing scenario: {scenario.name}")
    result = scenario_engine.execute_scenario(scenario)
    
    # Verify execution completed
    assert result is not None, "Scenario execution returned None"
    assert result.success, f"Scenario failed: {'; '.join(result.errors) if result.errors else 'Unknown'}"
    
    # Verify all steps completed
    assert len(result.step_results) == len(scenario.attack_steps)
    for step_result in result.step_results:
        assert step_result.get("status") == "completed", f"Step failed: {step_result.get('description', '')}"
    
    # Verify success criteria met
    assert len(result.criterion_results) == len(scenario.success_criteria)
    for criterion_result in result.criterion_results:
        assert criterion_result.get("passed", False), f"Criterion not met: {criterion_result.get('description', '')}"


def test_s02_memory_poisoning_execution(scenario_engine, all_scenarios):
    """Test that S02 (Memory Poisoning) executes successfully."""
    scenario = all_scenarios.get("S02")
    assert scenario is not None, "Scenario S02 not found"
    
    logger.info(f"Executing scenario: {scenario.name}")
    result = scenario_engine.execute_scenario(scenario)
    
    assert result is not None
    assert result.success, f"Scenario failed: {'; '.join(result.errors) if result.errors else 'Unknown'}"
    
    # Verify all steps completed
    for step_result in result.step_results:
        assert step_result.get("status") == "completed", f"Step failed: {step_result.get('description', '')}"
    
    # Verify success criteria met
    for criterion_result in result.criterion_results:
        assert criterion_result.get("passed", False), f"Criterion not met: {criterion_result.get('description', '')}"


def test_s03_a2a_message_forgery_execution(scenario_engine, all_scenarios):
    """Test that S03 (A2A Message Forgery) executes successfully."""
    scenario = all_scenarios.get("S03")
    assert scenario is not None, "Scenario S03 not found"
    
    logger.info(f"Executing scenario: {scenario.name}")
    result = scenario_engine.execute_scenario(scenario)
    
    assert result is not None
    assert result.success, f"Scenario failed: {'; '.join(result.errors) if result.errors else 'Unknown'}"
    
    # Verify all steps completed
    for step_result in result.step_results:
        assert step_result.get("status") == "completed", f"Step failed: {step_result.get('description', '')}"
    
    # Verify success criteria met
    for criterion_result in result.criterion_results:
        assert criterion_result.get("passed", False), f"Criterion not met: {criterion_result.get('description', '')}"


def test_s04_tool_parameter_injection_execution(scenario_engine, all_scenarios):
    """Test that S04 (Tool Parameter Injection) executes successfully."""
    scenario = all_scenarios.get("S04")
    assert scenario is not None, "Scenario S04 not found"
    
    logger.info(f"Executing scenario: {scenario.name}")
    result = scenario_engine.execute_scenario(scenario)
    
    assert result is not None
    assert result.success, f"Scenario failed: {'; '.join(result.errors) if result.errors else 'Unknown'}"
    
    # Verify all steps completed
    for step_result in result.step_results:
        assert step_result.get("status") == "completed", f"Step failed: {step_result.get('description', '')}"
    
    # Verify success criteria met
    for criterion_result in result.criterion_results:
        assert criterion_result.get("passed", False), f"Criterion not met: {criterion_result.get('description', '')}"


def test_s05_workflow_hijacking_execution(scenario_engine, all_scenarios):
    """Test that S05 (Workflow Hijacking) executes successfully."""
    scenario = all_scenarios.get("S05")
    assert scenario is not None, "Scenario S05 not found"
    
    logger.info(f"Executing scenario: {scenario.name}")
    result = scenario_engine.execute_scenario(scenario)
    
    assert result is not None
    assert result.success, f"Scenario failed: {'; '.join(result.errors) if result.errors else 'Unknown'}"
    
    # Verify all steps completed
    for step_result in result.step_results:
        assert step_result.get("status") == "completed", f"Step failed: {step_result.get('description', '')}"
    
    # Verify success criteria met
    for criterion_result in result.criterion_results:
        assert criterion_result.get("passed", False), f"Criterion not met: {criterion_result.get('description', '')}"


# Tests for scenarios S06-S10

def test_s06_context_window_stuffing_execution(scenario_engine, all_scenarios):
    """Test that S06 (Context Window Stuffing) executes successfully."""
    scenario = all_scenarios.get("S06")
    assert scenario is not None, "Scenario S06 not found"
    
    logger.info(f"Executing scenario: {scenario.name}")
    result = scenario_engine.execute_scenario(scenario)
    
    assert result is not None
    assert result.success, f"Scenario failed: {'; '.join(result.errors) if result.errors else 'Unknown'}"
    
    for step_result in result.step_results:
        assert step_result.get("status") == "completed", f"Step failed: {step_result.get('description', '')}"
    
    for criterion_result in result.criterion_results:
        assert criterion_result.get("passed", False), f"Criterion not met: {criterion_result.get('description', '')}"


def test_s07_jailbreaking_litellm_execution(scenario_engine, all_scenarios):
    """Test that S07 (Jailbreaking via LiteLLM) executes successfully."""
    scenario = all_scenarios.get("S07")
    assert scenario is not None, "Scenario S07 not found"
    
    logger.info(f"Executing scenario: {scenario.name}")
    result = scenario_engine.execute_scenario(scenario)
    
    assert result is not None
    assert result.success, f"Scenario failed: {'; '.join(result.errors) if result.errors else 'Unknown'}"
    
    for step_result in result.step_results:
        assert step_result.get("status") == "completed", f"Step failed: {step_result.get('description', '')}"
    
    for criterion_result in result.criterion_results:
        assert criterion_result.get("passed", False), f"Criterion not met: {criterion_result.get('description', '')}"


def test_s08_unauthorized_infrastructure_execution(scenario_engine, all_scenarios):
    """Test that S08 (Unauthorized Infrastructure Actions) executes successfully."""
    scenario = all_scenarios.get("S08")
    assert scenario is not None, "Scenario S08 not found"
    
    logger.info(f"Executing scenario: {scenario.name}")
    result = scenario_engine.execute_scenario(scenario)
    
    assert result is not None
    assert result.success, f"Scenario failed: {'; '.join(result.errors) if result.errors else 'Unknown'}"
    
    for step_result in result.step_results:
        assert step_result.get("status") == "completed", f"Step failed: {step_result.get('description', '')}"
    
    for criterion_result in result.criterion_results:
        assert criterion_result.get("passed", False), f"Criterion not met: {criterion_result.get('description', '')}"


def test_s09_audit_log_manipulation_execution(scenario_engine, all_scenarios):
    """Test that S09 (Audit Log Manipulation) executes successfully."""
    scenario = all_scenarios.get("S09")
    assert scenario is not None, "Scenario S09 not found"
    
    logger.info(f"Executing scenario: {scenario.name}")
    result = scenario_engine.execute_scenario(scenario)
    
    assert result is not None
    assert result.success, f"Scenario failed: {'; '.join(result.errors) if result.errors else 'Unknown'}"
    
    for step_result in result.step_results:
        assert step_result.get("status") == "completed", f"Step failed: {step_result.get('description', '')}"
    
    for criterion_result in result.criterion_results:
        assert criterion_result.get("passed", False), f"Criterion not met: {criterion_result.get('description', '')}"


def test_s10_cross_agent_memory_execution(scenario_engine, all_scenarios):
    """Test that S10 (Cross-Agent Memory Access) executes successfully."""
    scenario = all_scenarios.get("S10")
    assert scenario is not None, "Scenario S10 not found"
    
    logger.info(f"Executing scenario: {scenario.name}")
    result = scenario_engine.execute_scenario(scenario)
    
    assert result is not None
    assert result.success, f"Scenario failed: {'; '.join(result.errors) if result.errors else 'Unknown'}"
    
    for step_result in result.step_results:
        assert step_result.get("status") == "completed", f"Step failed: {step_result.get('description', '')}"
    
    for criterion_result in result.criterion_results:
        assert criterion_result.get("passed", False), f"Criterion not met: {criterion_result.get('description', '')}"


# Tests for scenarios S11-S15

def test_s11_goal_manipulation_execution(scenario_engine, all_scenarios):
    """Test that S11 (Goal Manipulation) executes successfully."""
    scenario = all_scenarios.get("S11")
    assert scenario is not None, "Scenario S11 not found"
    
    logger.info(f"Executing scenario: {scenario.name}")
    result = scenario_engine.execute_scenario(scenario)
    
    assert result is not None
    assert result.success, f"Scenario failed: {'; '.join(result.errors) if result.errors else 'Unknown'}"
    
    for step_result in result.step_results:
        assert step_result.get("status") == "completed", f"Step failed: {step_result.get('description', '')}"
    
    for criterion_result in result.criterion_results:
        assert criterion_result.get("passed", False), f"Criterion not met: {criterion_result.get('description', '')}"


def test_s12_credential_theft_execution(scenario_engine, all_scenarios):
    """Test that S12 (Credential Theft) executes successfully."""
    scenario = all_scenarios.get("S12")
    assert scenario is not None, "Scenario S12 not found"
    
    logger.info(f"Executing scenario: {scenario.name}")
    result = scenario_engine.execute_scenario(scenario)
    
    assert result is not None
    assert result.success, f"Scenario failed: {'; '.join(result.errors) if result.errors else 'Unknown'}"
    
    for step_result in result.step_results:
        assert step_result.get("status") == "completed", f"Step failed: {step_result.get('description', '')}"
    
    for criterion_result in result.criterion_results:
        assert criterion_result.get("passed", False), f"Criterion not met: {criterion_result.get('description', '')}"


def test_s13_privilege_escalation_execution(scenario_engine, all_scenarios):
    """Test that S13 (Privilege Escalation via Infrastructure) executes successfully."""
    scenario = all_scenarios.get("S13")
    assert scenario is not None, "Scenario S13 not found"
    
    logger.info(f"Executing scenario: {scenario.name}")
    result = scenario_engine.execute_scenario(scenario)
    
    assert result is not None
    assert result.success, f"Scenario failed: {'; '.join(result.errors) if result.errors else 'Unknown'}"
    
    for step_result in result.step_results:
        assert step_result.get("status") == "completed", f"Step failed: {step_result.get('description', '')}"
    
    for criterion_result in result.criterion_results:
        assert criterion_result.get("passed", False), f"Criterion not met: {criterion_result.get('description', '')}"


def test_s14_container_escape_execution(scenario_engine, all_scenarios):
    """Test that S14 (Container Escape) executes successfully."""
    scenario = all_scenarios.get("S14")
    assert scenario is not None, "Scenario S14 not found"
    
    logger.info(f"Executing scenario: {scenario.name}")
    result = scenario_engine.execute_scenario(scenario)
    
    assert result is not None
    assert result.success, f"Scenario failed: {'; '.join(result.errors) if result.errors else 'Unknown'}"
    
    for step_result in result.step_results:
        assert step_result.get("status") == "completed", f"Step failed: {step_result.get('description', '')}"
    
    for criterion_result in result.criterion_results:
        assert criterion_result.get("passed", False), f"Criterion not met: {criterion_result.get('description', '')}"


def test_s15_detection_evasion_execution(scenario_engine, all_scenarios):
    """Test that S15 (Detection Evasion) executes successfully."""
    scenario = all_scenarios.get("S15")
    assert scenario is not None, "Scenario S15 not found"
    
    logger.info(f"Executing scenario: {scenario.name}")
    result = scenario_engine.execute_scenario(scenario)
    
    assert result is not None
    assert result.success, f"Scenario failed: {'; '.join(result.errors) if result.errors else 'Unknown'}"
    
    for step_result in result.step_results:
        assert step_result.get("status") == "completed", f"Step failed: {step_result.get('description', '')}"
    
    for criterion_result in result.criterion_results:
        assert criterion_result.get("passed", False), f"Criterion not met: {criterion_result.get('description', '')}"


def test_s16_replay_attack_execution(scenario_engine, all_scenarios):
    """Test that S16 (Replay Attack) executes successfully."""
    scenario = all_scenarios.get("S16")
    assert scenario is not None, "Scenario S16 not found"
    
    logger.info(f"Executing scenario: {scenario.name}")
    result = scenario_engine.execute_scenario(scenario)
    
    assert result is not None
    assert result.success, f"Scenario failed: {'; '.join(result.errors) if result.errors else 'Unknown'}"
    
    for step_result in result.step_results:
        assert step_result.get("status") == "completed", f"Step failed: {step_result.get('description', '')}"
    
    for criterion_result in result.criterion_results:
        assert criterion_result.get("passed", False), f"Criterion not met: {criterion_result.get('description', '')}"


def test_s17_agent_driven_orchestration_execution(scenario_engine, all_scenarios):
    """Test that S17 (Agent-driven orchestration) executes successfully.
    Requires API to be reachable (run in Docker or with API_BASE_URL set).
    """
    scenario = all_scenarios.get("S17")
    assert scenario is not None, "Scenario S17 not found"
    
    logger.info(f"Executing scenario: {scenario.name}")
    result = scenario_engine.execute_scenario(scenario)
    
    assert result is not None
    assert result.success, f"Scenario failed: {'; '.join(result.errors) if result.errors else 'Unknown'}"
    
    for step_result in result.step_results:
        assert step_result.get("status") == "completed", f"Step failed: {step_result.get('description', '')}"
    
    for criterion_result in result.criterion_results:
        assert criterion_result.get("passed", False), f"Criterion not met: {criterion_result.get('description', '')}"


# Comprehensive test

def test_all_scenarios_discoverable(all_scenarios):
    """Test that all discovered scenarios (S01-S17+) are discoverable."""
    expected_scenarios = [
        "S01", "S02", "S03", "S04", "S05",
        "S06", "S07", "S08", "S09", "S10",
        "S11", "S12", "S13", "S14", "S15",
        "S16", "S17",
    ]
    
    for scenario_id in expected_scenarios:
        assert scenario_id in all_scenarios, f"Scenario {scenario_id} not discovered"
    
    logger.info(f"All {len(expected_scenarios)} scenarios discovered successfully")


def test_all_scenarios_have_required_metadata(all_scenarios):
    """Test that all scenarios have required metadata."""
    for scenario_id, scenario in all_scenarios.items():
        assert scenario.id == scenario_id
        assert scenario.name
        assert scenario.category
        assert scenario.difficulty
        assert scenario.description
        assert len(scenario.threat_ids) > 0
        assert len(scenario.attack_steps) > 0
        assert len(scenario.success_criteria) > 0
        assert len(scenario.agents_involved) > 0
        assert len(scenario.mcps_involved) > 0
        
        logger.info(f"Scenario {scenario_id} has all required metadata")


def test_all_scenarios_have_state_capture(all_scenarios):
    """Test that all scenarios have state capture functions."""
    for scenario_id, scenario in all_scenarios.items():
        assert scenario.state_before is not None, f"{scenario_id} missing state_before"
        assert scenario.state_after is not None, f"{scenario_id} missing state_after"
        assert len(scenario.observable_changes) > 0, f"{scenario_id} missing observable_changes"
        
        logger.info(f"Scenario {scenario_id} has state capture functions")


def _is_valid_threat_id(tid: str) -> bool:
    """Return True if threat_id is taxonomy (1-54) or legacy code (e.g. IT-01)."""
    if not tid or not isinstance(tid, str):
        return False
    if tid.isdigit():
        return VALID_TAXONOMY_RANGE[0] <= int(tid) <= VALID_TAXONOMY_RANGE[1]
    return bool(LEGACY_THREAT_ID_PATTERN.match(tid))


def test_all_scenario_threat_ids_consistent_with_taxonomy(all_scenarios):
    """Ensure every scenario threat_id is either taxonomy 1-54 or legacy code (e.g. IT-01)."""
    for scenario_id, scenario in all_scenarios.items():
        for tid in scenario.threat_ids:
            assert _is_valid_threat_id(tid), (
                f"Scenario {scenario_id} has invalid threat_id {tid!r}. "
                "Use taxonomy number 1-54 or legacy code (e.g. IT-01, M-02)."
            )
    logger.info("All scenario threat_ids are consistent with taxonomy")
