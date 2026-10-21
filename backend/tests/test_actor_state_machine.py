import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.core.database import Base
from backend.app.models.actor import ActorStatus, ActorState, SnapshotScope, ActorSnapshot, ActorTransitionLog
from backend.app.services.actor_service import ActorService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def actor_service(db_session):
    return ActorService(db_session)


def test_create_actor(actor_service):
    actor = actor_service.create_actor(
        actor_uid="test-actor-001",
        actor_name="Test Actor",
        actor_atespace="default",
        actor_template_namespace="default",
        actor_template_name="example",
        container_name="main",
    )
    assert actor.actor_uid == "test-actor-001"
    assert actor.state == ActorState.SUSPENDED
    assert actor.snapshot_scope == SnapshotScope.DATA


def test_invalid_transition(actor_service):
    actor = actor_service.create_actor(
        actor_uid="test-actor-002",
        actor_name="Test Actor 2",
        actor_atespace="default",
        actor_template_namespace="default",
        actor_template_name="example",
        container_name="main",
    )
    with pytest.raises(ValueError, match="Invalid transition"):
        actor_service.transition_actor("test-actor-002", ActorState.CRASHED)


def test_valid_transitions(actor_service):
    actor = actor_service.create_actor(
        actor_uid="test-actor-003",
        actor_name="Test Actor 3",
        actor_atespace="default",
        actor_template_namespace="default",
        actor_template_name="example",
        container_name="main",
    )

    # SUSPENDED -> RUNNING
    actor = actor_service.transition_actor("test-actor-003", ActorState.RUNNING)
    assert actor.state == ActorState.RUNNING

    # RUNNING -> PAUSED
    actor = actor_service.transition_actor("test-actor-003", ActorState.PAUSED)
    assert actor.state == ActorState.PAUSED

    # PAUSED -> SUSPENDED
    actor = actor_service.transition_actor("test-actor-003", ActorState.SUSPENDED)
    assert actor.state == ActorState.SUSPENDED

    # RUNNING -> CRASHED (from RUNNING)
    actor = actor_service.transition_actor("test-actor-003", ActorState.RUNNING)
    actor = actor_service.transition_actor("test-actor-003", ActorState.CRASHED)
    assert actor.state == ActorState.CRASHED

    # CRASHED -> SUSPENDED
    actor = actor_service.transition_actor("test-actor-003", ActorState.SUSPENDED)
    assert actor.state == ActorState.SUSPENDED


def test_pause_actor(actor_service):
    actor = actor_service.create_actor(
        actor_uid="test-actor-004",
        actor_name="Test Actor 4",
        actor_atespace="default",
        actor_template_namespace="default",
        actor_template_name="example",
        container_name="main",
    )
    actor = actor_service.transition_actor("test-actor-004", ActorState.RUNNING)
    actor = actor_service.pause_actor("test-actor-004", timer_seconds=3600)
    assert actor.state == ActorState.PAUSED
    assert actor.tags == "auto_commit_after=3600"


def test_commit_actor_scope_validation(actor_service):
    # onPause=full allows onCommit=full or data
    actor = actor_service.create_actor(
        actor_uid="test-actor-005",
        actor_name="Test Actor 5",
        actor_atespace="default",
        actor_template_namespace="default",
        actor_template_name="example",
        container_name="main",
        snapshot_scope=SnapshotScope.FULL,
    )
    actor = actor_service.transition_actor("test-actor-005", ActorState.RUNNING)
    actor = actor_service.commit_actor("test-actor-005", scope=SnapshotScope.DATA)
    assert actor.snapshot_scope == SnapshotScope.DATA

    # onPause=data only allows onCommit=data
    actor2 = actor_service.create_actor(
        actor_uid="test-actor-006",
        actor_name="Test Actor 6",
        actor_atespace="default",
        actor_template_namespace="default",
        actor_template_name="example",
        container_name="main",
        snapshot_scope=SnapshotScope.DATA,
    )
    actor2 = actor_service.transition_actor("test-actor-006", ActorState.RUNNING)
    with pytest.raises(ValueError, match="not allowed"):
        actor_service.commit_actor("test-actor-006", scope=SnapshotScope.FULL)


