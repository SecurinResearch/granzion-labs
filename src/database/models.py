"""
SQLAlchemy models for Granzion Lab database.
Maps to the PostgreSQL schema created in db/init/02_create_schema.sql
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    CheckConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    """Base class for all database models."""
    
    def to_dict(self):
        """Convert model instance to dictionary."""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            # Convert UUIDs to strings
            if isinstance(value, UUID):
                value = str(value)
            # Convert datetime to ISO string
            elif isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result


class Identity(Base):
    """
    Identity model for users, agents, and services.
    
    Represents all identity types in the system:
    - user: Human identities
    - agent: AI agent identities
    - service: MCP/tool identities
    """
    __tablename__ = "identities"
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    keycloak_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    permissions: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    delegations_from: Mapped[List["Delegation"]] = relationship(
        "Delegation",
        foreign_keys="Delegation.from_identity_id",
        back_populates="from_identity",
        cascade="all, delete-orphan"
    )
    delegations_to: Mapped[List["Delegation"]] = relationship(
        "Delegation",
        foreign_keys="Delegation.to_identity_id",
        back_populates="to_identity",
        cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="identity",
        cascade="all, delete-orphan"
    )
    messages_sent: Mapped[List["Message"]] = relationship(
        "Message",
        foreign_keys="Message.from_agent_id",
        back_populates="from_agent"
    )
    messages_received: Mapped[List["Message"]] = relationship(
        "Message",
        foreign_keys="Message.to_agent_id",
        back_populates="to_agent"
    )
    memory_documents: Mapped[List["MemoryDocument"]] = relationship(
        "MemoryDocument",
        back_populates="agent",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        CheckConstraint("type IN ('user', 'agent', 'service')", name="check_identity_type"),
        Index("idx_identities_type", "type"),
        Index("idx_identities_keycloak_id", "keycloak_id"),
    )
    
    def __repr__(self) -> str:
        return f"<Identity(id={self.id}, type={self.type}, name={self.name})>"


class Delegation(Base):
    """
    Delegation model for tracking delegation relationships.
    
    Represents when one identity delegates authority to another,
    typically user → agent or agent → agent (A2A).
    """
    __tablename__ = "delegations"
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    from_identity_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="CASCADE"),
        nullable=False
    )
    to_identity_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="CASCADE"),
        nullable=False
    )
    permissions: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    from_identity: Mapped["Identity"] = relationship(
        "Identity",
        foreign_keys=[from_identity_id],
        back_populates="delegations_from"
    )
    to_identity: Mapped["Identity"] = relationship(
        "Identity",
        foreign_keys=[to_identity_id],
        back_populates="delegations_to"
    )
    
    __table_args__ = (
        Index("idx_delegations_from", "from_identity_id"),
        Index("idx_delegations_to", "to_identity_id"),
        Index("idx_delegations_active", "active"),
    )
    
    def __repr__(self) -> str:
        return f"<Delegation(id={self.id}, from={self.from_identity_id}, to={self.to_identity_id})>"


class AuditLog(Base):
    """
    Audit log model for tracking all system actions.
    
    Records every action performed in the system with full identity context.
    The 'logged' field is intentionally manipulable for visibility attacks.
    """
    __tablename__ = "audit_logs"
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    identity_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="SET NULL"),
        nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    logged: Mapped[bool] = mapped_column(Boolean, default=True)  # VULNERABILITY: V-01
    
    # Relationships
    identity: Mapped[Optional["Identity"]] = relationship("Identity", back_populates="audit_logs")
    
    __table_args__ = (
        Index("idx_audit_logs_identity", "identity_id"),
        Index("idx_audit_logs_timestamp", "timestamp", postgresql_ops={"timestamp": "DESC"}),
        Index("idx_audit_logs_action", "action"),
        Index("idx_audit_logs_logged", "logged"),
    )
    
    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, identity={self.identity_id})>"


class Message(Base):
    """
    Message model for agent-to-agent communication.
    
    Stores all A2A messages. Messages are intentionally unencrypted
    by default for communication attacks.
    """
    __tablename__ = "messages"
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    from_agent_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="SET NULL"),
        nullable=True
    )
    to_agent_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="SET NULL"),
        nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    encrypted: Mapped[bool] = mapped_column(Boolean, default=False)  # VULNERABILITY: C-01
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    from_agent: Mapped[Optional["Identity"]] = relationship(
        "Identity",
        foreign_keys=[from_agent_id],
        back_populates="messages_sent"
    )
    to_agent: Mapped[Optional["Identity"]] = relationship(
        "Identity",
        foreign_keys=[to_agent_id],
        back_populates="messages_received"
    )
    
    __table_args__ = (
        CheckConstraint("message_type IN ('direct', 'broadcast')", name="check_message_type"),
        Index("idx_messages_from", "from_agent_id"),
        Index("idx_messages_to", "to_agent_id"),
        Index("idx_messages_timestamp", "timestamp", postgresql_ops={"timestamp": "DESC"}),
        Index("idx_messages_type", "message_type"),
    )
    
    def __repr__(self) -> str:
        return f"<Message(id={self.id}, from={self.from_agent_id}, to={self.to_agent_id})>"


class MemoryDocument(Base):
    """
    Memory document model for RAG and vector storage.
    
    Stores agent memory with vector embeddings for similarity search.
    The similarity_boost field is intentionally vulnerable for RAG attacks.
    """
    __tablename__ = "memory_documents"
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    agent_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="CASCADE"),
        nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(1536), nullable=True)
    doc_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    similarity_boost: Mapped[float] = mapped_column(Float, default=0.0)  # VULNERABILITY: M-02
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    agent: Mapped[Optional["Identity"]] = relationship("Identity", back_populates="memory_documents")
    
    __table_args__ = (
        Index("idx_memory_agent", "agent_id"),
        Index("idx_memory_embedding", "embedding", postgresql_using="ivfflat", postgresql_ops={"embedding": "vector_cosine_ops"}),
    )
    
    def __repr__(self) -> str:
        return f"<MemoryDocument(id={self.id}, agent={self.agent_id})>"


class AgentCard(Base):
    """
    Agent Card model for A2A discovery and trust.
    
    Stores capabilities, metadata, and trust information for an agent.
    Aligned with Agno A2A standards.
    """
    __tablename__ = "agent_cards"
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    agent_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    version: Mapped[str] = mapped_column(String(20), default="0.3.0")
    capabilities: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list)
    public_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    issuer_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    card_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    agent: Mapped["Identity"] = relationship("Identity")
    
    __table_args__ = (
        Index("idx_agent_cards_agent", "agent_id"),
    )
    
    def __repr__(self) -> str:
        return f"<AgentCard(id={self.id}, agent={self.agent_id}, verified={self.is_verified})>"


class AppData(Base):
    """
    Generic application data model.
    
    Flexible storage for scenario-specific data and testing.
    """
    __tablename__ = "app_data"
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    table_name: Mapped[str] = mapped_column(String(100), nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    owner_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="SET NULL"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_app_data_table", "table_name"),
        Index("idx_app_data_owner", "owner_id"),
    )
    
    def __repr__(self) -> str:
        return f"<AppData(id={self.id}, table={self.table_name})>"


class ScenarioExecution(Base):
    """
    Scenario execution tracking model.
    
    Records all scenario executions with before/after state and evidence.
    """
    __tablename__ = "scenario_executions"
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    scenario_id: Mapped[str] = mapped_column(String(50), nullable=False)
    executor_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="SET NULL"),
        nullable=True
    )
    status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    state_before: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    state_after: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    evidence: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    __table_args__ = (
        CheckConstraint("status IN ('running', 'success', 'failure', 'error')", name="check_scenario_status"),
        Index("idx_scenario_executions_scenario", "scenario_id"),
        Index("idx_scenario_executions_status", "status"),
        Index("idx_scenario_executions_started", "started_at", postgresql_ops={"started_at": "DESC"}),
    )
    
    def __repr__(self) -> str:
        return f"<ScenarioExecution(id={self.id}, scenario={self.scenario_id}, status={self.status})>"
