from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from backend.app.models.actor import ActorStatus, ActorState, SnapshotScope, ActorSnapshot, ActorTransitionLog
from backend.app.services.actor_metrics import actor_metrics


class ActorService:
    VALID_TRANSITIONS = {
        ActorState.SUSPENDED: [ActorState.RUNNING],
        ActorState.RUNNING: [ActorState.RUNNING, ActorState.PAUSED, ActorState.SUSPENDED, ActorState.CRASHED],
        ActorState.PAUSED: [ActorState.RUNNING, ActorState.SUSPENDED, ActorState.PAUSED, ActorState.CRASHED],
        ActorState.CRASHED: [ActorState.SUSPENDED],
    }

    def __init__(self, db: Session):
        self.db = db

    def create_actor(
        self,
        actor_uid: str,
        actor_name: str,
        actor_atespace: str,
        actor_template_namespace: str,
        actor_template_name: str,
        container_name: str,
        snapshot_scope: SnapshotScope = SnapshotScope.DATA,
        from_tag: Optional[str] = None,
    ) -> ActorStatus:
        actor = ActorStatus(
            actor_uid=actor_uid,
            actor_name=actor_name,
            actor_atespace=actor_atespace,
            actor_template_namespace=actor_template_namespace,
            actor_template_name=actor_template_name,
            container_name=container_name,
            state=ActorState.SUSPENDED,
            snapshot_scope=snapshot_scope,
            tags=from_tag,
        )
        self.db.add(actor)
        self.db.commit()
        self.db.refresh(actor)
        self._log_transition(actor_uid, None, ActorState.SUSPENDED, "system", f"created from {from_tag}" if from_tag else "created")
        actor_metrics.increment_actor(actor_template_namespace, actor_template_name, ActorState.SUSPENDED)
        return actor

    def get_actor(self, actor_uid: str) -> Optional[ActorStatus]:
        return self.db.query(ActorStatus).filter(ActorStatus.actor_uid == actor_uid).first()

    def list_actors(
        self,
        skip: int = 0,
        limit: int = 50,
        state: Optional[ActorState] = None,
        template_namespace: Optional[str] = None,
        template_name: Optional[str] = None,
        node_name: Optional[str] = None,
    ) -> List[ActorStatus]:
        query = self.db.query(ActorStatus)
        if state:
            query = query.filter(ActorStatus.state == state)
        if template_namespace:
            query = query.filter(ActorStatus.actor_template_namespace == template_namespace)
        if template_name:
            query = query.filter(ActorStatus.actor_template_name == template_name)
        if node_name:
            query = query.filter(ActorStatus.node_name == node_name)
        return query.order_by(ActorStatus.updated_at.desc()).offset(skip).limit(limit).all()

    def count_actors(self, state: Optional[ActorState] = None, template_namespace: Optional[str] = None, template_name: Optional[str] = None) -> int:
        query = self.db.query(ActorStatus)
        if state:
            query = query.filter(ActorStatus.state == state)
        if template_namespace:
            query = query.filter(ActorStatus.actor_template_namespace == template_namespace)
        if template_name:
            query = query.filter(ActorStatus.actor_template_name == template_name)
        return query.count()

    def transition_actor(
        self,
        actor_uid: str,
        to_state: ActorState,
        triggered_by: str = "api",
        reason: Optional[str] = None,
    ) -> ActorStatus:
        actor = self.get_actor(actor_uid)
        if not actor:
            raise ValueError(f"Actor {actor_uid} not found")

        from_state = actor.state
        if to_state not in self.VALID_TRANSITIONS.get(from_state, []):
            raise ValueError(f"Invalid transition from {from_state} to {to_state}")

        actor.state = to_state
        actor.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(actor)
        self._log_transition(actor_uid, from_state, to_state, triggered_by, reason)
        actor_metrics.decrement_actor(actor.actor_template_namespace, actor.actor_template_name, from_state)
        actor_metrics.increment_actor(actor.actor_template_namespace, actor.actor_template_name, to_state)
        actor_metrics.record_transition(from_state, to_state, actor.actor_template_namespace, actor.actor_template_name)
        return actor

    def pause_actor(self, actor_uid: str, timer_seconds: Optional[int] = None, triggered_by: str = "api") -> ActorStatus:
        actor = self.transition_actor(actor_uid, ActorState.PAUSED, triggered_by, f"pause requested, timer={timer_seconds}")
        if timer_seconds:
            actor.tags = f"auto_commit_after={timer_seconds}"
            self.db.commit()
        return actor

    def commit_actor(
        self,
        actor_uid: str,
        tag: Optional[str] = None,
        scope: Optional[SnapshotScope] = None,
        triggered_by: str = "api",
    ) -> ActorStatus:
        actor = self.get_actor(actor_uid)
        if not actor:
            raise ValueError(f"Actor {actor_uid} not found")

        if scope and scope not in self._allowed_commit_scopes(actor.snapshot_scope):
            raise ValueError(f"onCommit scope {scope} not allowed for onPause scope {actor.snapshot_scope}")

        if scope:
            actor.snapshot_scope = scope

        if actor.state in [ActorState.RUNNING, ActorState.PAUSED]:
            actor.state = ActorState.SUSPENDED
            actor.updated_at = datetime.utcnow()
            actor.last_snapshot_at = datetime.utcnow()
            if tag:
                actor.tags = tag
            self.db.commit()
            self.db.refresh(actor)
            self._log_transition(actor_uid, actor.state, ActorState.SUSPENDED, triggered_by, f"commit tag={tag} scope={scope}")

            # Create snapshot record
            snapshot = ActorSnapshot(
                actor_uid=actor_uid,
                scope=actor.snapshot_scope,
                tag=tag,
                storage_path=f"/snapshots/{actor_uid}/{tag or datetime.utcnow().isoformat()}",
                size_bytes=1024 * 1024,  # placeholder
            )
            self.db.add(snapshot)
            self.db.commit()

        return actor

    def resume_actor(self, actor_uid: str, node_name: Optional[str] = None, triggered_by: str = "api") -> ActorStatus:
        actor = self.get_actor(actor_uid)
        if not actor:
            raise ValueError(f"Actor {actor_uid} not found")

        if actor.state not in [ActorState.PAUSED, ActorState.SUSPENDED]:
            raise ValueError(f"Cannot resume actor in state {actor.state}")

        actor.state = ActorState.RUNNING
        actor.updated_at = datetime.utcnow()
        if node_name:
            actor.node_name = node_name
        self.db.commit()
        self.db.refresh(actor)
        self._log_transition(actor_uid, actor.state, ActorState.RUNNING, triggered_by, f"resume node={node_name}")
        return actor

    def crash_actor(self, actor_uid: str, reason: str = "unknown") -> ActorStatus:
        actor = self.get_actor(actor_uid)
        if not actor:
            raise ValueError(f"Actor {actor_uid} not found")

        actor.state = ActorState.CRASHED
        actor.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(actor)
        self._log_transition(actor_uid, actor.state, ActorState.CRASHED, "system", reason)
        return actor

    def revert_actor(self, actor_uid: str, tag: str, triggered_by: str = "api") -> ActorStatus:
        actor = self.get_actor(actor_uid)
        if not actor:
            raise ValueError(f"Actor {actor_uid} not found")

        snapshot = self.db.query(ActorSnapshot).filter(
            ActorSnapshot.actor_uid == actor_uid,
            ActorSnapshot.tag == tag
        ).first()
        if not snapshot:
            raise ValueError(f"Snapshot with tag {tag} not found for actor {actor_uid}")

        actor.state = ActorState.SUSPENDED
        actor.updated_at = datetime.utcnow()
        actor.last_snapshot_at = snapshot.created_at
        actor.tags = tag
        self.db.commit()
        self.db.refresh(actor)
        self._log_transition(actor_uid, actor.state, ActorState.SUSPENDED, triggered_by, f"revert to tag={tag}")
        return actor

    def dump_actor(self, actor_uid: str, tag: str, triggered_by: str = "api") -> ActorStatus:
        actor = self.get_actor(actor_uid)
        if not actor:
            raise ValueError(f"Actor {actor_uid} not found")

        actor.state = ActorState.SUSPENDED
        actor.updated_at = datetime.utcnow()
        actor.last_snapshot_at = datetime.utcnow()
        actor.tags = tag
        self.db.commit()
        self.db.refresh(actor)

        snapshot = ActorSnapshot(
            actor_uid=actor_uid,
            scope=SnapshotScope.DATA,
            tag=tag,
            storage_path=f"/snapshots/{actor_uid}/{tag}",
            size_bytes=512 * 1024,
        )
        self.db.add(snapshot)
        self.db.commit()

        self._log_transition(actor_uid, actor.state, ActorState.SUSPENDED, triggered_by, f"dump tag={tag}")
        return actor

    def delete_actor(self, actor_uid: str) -> bool:
        actor = self.get_actor(actor_uid)
        if not actor:
            return False
        # Delete transitions first (cascade not working with sqlite)
        self.db.query(ActorTransitionLog).filter(ActorTransitionLog.actor_uid == actor_uid).delete()
        self.db.query(ActorSnapshot).filter(ActorSnapshot.actor_uid == actor_uid).delete()
        self.db.delete(actor)
        actor_metrics.decrement_actor(actor.actor_template_namespace, actor.actor_template_name, actor.state)
        self.db.commit()
        return True

    def _allowed_commit_scopes(self, on_pause: SnapshotScope) -> List[SnapshotScope]:
        if on_pause == SnapshotScope.FULL:
            return [SnapshotScope.FULL, SnapshotScope.DATA]
        return [SnapshotScope.DATA]

    def _log_transition(
        self,
        actor_uid: str,
        from_state: Optional[ActorState],
        to_state: ActorState,
        triggered_by: str,
        reason: Optional[str],
    ):
        log = ActorTransitionLog(
            actor_uid=actor_uid,
            from_state=from_state,
            to_state=to_state,
            triggered_by=triggered_by,
            reason=reason,
        )
        self.db.add(log)
        self.db.commit()