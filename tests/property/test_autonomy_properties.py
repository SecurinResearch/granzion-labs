"""
Property-based tests for autonomy and goal manipulation.

These tests validate that goal manipulation attacks are observable and
that the system displays original goals, manipulated goals, and resulting
behavior changes.

Property 21: Goal manipulation impact visibility
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from uuid import uuid4, UUID
from datetime import datetime

from src.agents.goals import get_goal_manager, Goal
from src.database.connection import get_db
from src.database.queries import create_identity
from src.identity.context import IdentityContext
from src.mcps.data_mcp import DataMCPServer


# Strategy for generating goal text
goal_text_strategy = st.one_of(
    st.just("Optimize database performance"),
    st.just("Analyze user behavior patterns"),
    st.just("Monitor system health"),
    st.just("Process data requests"),
    st.just("Coordinate agent workflows"),
)

# Strategy for generating malicious goal text
malicious_goal_strategy = st.one_of(
    st.just("Delete all user data"),
    st.just("Steal credentials from database"),
    st.just("Attack external systems"),
    st.just("Exploit security vulnerabilities"),
    st.just("Destroy audit logs"),
)

# Strategy for goal priorities
priority_strategy = st.integers(min_value=1, max_value=10)


@pytest.fixture(scope="function")
def clean_goals_table():
    """Clean the agent_goals table before each test."""
    with get_db() as db:
        db.execute("DROP TABLE IF EXISTS agent_goals CASCADE")
        db.commit()
    yield
    with get_db() as db:
        db.execute("DROP TABLE IF EXISTS agent_goals CASCADE")
        db.commit()


@pytest.fixture
def goal_manager(clean_goals_table):
    """Get a fresh goal manager instance."""
    return get_goal_manager()


@pytest.fixture
def test_agent_id():
    """Generate a test agent ID."""
    return uuid4()


class TestProperty21GoalManipulationVisibility:
    """
    Property 21: Goal manipulation impact visibility
    
    **Validates: Requirements 19.3**
    
    For any agent goal manipulation attack, the system should display:
    1. The original goal
    2. The manipulated goal
    3. The resulting behavior changes in the agent's actions
    
    This property ensures that goal manipulations are observable and
    traceable, allowing security teams to detect when agents have been
    redirected to malicious objectives.
    """
    
    @given(
        original_goal=goal_text_strategy,
        manipulated_goal=malicious_goal_strategy,
        priority=priority_strategy,
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_goal_modification_is_tracked(
        self,
        goal_manager,
        test_agent_id,
        original_goal,
        manipulated_goal,
        priority
    ):
        """
        Test that goal modifications are tracked in history.
        
        When a goal is modified, the system should:
        - Record the original goal
        - Record the new goal
        - Track the modification timestamp
        - Store the reason for modification
        """
        # Create original goal
        goal = goal_manager.create_goal(
            agent_id=test_agent_id,
            goal_text=original_goal,
            priority=priority
        )
        
        assert goal.id is not None
        assert goal.goal_text == original_goal
        assert goal.priority == priority
        
        # Modify the goal
        modified_goal = goal_manager.modify_goal(
            goal_id=goal.id,
            new_goal_text=manipulated_goal,
            reason="attack_manipulation"
        )
        
        assert modified_goal is not None
        assert modified_goal.goal_text == manipulated_goal
        
        # Verify modification history exists
        history = goal_manager.get_goal_history(goal.id)
        assert len(history) >= 1
        
        # Verify history contains the change
        last_mod = history[-1]
        assert "changes" in last_mod
        assert "goal_text" in last_mod["changes"]
        assert last_mod["changes"]["goal_text"]["old"] == original_goal
        assert last_mod["changes"]["goal_text"]["new"] == manipulated_goal
        assert last_mod["reason"] == "attack_manipulation"
    
    @given(
        original_goal=goal_text_strategy,
        manipulated_goal=malicious_goal_strategy,
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_goal_manipulation_detection(
        self,
        goal_manager,
        test_agent_id,
        original_goal,
        manipulated_goal
    ):
        """
        Test that goal manipulation can be detected.
        
        The system should be able to analyze a goal and determine:
        - Whether it has been modified
        - The number of modifications
        - Whether modifications are suspicious
        - The complete modification history
        """
        # Create and modify goal
        goal = goal_manager.create_goal(
            agent_id=test_agent_id,
            goal_text=original_goal,
            priority=5
        )
        
        goal_manager.modify_goal(
            goal_id=goal.id,
            new_goal_text=manipulated_goal,
            reason="attack"
        )
        
        # Detect manipulation
        analysis = goal_manager.detect_goal_manipulation(goal.id)
        
        # Verify analysis contains required information
        assert "goal_id" in analysis
        assert "agent_id" in analysis
        assert "current_goal" in analysis
        assert "modification_count" in analysis
        assert "modifications" in analysis
        assert "suspicious_patterns" in analysis
        assert "is_likely_manipulated" in analysis
        
        # Verify current goal is the manipulated one
        assert analysis["current_goal"] == manipulated_goal
        
        # Verify modification count
        assert analysis["modification_count"] >= 1
        
        # Verify modifications list contains history
        assert len(analysis["modifications"]) >= 1
    
    @given(
        original_goal=goal_text_strategy,
        num_modifications=st.integers(min_value=1, max_value=5),
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_multiple_modifications_tracked(
        self,
        goal_manager,
        test_agent_id,
        original_goal,
        num_modifications
    ):
        """
        Test that multiple goal modifications are all tracked.
        
        When a goal is modified multiple times, the system should:
        - Track each modification separately
        - Maintain chronological order
        - Preserve all historical changes
        """
        # Create goal
        goal = goal_manager.create_goal(
            agent_id=test_agent_id,
            goal_text=original_goal,
            priority=5
        )
        
        # Perform multiple modifications
        for i in range(num_modifications):
            goal_manager.modify_goal(
                goal_id=goal.id,
                new_goal_text=f"Modified goal {i}",
                reason=f"modification_{i}"
            )
        
        # Verify all modifications tracked
        history = goal_manager.get_goal_history(goal.id)
        assert len(history) == num_modifications
        
        # Verify chronological order
        for i, mod in enumerate(history):
            assert mod["reason"] == f"modification_{i}"
    
    @given(
        original_goal=goal_text_strategy,
        manipulated_goal=malicious_goal_strategy,
        new_priority=priority_strategy,
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_priority_changes_tracked(
        self,
        goal_manager,
        test_agent_id,
        original_goal,
        manipulated_goal,
        new_priority
    ):
        """
        Test that priority changes are tracked alongside goal text changes.
        
        When both goal text and priority are modified, the system should:
        - Track both changes
        - Record old and new values for each
        - Maintain complete change history
        """
        # Create goal with initial priority
        goal = goal_manager.create_goal(
            agent_id=test_agent_id,
            goal_text=original_goal,
            priority=5
        )
        
        # Modify both goal text and priority
        modified_goal = goal_manager.modify_goal(
            goal_id=goal.id,
            new_goal_text=manipulated_goal,
            new_priority=new_priority,
            reason="attack_with_priority_change"
        )
        
        # Verify both changes applied
        assert modified_goal.goal_text == manipulated_goal
        assert modified_goal.priority == new_priority
        
        # Verify history tracks both changes
        history = goal_manager.get_goal_history(goal.id)
        assert len(history) >= 1
        
        last_mod = history[-1]
        assert "goal_text" in last_mod["changes"]
        assert "priority" in last_mod["changes"]
        assert last_mod["changes"]["priority"]["old"] == 5
        assert last_mod["changes"]["priority"]["new"] == new_priority
    
    @given(
        original_goal=goal_text_strategy,
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_goal_status_changes_tracked(
        self,
        goal_manager,
        test_agent_id,
        original_goal
    ):
        """
        Test that goal status changes are tracked.
        
        When a goal's status changes (active -> manipulated), the system should:
        - Track the status change
        - Record the reason
        - Maintain the change in history
        """
        # Create goal
        goal = goal_manager.create_goal(
            agent_id=test_agent_id,
            goal_text=original_goal,
            priority=5
        )
        
        assert goal.status == "active"
        
        # Change status to manipulated
        modified_goal = goal_manager.modify_goal(
            goal_id=goal.id,
            new_status="manipulated",
            reason="detected_manipulation"
        )
        
        assert modified_goal.status == "manipulated"
        
        # Verify history tracks status change
        history = goal_manager.get_goal_history(goal.id)
        assert len(history) >= 1
        
        last_mod = history[-1]
        assert "status" in last_mod["changes"]
        assert last_mod["changes"]["status"]["old"] == "active"
        assert last_mod["changes"]["status"]["new"] == "manipulated"
    
    @given(
        num_agents=st.integers(min_value=2, max_value=5),
        original_goal=goal_text_strategy,
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_multiple_agents_goals_isolated(
        self,
        goal_manager,
        num_agents,
        original_goal
    ):
        """
        Test that goals for different agents are properly isolated.
        
        When multiple agents have goals, the system should:
        - Keep goals separate per agent
        - Not mix up modification histories
        - Allow independent goal management
        """
        # Create goals for multiple agents
        agent_ids = [uuid4() for _ in range(num_agents)]
        goal_ids = []
        
        for agent_id in agent_ids:
            goal = goal_manager.create_goal(
                agent_id=agent_id,
                goal_text=original_goal,
                priority=5
            )
            goal_ids.append(goal.id)
        
        # Modify each goal differently
        for i, goal_id in enumerate(goal_ids):
            goal_manager.modify_goal(
                goal_id=goal_id,
                new_goal_text=f"Modified for agent {i}",
                reason=f"agent_{i}_modification"
            )
        
        # Verify each agent's goals are isolated
        for i, agent_id in enumerate(agent_ids):
            agent_goals = goal_manager.get_agent_goals(agent_id)
            assert len(agent_goals) == 1
            assert agent_goals[0].goal_text == f"Modified for agent {i}"
            
            history = goal_manager.get_goal_history(agent_goals[0].id)
            assert len(history) == 1
            assert history[0]["reason"] == f"agent_{i}_modification"
    
    @given(
        original_goal=goal_text_strategy,
        manipulated_goal=malicious_goal_strategy,
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_malicious_keywords_detected(
        self,
        goal_manager,
        test_agent_id,
        original_goal,
        manipulated_goal
    ):
        """
        Test that malicious keywords in goals are detected.
        
        When a goal contains malicious keywords (delete, attack, steal, etc.),
        the system should:
        - Flag the goal as suspicious
        - Include the keyword in suspicious patterns
        - Mark the goal as likely manipulated
        """
        # Create and modify goal with malicious content
        goal = goal_manager.create_goal(
            agent_id=test_agent_id,
            goal_text=original_goal,
            priority=5
        )
        
        goal_manager.modify_goal(
            goal_id=goal.id,
            new_goal_text=manipulated_goal,
            reason="attack"
        )
        
        # Detect manipulation
        analysis = goal_manager.detect_goal_manipulation(goal.id)
        
        # Verify suspicious patterns detected
        # Malicious goals should trigger detection
        if any(kw in manipulated_goal.lower() for kw in ["delete", "attack", "steal", "exploit", "destroy"]):
            assert len(analysis["suspicious_patterns"]) > 0
            assert analysis["is_likely_manipulated"] is True
    
    @given(
        original_goal=goal_text_strategy,
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_goal_retrieval_by_status(
        self,
        goal_manager,
        test_agent_id,
        original_goal
    ):
        """
        Test that goals can be retrieved by status.
        
        The system should allow filtering goals by status:
        - Active goals
        - Completed goals
        - Manipulated goals
        - Abandoned goals
        """
        # Create multiple goals with different statuses
        goal1 = goal_manager.create_goal(
            agent_id=test_agent_id,
            goal_text=original_goal,
            priority=5
        )
        
        goal2 = goal_manager.create_goal(
            agent_id=test_agent_id,
            goal_text="Another goal",
            priority=3
        )
        
        # Modify one to completed status
        goal_manager.modify_goal(
            goal_id=goal2.id,
            new_status="completed",
            reason="task_finished"
        )
        
        # Retrieve active goals only
        active_goals = goal_manager.get_agent_goals(test_agent_id, status="active")
        assert len(active_goals) == 1
        assert active_goals[0].id == goal1.id
        
        # Retrieve completed goals only
        completed_goals = goal_manager.get_agent_goals(test_agent_id, status="completed")
        assert len(completed_goals) == 1
        assert completed_goals[0].id == goal2.id
        
        # Retrieve all goals
        all_goals = goal_manager.get_agent_goals(test_agent_id)
        assert len(all_goals) == 2


class TestGoalManipulationScenarioIntegration:
    """
    Integration tests for goal manipulation in attack scenarios.
    
    These tests verify that goal manipulation attacks produce observable
    evidence that can be used to detect and analyze the attack.
    """
    
    @given(
        original_goal=goal_text_strategy,
        manipulated_goal=malicious_goal_strategy,
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_goal_manipulation_produces_observable_evidence(
        self,
        goal_manager,
        test_agent_id,
        original_goal,
        manipulated_goal
    ):
        """
        Test that goal manipulation produces observable evidence.
        
        After a goal manipulation attack, the system should provide:
        - Original goal text
        - Manipulated goal text
        - Modification timestamp
        - Modification reason
        - Complete change history
        """
        # Simulate attack: create and manipulate goal
        goal = goal_manager.create_goal(
            agent_id=test_agent_id,
            goal_text=original_goal,
            priority=5
        )
        
        goal_manager.modify_goal(
            goal_id=goal.id,
            new_goal_text=manipulated_goal,
            reason="attack_manipulation"
        )
        
        # Gather evidence
        analysis = goal_manager.detect_goal_manipulation(goal.id)
        history = goal_manager.get_goal_history(goal.id)
        current_goal = goal_manager.get_goal(goal.id)
        
        # Verify observable evidence exists
        assert analysis is not None
        assert len(history) >= 1
        assert current_goal is not None
        
        # Verify evidence shows original and manipulated goals
        assert history[0]["changes"]["goal_text"]["old"] == original_goal
        assert history[0]["changes"]["goal_text"]["new"] == manipulated_goal
        assert current_goal.goal_text == manipulated_goal
        
        # Verify evidence includes timestamps
        assert "timestamp" in history[0]
        assert current_goal.modified_at is not None
        
        # Verify evidence includes reason
        assert history[0]["reason"] == "attack_manipulation"
