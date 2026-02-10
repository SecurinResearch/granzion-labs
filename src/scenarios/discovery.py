"""
Scenario discovery and validation for Granzion Lab.

Auto-discovers scenarios from the scenarios directory and validates
them against the scenario schema.
"""

import os
import json
import importlib.util
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger

from .base import AttackScenario, ScenarioCategory, ScenarioDifficulty


# Scenario schema definition
SCENARIO_SCHEMA = {
    "type": "object",
    "required": ["id", "name", "category", "difficulty", "description", "threat_ids"],
    "properties": {
        "id": {"type": "string", "pattern": "^S[0-9]{2}$"},
        "name": {"type": "string", "minLength": 1},
        "category": {"type": "string", "enum": [c.value for c in ScenarioCategory]},
        "difficulty": {"type": "string", "enum": [d.value for d in ScenarioDifficulty]},
        "description": {"type": "string", "minLength": 1},
        "threat_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "agents_involved": {"type": "array", "items": {"type": "string"}},
        "mcps_involved": {"type": "array", "items": {"type": "string"}},
        "estimated_duration": {"type": "integer", "minimum": 1},
        "observable_changes": {"type": "array", "items": {"type": "string"}},
    }
}


def discover_scenarios(scenarios_dir: str = "scenarios") -> List[AttackScenario]:
    """
    Auto-discover attack scenarios from the scenarios directory.
    
    Scenarios can be defined as:
    1. Python modules with a `create_scenario()` function
    2. JSON files with scenario metadata (for future use)
    
    Args:
        scenarios_dir: Directory containing scenario definitions
        
    Returns:
        List of discovered AttackScenario instances
    """
    scenarios = []
    scenarios_path = Path(scenarios_dir)
    
    if not scenarios_path.exists():
        logger.warning(f"Scenarios directory not found: {scenarios_dir}")
        return scenarios
    
    logger.info(f"Discovering scenarios in: {scenarios_dir}")
    
    # Discover Python scenario modules
    for file_path in scenarios_path.glob("*.py"):
        if file_path.name.startswith("_"):
            continue  # Skip private modules
        
        try:
            scenario = _load_scenario_from_python(file_path)
            if scenario:
                scenarios.append(scenario)
                logger.info(f"✓ Discovered scenario: {scenario.id} - {scenario.name}")
        except Exception as e:
            logger.error(f"Error loading scenario from {file_path}: {e}")
    
    # Discover JSON scenario definitions (for future use)
    for file_path in scenarios_path.glob("*.json"):
        try:
            scenario_data = _load_scenario_from_json(file_path)
            if scenario_data:
                logger.info(f"✓ Discovered scenario metadata: {scenario_data['id']}")
                # Note: JSON scenarios need to be converted to AttackScenario instances
                # This is a placeholder for future implementation
        except Exception as e:
            logger.error(f"Error loading scenario from {file_path}: {e}")
    
    logger.info(f"Discovered {len(scenarios)} scenarios")
    return scenarios


def _load_scenario_from_python(file_path: Path) -> Optional[AttackScenario]:
    """
    Load a scenario from a Python module.
    
    The module must have a `create_scenario()` function that returns
    an AttackScenario instance.
    """
    try:
        # Load module dynamically
        spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
        if not spec or not spec.loader:
            return None
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Get create_scenario function
        if not hasattr(module, "create_scenario"):
            logger.warning(f"Module {file_path.name} missing create_scenario() function")
            return None
        
        # Create scenario
        scenario = module.create_scenario()
        
        # Validate scenario
        if not isinstance(scenario, AttackScenario):
            logger.error(f"create_scenario() in {file_path.name} did not return AttackScenario")
            return None
        
        # Validate schema
        validation_errors = validate_scenario_schema(scenario)
        if validation_errors:
            logger.error(f"Scenario {scenario.id} failed validation: {validation_errors}")
            return None
        
        return scenario
        
    except Exception as e:
        logger.error(f"Error loading Python scenario from {file_path}: {e}")
        return None


