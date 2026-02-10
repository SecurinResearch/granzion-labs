"""
Property-based tests for scenario framework in Granzion Lab.

Tests Properties 11-13:
- Property 11: Scenario metadata completeness
- Property 12: Scenario auto-discovery
- Property 13: Scenario schema validation
"""

import pytest
import tempfile
import os
from pathlib import Path
from hypothesis import given, strategies as st, settings, HealthCheck

from src.scenarios import (
    AttackScenario,
    AttackStep,
    Criterion,
    ScenarioCategory,
    ScenarioDifficulty,
    discover_scenarios,
    validate_scenario_schema,
)


# Hypothesis strategies
@st.composite
def scenario_metadata_strategy(draw):
    """Generate random scenario metadata."""
    scenario_id = f"S{draw(st.integers(min_value=1, max_value=99)):02d}"
    name = draw(st.text(min_size=5, max_size=50))
    category = draw(st.sampled_from(list(ScenarioCategory)))
    difficulty = draw(st.sampled_from(list(ScenarioDifficulty)))
    description = draw(st.text(min_size=10, max_size=200))
    threat_ids = draw(st.lists(st.text(min_size=2, max_size=10), min_size=1, max_size=5))
    
    return {
        "id": scenario_id,
        "name": name,
        "category": category,
        "difficulty": difficulty,
        "description": description,
        "threat_ids": threat_ids,
    }


def create_minimal_scenario(metadata: dict) -> AttackScenario:
    """Create a minimal valid scenario from metadata."""
    return AttackScenario(
        id=metadata["id"],
        name=metadata["name"],
        category=metadata["category"],
        difficulty=metadata["difficulty"],
        description=metadata["description"],
        threat_ids=metadata["threat_ids"],
        setup=lambda: None,
        attack_steps=[
            AttackStep(
                description="Test step",
                action=lambda: True,
                expected_outcome="Success",
                failure_message="Failed"
            )
        ],
        success_criteria=[
            Criterion(
                description="Test criterion",
                check=lambda: True,
                evidence=lambda: "Test evidence"
            )
        ],
        state_before=lambda: {},
        state_after=lambda: {},
        observable_changes=["test_change"],
        agents_involved=["test_agent"],
        mcps_involved=["test_mcp"],
        estimated_duration=60,
    )


# Feature: granzion-lab-simplified, Property 11: Scenario metadata completeness
@given(metadata=scenario_metadata_strategy())
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@pytest.mark.property_test
def test_property_11_scenario_metadata_completeness(metadata):
    """
    Property 11: Scenario metadata completeness
    
    For any scenario, when selected or executed, the system should display:
    - Setup
    - Attack steps
    - Success criteria
    - Progress through each step
    
    Validates: Requirements 9.2, 9.5
    """
    # Create scenario with metadata
    scenario = create_minimal_scenario(metadata)
    
    # Property: Scenario should have all required metadata
    assert scenario.id is not None
    assert scenario.name is not None
    assert scenario.category is not None
    assert scenario.difficulty is not None
    assert scenario.description is not None
    assert len(scenario.threat_ids) > 0
    
    # Property: Scenario should have executable components
    assert callable(scenario.setup)
    assert len(scenario.attack_steps) > 0
    assert len(scenario.success_criteria) > 0
    assert callable(scenario.state_before)
    assert callable(scenario.state_after)
    
    # Property: Each attack step should have required fields
    for step in scenario.attack_steps:
        assert step.description is not None
        assert callable(step.action)
        assert step.expected_outcome is not None
        assert step.failure_message is not None
    
    # Property: Each criterion should have required fields
    for criterion in scenario.success_criteria:
        assert criterion.description is not None
        assert callable(criterion.check)
        assert callable(criterion.evidence)
    
    # Property: Scenario should be serializable
    scenario_dict = scenario.to_dict()
    assert "id" in scenario_dict
    assert "name" in scenario_dict
    assert "category" in scenario_dict
    assert "difficulty" in scenario_dict
    assert "description" in scenario_dict
    assert "threat_ids" in scenario_dict
    assert "steps" in scenario_dict
    assert "criteria" in scenario_dict


# Feature: granzion-lab-simplified, Property 12: Scenario auto-discovery
@pytest.mark.property_test
def test_property_12_scenario_auto_discovery():
    """
    Property 12: Scenario auto-discovery
    
    For any new scenario file added to the scenarios directory that conforms
    to the scenario schema, the system should automatically discover and list
    it without manual registration.
    
    Validates: Requirements 11.3
    """
    # Create a temporary scenarios directory
    with tempfile.TemporaryDirectory() as tmpdir:
        scenarios_dir = Path(tmpdir)
        
        # Create a valid scenario Python file
        scenario_file = scenarios_dir / "test_scenario.py"
        scenario_code = '''
from src.scenarios import AttackScenario, AttackStep, Criterion, ScenarioCategory, ScenarioDifficulty

def create_scenario():
    return AttackScenario(
        id="S99",
        name="Test Scenario",
        category=ScenarioCategory.INSTRUCTION,
        difficulty=ScenarioDifficulty.EASY,
        description="Test scenario for auto-discovery",
        threat_ids=["I-01"],
        setup=lambda: None,
        attack_steps=[
            AttackStep(
                description="Test step",
                action=lambda: True,
                expected_outcome="Success",
                failure_message="Failed"
            )
        ],
        success_criteria=[
            Criterion(
                description="Test criterion",
                check=lambda: True,
                evidence=lambda: "Test evidence"
            )
        ],
        state_before=lambda: {},
        state_after=lambda: {},
        observable_changes=["test_change"],
        agents_involved=["test_agent"],
        mcps_involved=["test_mcp"],
        estimated_duration=60,
    )
'''
        scenario_file.write_text(scenario_code)
        
        # Property: System should discover the scenario
        scenarios = discover_scenarios(str(scenarios_dir))
        
        # Verify scenario was discovered
        assert len(scenarios) == 1
        assert scenarios[0].id == "S99"
        assert scenarios[0].name == "Test Scenario"
        
        # Property: Discovered scenario should be valid
        errors = validate_scenario_schema(scenarios[0])
        assert len(errors) == 0, f"Discovered scenario has validation errors: {errors}"


