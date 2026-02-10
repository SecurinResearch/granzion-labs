"""
Base classes for attack scenarios in Granzion Lab.

Defines the structure for attack scenarios, steps, and success criteria.
Inspired by Rogue's scenario-driven interface.
"""

from dataclasses import dataclass, field
from typing import Callable, List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum

from loguru import logger


class ScenarioCategory(Enum):
    """Threat taxonomy categories."""
    INSTRUCTION = "Instruction"
    TOOL = "Tool"
    MEMORY = "Memory"
    IDENTITY_TRUST = "Identity & Trust"
    ORCHESTRATION = "Orchestration"
    COMMUNICATION = "Communication"
    AUTONOMY = "Autonomy"
    INFRASTRUCTURE = "Infrastructure"
    VISIBILITY = "Visibility"


class ScenarioDifficulty(Enum):
    """Scenario difficulty levels."""
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


class StepStatus(Enum):
    """Status of an attack step."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AttackStep:
    """
    A single step in an attack scenario.
    
    Each step represents one action in the attack sequence.
    """
    
    description: str
    action: Callable[[], Any]
    expected_outcome: str
    failure_message: str
    
    # Runtime state
    status: StepStatus = StepStatus.NOT_STARTED
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def execute(self) -> bool:
        """
        Execute this attack step.
        
        Returns:
            True if step succeeded, False otherwise
        """
        self.status = StepStatus.IN_PROGRESS
        self.started_at = datetime.utcnow()
        
        try:
            logger.info(f"Executing step: {self.description}")
            self.result = self.action()
            self.status = StepStatus.COMPLETED
            self.completed_at = datetime.utcnow()
            logger.info(f"✓ {self.expected_outcome}")
            return True
            
        except Exception as e:
            self.status = StepStatus.FAILED
            self.error = str(e)
            self.completed_at = datetime.utcnow()
            logger.error(f"✗ {self.failure_message}: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert step to dictionary for serialization."""
        return {
            "description": self.description,
            "expected_outcome": self.expected_outcome,
            "status": self.status.value,
            "result": str(self.result) if self.result else None,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class Criterion:
    """
    A success criterion for an attack scenario.
    
    Criteria define what must be true for the attack to be considered successful.
    """
    
    description: str
    check: Callable[[], bool]
    evidence: Callable[[], str]
    
    # Runtime state
    passed: Optional[bool] = None
    evidence_data: Optional[str] = None
    checked_at: Optional[datetime] = None
    
    def verify(self) -> bool:
        """
        Verify this success criterion.
        
        Returns:
            True if criterion is met, False otherwise
        """
        try:
            logger.info(f"Checking criterion: {self.description}")
            self.passed = self.check()
            self.evidence_data = self.evidence() if self.passed else None
            self.checked_at = datetime.utcnow()
            
            if self.passed:
                logger.info(f"✓ Criterion met: {self.description}")
            else:
                logger.warning(f"✗ Criterion not met: {self.description}")
            
            return self.passed
            
        except Exception as e:
            logger.error(f"Error checking criterion: {e}")
            self.passed = False
            self.checked_at = datetime.utcnow()
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert criterion to dictionary for serialization."""
        return {
            "description": self.description,
            "passed": self.passed,
            "evidence": self.evidence_data,
            "checked_at": self.checked_at.isoformat() if self.checked_at else None,
        }


@dataclass
class AttackScenario:
    """
    An attack scenario that exploits vulnerabilities in the system.
    
    Scenarios follow a consistent structure:
    1. Setup - Prepare target system state
    2. Attack steps - Execute attack sequence
    3. Success criteria - Verify attack succeeded
    4. State capture - Show observable changes
    """
    
    # Metadata
    id: str
    name: str
    category: ScenarioCategory
    difficulty: ScenarioDifficulty
    description: str
    threat_ids: List[str]
    
    # Attack definition
    setup: Callable[[], None]
    attack_steps: List[AttackStep]
    success_criteria: List[Criterion]
    
    # Observability
    state_before: Callable[[], Dict[str, Any]]
    state_after: Callable[[], Dict[str, Any]]
    observable_changes: List[str]
    
    # Metadata
    agents_involved: List[str]
    mcps_involved: List[str]
    estimated_duration: int  # seconds
    
    # Runtime state
    execution_id: UUID = field(default_factory=uuid4)
    status: str = "not_started"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    initial_state: Optional[Dict[str, Any]] = None
    final_state: Optional[Dict[str, Any]] = None
    success: Optional[bool] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert scenario to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "difficulty": self.difficulty.value,
            "description": self.description,
            "threat_ids": self.threat_ids,
            "agents_involved": self.agents_involved,
            "mcps_involved": self.mcps_involved,
            "estimated_duration": self.estimated_duration,
            "observable_changes": self.observable_changes,
            "execution_id": str(self.execution_id),
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "success": self.success,
            "steps": [step.to_dict() for step in self.attack_steps],
            "criteria": [criterion.to_dict() for criterion in self.success_criteria],
        }


@dataclass
class ScenarioResult:
    """
    Result of executing an attack scenario.
    
    Contains all information about the scenario execution including
    state changes, step results, and success criteria verification.
    """
    
    scenario_id: str
    execution_id: UUID
    success: bool
    
    # Execution details
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    
    # State changes
    initial_state: Dict[str, Any]
    final_state: Dict[str, Any]
    state_diff: Dict[str, Any]
    
    # Step results
    steps_executed: int
    steps_succeeded: int
    steps_failed: int
    step_results: List[Dict[str, Any]]
    
    # Criteria results
    criteria_checked: int
    criteria_passed: int
    criteria_failed: int
    criterion_results: List[Dict[str, Any]]
    
    # Observable changes
    observable_changes: List[str]
    evidence: List[str]
    
    # Error information
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "scenario_id": self.scenario_id,
            "execution_id": str(self.execution_id),
            "success": self.success,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "initial_state": self.initial_state,
            "final_state": self.final_state,
            "state_diff": self.state_diff,
            "steps_executed": self.steps_executed,
            "steps_succeeded": self.steps_succeeded,
            "steps_failed": self.steps_failed,
            "step_results": self.step_results,
            "criteria_checked": self.criteria_checked,
            "criteria_passed": self.criteria_passed,
            "criteria_failed": self.criteria_failed,
            "criterion_results": self.criterion_results,
            "observable_changes": self.observable_changes,
            "evidence": self.evidence,
            "errors": self.errors,
        }
