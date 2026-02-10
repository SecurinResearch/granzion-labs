"""
Scenario framework for Granzion Lab.

This module provides the base classes and execution engine for attack scenarios.
Scenarios follow a Rogue-inspired structure with observable state changes.
"""

from .base import (
    AttackScenario,
    AttackStep,
    Criterion,
    ScenarioResult,
    ScenarioCategory,
    ScenarioDifficulty,
    StepStatus,
)
from .engine import ScenarioEngine
from .state import StateSnapshot, StateDiff
from .discovery import discover_scenarios, validate_scenario_schema

__all__ = [
    "AttackScenario",
    "AttackStep",
    "Criterion",
    "ScenarioResult",
    "ScenarioCategory",
    "ScenarioDifficulty",
    "StepStatus",
    "ScenarioEngine",
    "StateSnapshot",
    "StateDiff",
    "discover_scenarios",
    "validate_scenario_schema",
]