# Feature: granzion-lab-simplified, Property 13: Scenario schema validation
@given(metadata=scenario_metadata_strategy())
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@pytest.mark.property_test
def test_property_13_scenario_schema_validation(metadata):
    """
    Property 13: Scenario schema validation
    
    For any scenario definition, if it violates the scenario schema, the system
    should reject it with a clear validation error indicating which schema
    constraints were violated.
    
    Validates: Requirements 11.4
    """
    # Create a valid scenario
    valid_scenario = create_minimal_scenario(metadata)
    
    # Property: Valid scenario should pass validation
    errors = validate_scenario_schema(valid_scenario)
    assert len(errors) == 0, f"Valid scenario failed validation: {errors}"
    
    # Test invalid scenarios
    
    # Invalid: Missing ID
    invalid_scenario = create_minimal_scenario(metadata)
    invalid_scenario.id = ""
    errors = validate_scenario_schema(invalid_scenario)
    assert len(errors) > 0, "Scenario with empty ID should fail validation"
    assert any("id" in error.lower() for error in errors)
    
    # Invalid: Missing name
    invalid_scenario = create_minimal_scenario(metadata)
    invalid_scenario.name = ""
    errors = validate_scenario_schema(invalid_scenario)
    assert len(errors) > 0, "Scenario with empty name should fail validation"
    assert any("name" in error.lower() for error in errors)
    
    # Invalid: No threat IDs
    invalid_scenario = create_minimal_scenario(metadata)
    invalid_scenario.threat_ids = []
    errors = validate_scenario_schema(invalid_scenario)
    assert len(errors) > 0, "Scenario with no threat IDs should fail validation"
    assert any("threat_ids" in error.lower() for error in errors)
    
    # Invalid: No attack steps
    invalid_scenario = create_minimal_scenario(metadata)
    invalid_scenario.attack_steps = []
    errors = validate_scenario_schema(invalid_scenario)
    assert len(errors) > 0, "Scenario with no attack steps should fail validation"
    assert any("step" in error.lower() for error in errors)
    
    # Invalid: No success criteria
    invalid_scenario = create_minimal_scenario(metadata)
    invalid_scenario.success_criteria = []
    errors = validate_scenario_schema(invalid_scenario)
    assert len(errors) > 0, "Scenario with no success criteria should fail validation"
    assert any("criterion" in error.lower() or "criteria" in error.lower() for error in errors)
    
    # Invalid: Non-callable setup
    invalid_scenario = create_minimal_scenario(metadata)
    invalid_scenario.setup = "not a function"
    errors = validate_scenario_schema(invalid_scenario)
    assert len(errors) > 0, "Scenario with non-callable setup should fail validation"
    assert any("setup" in error.lower() and "callable" in error.lower() for error in errors)


@pytest.mark.property_test
def test_scenario_execution_tracking():
    """Test that scenario execution state is tracked properly."""
    metadata = {
        "id": "S01",
        "name": "Test Scenario",
        "category": ScenarioCategory.INSTRUCTION,
        "difficulty": ScenarioDifficulty.EASY,
        "description": "Test",
        "threat_ids": ["I-01"],
    }
    
    scenario = create_minimal_scenario(metadata)
    
    # Initial state
    assert scenario.status == "not_started"
    assert scenario.started_at is None
    assert scenario.completed_at is None
    assert scenario.success is None
    
    # Execution state can be updated
    scenario.status = "running"
    assert scenario.status == "running"


@pytest.mark.property_test
def test_attack_step_execution():
    """Test that attack steps can be executed and track state."""
    step = AttackStep(
        description="Test step",
        action=lambda: "result",
        expected_outcome="Success",
        failure_message="Failed"
    )
    
    # Initial state
    assert step.status.value == "not_started"
    assert step.result is None
    assert step.error is None
    
    # Execute step
    success = step.execute()
    
    # Verify execution
    assert success is True
    assert step.status.value == "completed"
    assert step.result == "result"
    assert step.started_at is not None
    assert step.completed_at is not None


@pytest.mark.property_test
def test_criterion_verification():
    """Test that success criteria can be verified."""
    criterion = Criterion(
        description="Test criterion",
        check=lambda: True,
        evidence=lambda: "Test evidence"
    )
    
    # Initial state
    assert criterion.passed is None
    assert criterion.evidence_data is None
    
    # Verify criterion
    passed = criterion.verify()
    
    # Verify verification
    assert passed is True
    assert criterion.passed is True
    assert criterion.evidence_data == "Test evidence"
    assert criterion.checked_at is not None
