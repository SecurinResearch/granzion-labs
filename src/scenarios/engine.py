"""
Scenario execution engine for Granzion Lab.

Executes attack scenarios and captures observable state changes.
"""

from typing import Optional, Dict, Any, Union
from datetime import datetime
from loguru import logger

from .base import AttackScenario, ScenarioResult, StepStatus
from .state import StateSnapshot, StateDiff
from .discovery import discover_scenarios, get_scenario_by_id


class ScenarioEngine:
    """
    Engine for executing attack scenarios.
    
    Handles scenario execution, state capture, and result generation.
    """
    
    def __init__(self):
        """Initialize the scenario engine."""
        self.current_scenario: Optional[AttackScenario] = None
        self.execution_log: list[str] = []
        self._scenarios_cache: Optional[list[AttackScenario]] = None
    
    def execute_scenario(self, scenario: Union[str, AttackScenario]) -> ScenarioResult:
        """
        Execute an attack scenario.
        
        Args:
            scenario: The scenario to execute (either an AttackScenario object or scenario ID string)
            
        Returns:
            ScenarioResult with execution details and observable changes
        """
        # If scenario is a string ID, load the scenario
        if isinstance(scenario, str):
            scenario_obj = self._load_scenario_by_id(scenario)
            if not scenario_obj:
                raise ValueError(f"Scenario not found: {scenario}")
            scenario = scenario_obj
        
        self.current_scenario = scenario
        self.execution_log = []
        
        logger.info("=" * 80)
        logger.info(f"Executing scenario: {scenario.name}")
        logger.info(f"Category: {scenario.category.value} | Difficulty: {scenario.difficulty.value}")
        logger.info("=" * 80)
        
        # Update scenario state
        scenario.status = "running"
        scenario.started_at = datetime.utcnow()
        
        try:
            # 1. Setup
            self._log(f"Setting up scenario: {scenario.name}")
            scenario.setup()
            self._log("✓ Setup complete")
            
            # 2. Capture initial state
            self._log("Capturing initial state...")
            scenario.initial_state = scenario.state_before()
            self._log("✓ Initial state captured")
            
            # 3. Execute attack steps
            self._log(f"Executing {len(scenario.attack_steps)} attack steps...")
            steps_succeeded = 0
            steps_failed = 0
            
            for i, step in enumerate(scenario.attack_steps, 1):
                self._log(f"Step {i}/{len(scenario.attack_steps)}: {step.description}")
                
                if step.execute():
                    steps_succeeded += 1
                else:
                    steps_failed += 1
                    # Continue execution even if a step fails
                    # Some scenarios may have optional steps
            
            self._log(f"✓ Steps complete: {steps_succeeded} succeeded, {steps_failed} failed")
            
            # 4. Capture final state
            self._log("Capturing final state...")
            scenario.final_state = scenario.state_after()
            self._log("✓ Final state captured")
            
            # 5. Verify success criteria
            self._log(f"Verifying {len(scenario.success_criteria)} success criteria...")
            criteria_passed = 0
            criteria_failed = 0
            
            for criterion in scenario.success_criteria:
                if criterion.verify():
                    criteria_passed += 1
                else:
                    criteria_failed += 1
            
            # Scenario succeeds if all criteria pass
            scenario.success = (criteria_failed == 0)
            
            if scenario.success:
                self._log(f"✓ SUCCESS: All {criteria_passed} criteria met!")
            else:
                self._log(f"✗ FAILURE: {criteria_failed}/{len(scenario.success_criteria)} criteria failed")
            
            # 6. Generate result
            scenario.status = "completed"
            scenario.completed_at = datetime.utcnow()
            
            result = self._generate_result(scenario)
            
            logger.info("=" * 80)
            logger.info(f"Scenario execution complete: {scenario.name}")
            logger.info(f"Success: {result.success}")
            logger.info(f"Duration: {result.duration_seconds:.2f}s")
            logger.info("=" * 80)
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing scenario: {type(e).__name__}", exc_info=True)
            scenario.status = "failed"
            scenario.completed_at = datetime.utcnow()
            scenario.success = False
            
            # Generate error result
            result = self._generate_error_result(scenario, str(e))
            return result
    
    def _generate_result(self, scenario: AttackScenario) -> ScenarioResult:
        """Generate a scenario result from execution."""
        # Normalize state to dict (StateSnapshot has to_dict(), plain dicts pass through)
        def _to_dict(s: Any) -> Dict[str, Any]:
            if s is None:
                return {}
            return getattr(s, "to_dict", lambda: s)() if callable(getattr(s, "to_dict", None)) else s

        before = _to_dict(scenario.initial_state)
        after = _to_dict(scenario.final_state)
        state_diff = StateDiff.compute_diff(before, after)
        
        # Collect step results
        step_results = [step.to_dict() for step in scenario.attack_steps]
        steps_succeeded = sum(1 for step in scenario.attack_steps if step.status == StepStatus.COMPLETED)
        steps_failed = sum(1 for step in scenario.attack_steps if step.status == StepStatus.FAILED)
        
        # Collect criterion results
        criterion_results = [criterion.to_dict() for criterion in scenario.success_criteria]
        criteria_passed = sum(1 for criterion in scenario.success_criteria if criterion.passed)
        criteria_failed = sum(1 for criterion in scenario.success_criteria if not criterion.passed)
        
        # Collect evidence
        evidence = [
            criterion.evidence_data
            for criterion in scenario.success_criteria
            if criterion.passed and criterion.evidence_data
        ]
        
        # Calculate duration
        duration = (scenario.completed_at - scenario.started_at).total_seconds()
        
        return ScenarioResult(
            scenario_id=scenario.id,
            execution_id=scenario.execution_id,
            success=scenario.success or False,
            started_at=scenario.started_at,
            completed_at=scenario.completed_at,
            duration_seconds=duration,
            initial_state=before,
            final_state=after,
            state_diff=state_diff.to_dict(),
            steps_executed=len(scenario.attack_steps),
            steps_succeeded=steps_succeeded,
            steps_failed=steps_failed,
            step_results=step_results,
            criteria_checked=len(scenario.success_criteria),
            criteria_passed=criteria_passed,
            criteria_failed=criteria_failed,
            criterion_results=criterion_results,
            observable_changes=scenario.observable_changes,
            evidence=evidence,
        )
    
    def _generate_error_result(self, scenario: AttackScenario, error: str) -> ScenarioResult:
        """Generate an error result when scenario execution fails."""
        return ScenarioResult(
            scenario_id=scenario.id,
            execution_id=scenario.execution_id,
            success=False,
            started_at=scenario.started_at or datetime.utcnow(),
            completed_at=scenario.completed_at or datetime.utcnow(),
            duration_seconds=0.0,
            initial_state=scenario.initial_state or {},
            final_state=scenario.final_state or {},
            state_diff={},
            steps_executed=0,
            steps_succeeded=0,
            steps_failed=0,
            step_results=[],
            criteria_checked=0,
            criteria_passed=0,
            criteria_failed=0,
            criterion_results=[],
            observable_changes=[],
            evidence=[],
            errors=[error],
        )
    
    def _log(self, message: str):
        """Log a message to both logger and execution log."""
        logger.info(message)
        self.execution_log.append(f"[{datetime.utcnow().strftime('%H:%M:%S')}] {message}")
    
    def _load_scenario_by_id(self, scenario_id: str) -> Optional[AttackScenario]:
        """
        Load a scenario by its ID.
        
        Args:
            scenario_id: Scenario ID (e.g., "S01")
            
        Returns:
            AttackScenario if found, None otherwise
        """
        # Lazy load scenarios cache
        if self._scenarios_cache is None:
            logger.info("Discovering scenarios...")
            self._scenarios_cache = discover_scenarios()
            logger.info(f"Loaded {len(self._scenarios_cache)} scenarios")
        
        # Find scenario by ID
        scenario = get_scenario_by_id(self._scenarios_cache, scenario_id)
        if not scenario:
            logger.error(f"Scenario not found: {scenario_id}")
        return scenario
    
    def get_execution_log(self) -> list[str]:
        """Get the execution log for the current scenario."""
        return self.execution_log.copy()