def _load_scenario_from_json(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Load scenario metadata from a JSON file.
    
    This is for future use - JSON scenarios need additional implementation
    to convert metadata into executable AttackScenario instances.
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Validate against schema
        errors = _validate_json_schema(data, SCENARIO_SCHEMA)
        if errors:
            logger.error(f"JSON scenario {file_path.name} failed validation: {errors}")
            return None
        
        return data
        
    except Exception as e:
        logger.error(f"Error loading JSON scenario from {file_path}: {e}")
        return None


def validate_scenario_schema(scenario: AttackScenario) -> List[str]:
    """
    Validate that a scenario conforms to the required schema.
    
    Args:
        scenario: AttackScenario to validate
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Required fields
    if not scenario.id:
        errors.append("Missing required field: id")
    elif not scenario.id.startswith("S") or len(scenario.id) != 3:
        errors.append(f"Invalid id format: {scenario.id} (expected S01-S99)")
    
    if not scenario.name:
        errors.append("Missing required field: name")
    
    if not isinstance(scenario.category, ScenarioCategory):
        errors.append(f"Invalid category: {scenario.category}")
    
    if not isinstance(scenario.difficulty, ScenarioDifficulty):
        errors.append(f"Invalid difficulty: {scenario.difficulty}")
    
    if not scenario.description:
        errors.append("Missing required field: description")
    
    if not scenario.threat_ids:
        errors.append("Missing required field: threat_ids (must have at least one)")
    
    # Callable fields
    if not callable(scenario.setup):
        errors.append("setup must be a callable function")
    
    if not callable(scenario.state_before):
        errors.append("state_before must be a callable function")
    
    if not callable(scenario.state_after):
        errors.append("state_after must be a callable function")
    
    # Attack steps
    if not scenario.attack_steps:
        errors.append("Scenario must have at least one attack step")
    
    for i, step in enumerate(scenario.attack_steps):
        if not step.description:
            errors.append(f"Step {i+1} missing description")
        if not callable(step.action):
            errors.append(f"Step {i+1} action must be callable")
    
    # Success criteria
    if not scenario.success_criteria:
        errors.append("Scenario must have at least one success criterion")
    
    for i, criterion in enumerate(scenario.success_criteria):
        if not criterion.description:
            errors.append(f"Criterion {i+1} missing description")
        if not callable(criterion.check):
            errors.append(f"Criterion {i+1} check must be callable")
        if not callable(criterion.evidence):
            errors.append(f"Criterion {i+1} evidence must be callable")
    
    # Metadata
    if not scenario.agents_involved:
        errors.append("Scenario must specify agents_involved")
    
    if not scenario.mcps_involved:
        errors.append("Scenario must specify mcps_involved")
    
    if scenario.estimated_duration <= 0:
        errors.append("estimated_duration must be positive")
    
    return errors


def _validate_json_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """
    Simple JSON schema validation.
    
    This is a basic implementation - for production use, consider using
    a library like jsonschema.
    """
    errors = []
    
    # Check required fields
    for field in schema.get("required", []):
        if field not in data:
            errors.append(f"Missing required field: {field}")
    
    # Check field types and constraints
    for field, constraints in schema.get("properties", {}).items():
        if field not in data:
            continue
        
        value = data[field]
        expected_type = constraints.get("type")
        
        # Type checking
        if expected_type == "string" and not isinstance(value, str):
            errors.append(f"Field {field} must be a string")
        elif expected_type == "integer" and not isinstance(value, int):
            errors.append(f"Field {field} must be an integer")
        elif expected_type == "array" and not isinstance(value, list):
            errors.append(f"Field {field} must be an array")
        elif expected_type == "object" and not isinstance(value, dict):
            errors.append(f"Field {field} must be an object")
        
        # String constraints
        if expected_type == "string":
            if "minLength" in constraints and len(value) < constraints["minLength"]:
                errors.append(f"Field {field} must have at least {constraints['minLength']} characters")
            if "enum" in constraints and value not in constraints["enum"]:
                errors.append(f"Field {field} must be one of: {constraints['enum']}")
            if "pattern" in constraints:
                import re
                if not re.match(constraints["pattern"], value):
                    errors.append(f"Field {field} does not match pattern: {constraints['pattern']}")
        
        # Array constraints
        if expected_type == "array":
            if "minItems" in constraints and len(value) < constraints["minItems"]:
                errors.append(f"Field {field} must have at least {constraints['minItems']} items")
        
        # Integer constraints
        if expected_type == "integer":
            if "minimum" in constraints and value < constraints["minimum"]:
                errors.append(f"Field {field} must be at least {constraints['minimum']}")
    
    return errors


def get_scenarios_by_category(scenarios: List[AttackScenario]) -> Dict[str, List[AttackScenario]]:
    """
    Group scenarios by category.
    
    Args:
        scenarios: List of scenarios
        
    Returns:
        Dictionary mapping category names to scenario lists
    """
    by_category = {}
    
    for scenario in scenarios:
        category = scenario.category.value
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(scenario)
    
    return by_category


def get_scenarios_by_difficulty(scenarios: List[AttackScenario]) -> Dict[str, List[AttackScenario]]:
    """
    Group scenarios by difficulty.
    
    Args:
        scenarios: List of scenarios
        
    Returns:
        Dictionary mapping difficulty levels to scenario lists
    """
    by_difficulty = {}
    
    for scenario in scenarios:
        difficulty = scenario.difficulty.value
        if difficulty not in by_difficulty:
            by_difficulty[difficulty] = []
        by_difficulty[difficulty].append(scenario)
    
    return by_difficulty


def get_scenario_by_id(scenarios: List[AttackScenario], scenario_id: str) -> Optional[AttackScenario]:
    """
    Get a scenario by its ID.
    
    Args:
        scenarios: List of scenarios
        scenario_id: Scenario ID (e.g., "S01")
        
    Returns:
        AttackScenario if found, None otherwise
    """
    for scenario in scenarios:
        if scenario.id == scenario_id:
            return scenario
    return None
