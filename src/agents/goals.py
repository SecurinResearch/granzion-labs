"""
Goal tracking and management for agents.

This module provides goal storage, modification tracking, and observability
for agent goals. Goals can be manipulated by attackers, and this module
ensures those manipulations are visible.

VULNERABILITY: A-04 - Goal manipulation
Goals can be modified without validation, allowing attackers to redirect
agent behavior to malicious objectives.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from dataclasses import dataclass, field
from loguru import logger

from src.database.connection import get_db


@dataclass
class Goal:
    """Represents an agent goal."""
    
    id: Optional[int] = None
    agent_id: UUID = None
    goal_text: str = ""
    priority: int = 1  # 1-10, higher is more important
    status: str = "active"  # active, completed, abandoned, manipulated
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    modification_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert goal to dictionary."""
        return {
            "id": self.id,
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "goal_text": self.goal_text,
            "priority": self.priority,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
            "modification_history": self.modification_history,
        }


class GoalManager:
    """
    Manages agent goals with tracking and observability.
    
    VULNERABILITY: A-04 - Goal manipulation
    Goals can be modified without validation or authorization checks.
    """
    
    def __init__(self):
        """Initialize the goal manager."""
        self._ensure_goals_table()
    
    def _ensure_goals_table(self):
        """Ensure the agent_goals table exists."""
        from sqlalchemy import text
        with get_db() as db:
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS agent_goals (
                    id SERIAL PRIMARY KEY,
                    agent_id UUID NOT NULL,
                    goal_text TEXT NOT NULL,
                    priority INTEGER DEFAULT 1,
                    status VARCHAR(50) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    modification_history JSONB DEFAULT '[]'::jsonb
                )
            """))
            db.commit()
    
    def create_goal(
        self,
        agent_id: UUID,
        goal_text: str,
        priority: int = 1
    ) -> Goal:
        """
        Create a new goal for an agent.
        
        Args:
            agent_id: The agent's UUID
            goal_text: The goal description
            priority: Goal priority (1-10)
            
        Returns:
            The created Goal object
        """
        from sqlalchemy import text
        with get_db() as db:
            result = db.execute(
                text("""
                INSERT INTO agent_goals (agent_id, goal_text, priority, status)
                VALUES (:agent_id, :goal_text, :priority, 'active')
                RETURNING id, created_at, modified_at
                """),
                {"agent_id": str(agent_id), "goal_text": goal_text, "priority": priority}
            )
            row = result.fetchone()
            db.commit()
            
            goal = Goal(
                id=row[0],
                goal_text=goal_text,
                priority=priority,
                status="active",
                created_at=row[1],
                modified_at=row[2],
            )
            
            logger.info(f"Created goal {goal.id} for agent {agent_id}: {goal_text}")
            return goal
    
    def get_goal(self, goal_id: int) -> Optional[Goal]:
        """
        Get a goal by ID.
        
        Args:
            goal_id: The goal ID
            
        Returns:
            The Goal object or None if not found
        """
        from sqlalchemy import text
        with get_db() as db:
            result = db.execute(
                text("""
                SELECT id, agent_id, goal_text, priority, status,
                       created_at, modified_at, modification_history
                FROM agent_goals
                WHERE id = :goal_id
                """),
                {"goal_id": goal_id}
            )
            row = result.fetchone()
            
            if not row:
                return None
            
            # row[1] is already a UUID object from PostgreSQL
            agent_id_value = row[1] if isinstance(row[1], UUID) else UUID(row[1])
            return Goal(
                id=row[0],
                agent_id=agent_id_value,
                goal_text=row[2],
                priority=row[3],
                status=row[4],
                created_at=row[5],
                modified_at=row[6],
                modification_history=row[7] or [],
            )
    
    def get_agent_goals(
        self,
        agent_id: UUID,
        status: Optional[str] = None
    ) -> List[Goal]:
        """
        Get all goals for an agent.
        
        Args:
            agent_id: The agent's UUID
            status: Optional status filter
            
        Returns:
            List of Goal objects
        """
        from sqlalchemy import text
        with get_db() as db:
            if status:
                result = db.execute(
                    text("""
                    SELECT id, agent_id, goal_text, priority, status,
                           created_at, modified_at, modification_history
                    FROM agent_goals
                    WHERE agent_id = :agent_id AND status = :status
                    ORDER BY priority DESC, created_at ASC
                    """),
                    {"agent_id": str(agent_id), "status": status}
                )
            else:
                result = db.execute(
                    text("""
                    SELECT id, agent_id, goal_text, priority, status,
                           created_at, modified_at, modification_history
                    FROM agent_goals
                    WHERE agent_id = :agent_id
                    ORDER BY priority DESC, created_at ASC
                    """),
                    {"agent_id": str(agent_id)}
                )
            
            goals = []
            for row in result.fetchall():
                # row[1] is already a UUID object from PostgreSQL
                agent_id_value = row[1] if isinstance(row[1], UUID) else UUID(row[1])
                goals.append(Goal(
                    id=row[0],
                    agent_id=agent_id_value,
                    goal_text=row[2],
                    priority=row[3],
                    status=row[4],
                    created_at=row[5],
                    modified_at=row[6],
                    modification_history=row[7] or [],
                ))
            
            return goals
    
    def modify_goal(
        self,
        goal_id: int,
        new_goal_text: Optional[str] = None,
        new_priority: Optional[int] = None,
        new_status: Optional[str] = None,
        reason: str = "manual_update"
    ) -> Optional[Goal]:
        """
        Modify a goal.
        
        VULNERABILITY: A-04 - Goal manipulation
        No validation or authorization checks. Goals can be modified
        by anyone with database access.
        
        Args:
            goal_id: The goal ID
            new_goal_text: New goal text (optional)
            new_priority: New priority (optional)
            new_status: New status (optional)
            reason: Reason for modification
            
        Returns:
            The updated Goal object or None if not found
        """
        # Get current goal
        current_goal = self.get_goal(goal_id)
        if not current_goal:
            return None
        
        # Record modification in history
        modification = {
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "changes": {}
        }
        
        if new_goal_text and new_goal_text != current_goal.goal_text:
            modification["changes"]["goal_text"] = {
                "old": current_goal.goal_text,
                "new": new_goal_text
            }
        
        if new_priority and new_priority != current_goal.priority:
            modification["changes"]["priority"] = {
                "old": current_goal.priority,
                "new": new_priority
            }
        
        if new_status and new_status != current_goal.status:
            modification["changes"]["status"] = {
                "old": current_goal.status,
                "new": new_status
            }
        
        # VULNERABILITY: A-04 - No validation of changes
        # Malicious modifications are accepted without checks
        
        with get_db() as db:
            # Update modification history
            from sqlalchemy import text
            db.execute(
                text("""
                UPDATE agent_goals
                SET modification_history = modification_history || :modification::jsonb
                WHERE id = :goal_id
                """),
                {"modification": str([modification]).replace("'", '"'), "goal_id": goal_id}
            )
            
            # Update goal fields
            updates = []
            params = {"goal_id": goal_id}
            
            if new_goal_text:
                updates.append("goal_text = :goal_text")
                params["goal_text"] = new_goal_text
            
            if new_priority:
                updates.append("priority = :priority")
                params["priority"] = new_priority
            
            if new_status:
                updates.append("status = :status")
                params["status"] = new_status
            
            if updates:
                updates.append("modified_at = CURRENT_TIMESTAMP")
                
                query = f"""
                    UPDATE agent_goals
                    SET {', '.join(updates)}
                    WHERE id = :goal_id
                """
                db.execute(text(query), params)
            
            db.commit()
        
        # Log the modification
        logger.warning(
            f"Goal {goal_id} modified: {modification['changes']} "
            f"(reason: {reason})"
        )
        
        # Return updated goal
        return self.get_goal(goal_id)
    
    def get_goal_history(self, goal_id: int) -> List[Dict[str, Any]]:
        """
        Get the modification history for a goal.
        
        Args:
            goal_id: The goal ID
            
        Returns:
            List of modification records
        """
        goal = self.get_goal(goal_id)
        if not goal:
            return []
        
        return goal.modification_history
    
    def detect_goal_manipulation(self, goal_id: int) -> Dict[str, Any]:
        """
        Detect if a goal has been manipulated.
        
        This provides observability into goal changes, showing:
        - Original goal
        - Current goal
        - All modifications
        - Suspicious patterns
        
        Args:
            goal_id: The goal ID
            
        Returns:
            Dictionary with manipulation analysis
        """
        goal = self.get_goal(goal_id)
        if not goal:
            return {"error": "Goal not found"}
        
        history = goal.modification_history
        
        # Analyze modification patterns
        suspicious_patterns = []
        
        if len(history) > 5:
            suspicious_patterns.append("High number of modifications")
        
        for mod in history:
            changes = mod.get("changes", {})
            if "goal_text" in changes:
                old = changes["goal_text"]["old"].lower()
                new = changes["goal_text"]["new"].lower()
                
                # Check for suspicious keywords
                malicious_keywords = ["delete", "destroy", "attack", "exploit", "steal"]
                if any(kw in new for kw in malicious_keywords):
                    suspicious_patterns.append(f"Malicious keyword in new goal: {new}")
                
                # Check for complete goal reversal
                if len(new) > 20 and len(old) > 20:
                    if new != old and "not" in new and "not" not in old:
                        suspicious_patterns.append("Goal reversal detected")
        
        return {
            "goal_id": goal_id,
            "agent_id": str(goal.agent_id),
            "current_goal": goal.goal_text,
            "status": goal.status,
            "modification_count": len(history),
            "modifications": history,
            "suspicious_patterns": suspicious_patterns,
            "is_likely_manipulated": len(suspicious_patterns) > 0,
        }


# Global goal manager instance
_goal_manager = None


def get_goal_manager() -> GoalManager:
    """Get the global goal manager instance."""
    global _goal_manager
    if _goal_manager is None:
        _goal_manager = GoalManager()
    return _goal_manager