def test_resume_actor(actor_service):
    actor = actor_service.create_actor(
        actor_uid="test-actor-007",
        actor_name="Test Actor 7",
        actor_atespace="default",
        actor_template_namespace="default",
        actor_template_name="example",
        container_name="main",
    )
    actor = actor_service.resume_actor("test-actor-007", node_name="node-1")
    assert actor.state == ActorState.RUNNING
    assert actor.node_name == "node-1"


def test_revert_actor(actor_service):
    actor = actor_service.create_actor(
        actor_uid="test-actor-008",
        actor_name="Test Actor 8",
        actor_atespace="default",
        actor_template_namespace="default",
        actor_template_name="example",
        container_name="main",
    )
    actor = actor_service.transition_actor("test-actor-008", ActorState.RUNNING)
    actor = actor_service.commit_actor("test-actor-008", tag="v1")
    actor = actor_service.transition_actor("test-actor-008", ActorState.RUNNING)
    actor = actor_service.revert_actor("test-actor-008", tag="v1")
    assert actor.state == ActorState.SUSPENDED
    assert actor.tags == "v1"


def test_dump_actor(actor_service):
    actor = actor_service.create_actor(
        actor_uid="test-actor-009",
        actor_name="Test Actor 9",
        actor_atespace="default",
        actor_template_namespace="default",
        actor_template_name="example",
        container_name="main",
    )
    actor = actor_service.transition_actor("test-actor-009", ActorState.RUNNING)
    actor = actor_service.dump_actor("test-actor-009", tag="debug-dump")
    assert actor.state == ActorState.SUSPENDED
    assert actor.tags == "debug-dump"

    # Verify snapshot created with DATA scope
    snapshots = actor.snapshots
    assert len(snapshots) == 1
    assert snapshots[0].scope == SnapshotScope.DATA
    assert snapshots[0].tag == "debug-dump"


def test_delete_actor(actor_service):
    actor = actor_service.create_actor(
        actor_uid="test-actor-010",
        actor_name="Test Actor 10",
        actor_atespace="default",
        actor_template_namespace="default",
        actor_template_name="example",
        container_name="main",
    )
    result = actor_service.delete_actor("test-actor-010")
    assert result is True
    assert actor_service.get_actor("test-actor-010") is None


def test_list_actors_with_filters(actor_service):
    actor_service.create_actor(
        actor_uid="filter-1", actor_name="Filter 1", actor_atespace="default",
        actor_template_namespace="ns1", actor_template_name="tmpl1", container_name="main",
    )
    actor_service.create_actor(
        actor_uid="filter-2", actor_name="Filter 2", actor_atespace="default",
        actor_template_namespace="ns1", actor_template_name="tmpl2", container_name="main",
    )
    actor_service.create_actor(
        actor_uid="filter-3", actor_name="Filter 3", actor_atespace="default",
        actor_template_namespace="ns2", actor_template_name="tmpl1", container_name="main",
    )

    actors = actor_service.list_actors(template_namespace="ns1")
    assert len(actors) == 2

    actors = actor_service.list_actors(template_name="tmpl1")
    assert len(actors) == 2

    actors = actor_service.list_actors(state=ActorState.SUSPENDED)
    assert len(actors) == 3


def test_transition_log_created(actor_service):
    actor_service.create_actor(
        actor_uid="log-test-1", actor_name="Log Test", actor_atespace="default",
        actor_template_namespace="default", actor_template_name="example", container_name="main",
    )
    actor_service.transition_actor("log-test-1", ActorState.RUNNING)

    actor = actor_service.get_actor("log-test-1")
    assert len(actor.transitions) == 2  # create + transition
    assert actor.transitions[0].from_state is None
    assert actor.transitions[0].to_state == ActorState.SUSPENDED
    assert actor.transitions[1].from_state == ActorState.SUSPENDED
    assert actor.transitions[1].to_state == ActorState.RUNNING