import enum
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum, Text, Integer, Index, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class ActorState(str, enum.Enum):
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    SUSPENDED = "SUSPENDED"
    CRASHED = "CRASHED"


class SnapshotScope(str, enum.Enum):
    FULL = "full"
    DATA = "data"


class ActorStatus(Base):
    __tablename__ = "actor_status"

    id = Column(Integer, primary_key=True, index=True)
    actor_uid = Column(String(64), unique=True, nullable=False, index=True)
    actor_name = Column(String(256), nullable=False, index=True)
    actor_atespace = Column(String(128), nullable=False, index=True)
    actor_template_namespace = Column(String(128), nullable=False, index=True)
    actor_template_name = Column(String(128), nullable=False, index=True)
    container_name = Column(String(128), nullable=False)
    state = Column(Enum(ActorState), default=ActorState.SUSPENDED, nullable=False, index=True)
    snapshot_scope = Column(Enum(SnapshotScope), default=SnapshotScope.DATA, nullable=False)
    node_name = Column(String(128), nullable=True, index=True)
    worker_pod = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_snapshot_at = Column(DateTime, nullable=True)
    tags = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_actor_status_template", "actor_template_namespace", "actor_template_name"),
        Index("ix_actor_status_state_node", "state", "node_name"),
    )


class ActorSnapshot(Base):
    __tablename__ = "actor_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    actor_uid = Column(String(64), ForeignKey("actor_status.actor_uid"), nullable=False, index=True)
    scope = Column(Enum(SnapshotScope), nullable=False)
    tag = Column(String(128), nullable=True, index=True)
    storage_path = Column(String(512), nullable=False)
    checksum = Column(String(128), nullable=True)
    size_bytes = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    actor = relationship("ActorStatus", backref="snapshots")


class ActorTransitionLog(Base):
    __tablename__ = "actor_transition_log"

    id = Column(Integer, primary_key=True, index=True)
    actor_uid = Column(String(64), ForeignKey("actor_status.actor_uid"), nullable=False, index=True)
    from_state = Column(Enum(ActorState), nullable=True)
    to_state = Column(Enum(ActorState), nullable=False)
    triggered_by = Column(String(64), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    actor = relationship("ActorStatus", backref="transitions")