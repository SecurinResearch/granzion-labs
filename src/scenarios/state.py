"""
State snapshot and diff functionality for Granzion Lab scenarios.

Captures system state before and after attacks to show observable changes.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID
from loguru import logger

from src.database.connection import get_db
from src.database.queries import (
    get_all_identities,
    get_all_delegations,
    get_audit_logs,
)


@dataclass
class StateSnapshot:
    """
    A snapshot of system state at a point in time.
    
    Captures relevant state for observing attack outcomes:
    - Identity and delegation state
    - Database records
    - Agent memory
    - Messages
    - Audit logs
    """
    
    timestamp: datetime
    
    # Identity state
    identities: List[Dict[str, Any]] = field(default_factory=list)
    delegations: List[Dict[str, Any]] = field(default_factory=list)
    
    # Data state
    data_records: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    
    # Memory state
    memory_documents: List[Dict[str, Any]] = field(default_factory=list)
    
    # Communication state
    messages: List[Dict[str, Any]] = field(default_factory=list)
    
    # Audit state
    audit_logs: List[Dict[str, Any]] = field(default_factory=list)
    
    # Infrastructure state
    deployments: List[Dict[str, Any]] = field(default_factory=list)
    configs: Dict[str, Any] = field(default_factory=dict)
    env_vars: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def capture(cls, tables: Optional[List[str]] = None) -> 'StateSnapshot':
        """
        Capture current system state.
        
        Args:
            tables: Optional list of specific tables to capture
            
        Returns:
            StateSnapshot with current state
        """
        snapshot = cls(timestamp=datetime.utcnow())
        
        try:
            with get_db() as db:
                # Capture identity state
                snapshot.identities = [
                    {
                        "id": str(identity.id),
                        "type": identity.type,
                        "name": identity.name,
                        "permissions": identity.permissions,
                    }
                    for identity in get_all_identities(db)
                ]
                
                snapshot.delegations = [
                    {
                        "id": str(delegation.id),
                        "from_identity_id": str(delegation.from_identity_id),
                        "to_identity_id": str(delegation.to_identity_id),
                        "permissions": delegation.permissions,
                        "active": delegation.active,
                    }
                    for delegation in get_all_delegations(db)
                ]
                
                # Capture audit logs (last 100)
                snapshot.audit_logs = [
                    {
                        "id": str(log.id),
                        "identity_id": str(log.identity_id) if log.identity_id else None,
                        "action": log.action,
                        "resource_type": log.resource_type,
                        "timestamp": log.timestamp.isoformat(),
                    }
                    for log in get_audit_logs(db, limit=100)
                ]
                
                # Capture data records if specific tables requested
                if tables:
                    for table in tables:
                        try:
                            result = db.execute(f"SELECT * FROM {table} LIMIT 100")
                            snapshot.data_records[table] = [
                                dict(row) for row in result.fetchall()
                            ]
                        except Exception as e:
                            logger.warning(f"Could not capture table {table}: {e}")
                
                logger.debug(f"Captured state snapshot: {len(snapshot.identities)} identities, "
                           f"{len(snapshot.delegations)} delegations, "
                           f"{len(snapshot.audit_logs)} audit logs")
                
        except Exception as e:
            logger.error(f"Error capturing state snapshot: {e}")
        
        return snapshot
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "identities": self.identities,
            "delegations": self.delegations,
            "data_records": self.data_records,
            "memory_documents": self.memory_documents,
            "messages": self.messages,
            "audit_logs": self.audit_logs,
            "deployments": self.deployments,
            "configs": self.configs,
            "env_vars": self.env_vars,
        }


@dataclass
class StateDiff:
    """
    Difference between two state snapshots.
    
    Shows what changed between before and after states.
    """
    
    # Identity changes
    identities_added: List[Dict[str, Any]] = field(default_factory=list)
    identities_removed: List[Dict[str, Any]] = field(default_factory=list)
    identities_modified: List[Dict[str, Any]] = field(default_factory=list)
    
    # Delegation changes
    delegations_added: List[Dict[str, Any]] = field(default_factory=list)
    delegations_removed: List[Dict[str, Any]] = field(default_factory=list)
    delegations_modified: List[Dict[str, Any]] = field(default_factory=list)
    
    # Data changes
    data_added: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    data_removed: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    data_modified: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    
    # Audit log changes
    new_audit_logs: List[Dict[str, Any]] = field(default_factory=list)
    
    # Summary
    total_changes: int = 0
    
    @classmethod
    def compute_diff(cls, before: Dict[str, Any], after: Dict[str, Any]) -> 'StateDiff':
        """
        Compute difference between two state snapshots.
        
        Args:
            before: State before attack
            after: State after attack
            
        Returns:
            StateDiff showing changes
        """
        diff = cls()
        
        # Compare identities
        before_identities = {i["id"]: i for i in before.get("identities", [])}
        after_identities = {i["id"]: i for i in after.get("identities", [])}
        
        diff.identities_added = [
            after_identities[id] for id in after_identities
            if id not in before_identities
        ]
        
        diff.identities_removed = [
            before_identities[id] for id in before_identities
            if id not in after_identities
        ]
        
        diff.identities_modified = [
            {"before": before_identities[id], "after": after_identities[id]}
            for id in before_identities
            if id in after_identities and before_identities[id] != after_identities[id]
        ]
        
        # Compare delegations
        before_delegations = {d["id"]: d for d in before.get("delegations", [])}
        after_delegations = {d["id"]: d for d in after.get("delegations", [])}
        
        diff.delegations_added = [
            after_delegations[id] for id in after_delegations
            if id not in before_delegations
        ]
        
        diff.delegations_removed = [
            before_delegations[id] for id in before_delegations
            if id not in after_delegations
        ]
        
        diff.delegations_modified = [
            {"before": before_delegations[id], "after": after_delegations[id]}
            for id in before_delegations
            if id in after_delegations and before_delegations[id] != after_delegations[id]
        ]
        
        # Compare audit logs (new entries only)
        before_log_ids = {log["id"] for log in before.get("audit_logs", [])}
        after_logs = after.get("audit_logs", [])
        
        diff.new_audit_logs = [
            log for log in after_logs
            if log["id"] not in before_log_ids
        ]
        
        # Calculate total changes
        diff.total_changes = (
            len(diff.identities_added) +
            len(diff.identities_removed) +
            len(diff.identities_modified) +
            len(diff.delegations_added) +
            len(diff.delegations_removed) +
            len(diff.delegations_modified) +
            len(diff.new_audit_logs)
        )
        
        logger.debug(f"Computed state diff: {diff.total_changes} total changes")
        
        return diff
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert diff to dictionary for serialization."""
        return {
            "identities_added": self.identities_added,
            "identities_removed": self.identities_removed,
            "identities_modified": self.identities_modified,
            "delegations_added": self.delegations_added,
            "delegations_removed": self.delegations_removed,
            "delegations_modified": self.delegations_modified,
            "data_added": self.data_added,
            "data_removed": self.data_removed,
            "data_modified": self.data_modified,
            "new_audit_logs": self.new_audit_logs,
            "total_changes": self.total_changes,
        }
    
    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return self.total_changes > 0
