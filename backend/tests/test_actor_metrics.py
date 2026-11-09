import pytest
from backend.app.models.actor import ActorState
from backend.app.services.actor_metrics import ActorMetricsService
from prometheus_client import CollectorRegistry


@pytest.fixture
def metrics():
    # Use a fresh registry for each test to avoid duplicate registration
    registry = CollectorRegistry()
    return ActorMetricsService(registry=registry)


def test_increment_decrement_actor(metrics):
    metrics.increment_actor("ns1", "tmpl1", ActorState.RUNNING)
    assert metrics.get_current_count("ns1", "tmpl1", ActorState.RUNNING) == 1

    metrics.increment_actor("ns1", "tmpl1", ActorState.RUNNING)
    assert metrics.get_current_count("ns1", "tmpl1", ActorState.RUNNING) == 2

    metrics.decrement_actor("ns1", "tmpl1", ActorState.RUNNING)
    assert metrics.get_current_count("ns1", "tmpl1", ActorState.RUNNING) == 1

    metrics.decrement_actor("ns1", "tmpl1", ActorState.RUNNING)
    assert metrics.get_current_count("ns1", "tmpl1", ActorState.RUNNING) == 0

    # Decrement below zero should not go negative
    metrics.decrement_actor("ns1", "tmpl1", ActorState.RUNNING)
    assert metrics.get_current_count("ns1", "tmpl1", ActorState.RUNNING) == 0


def test_multiple_templates(metrics):
    metrics.increment_actor("ns1", "tmpl1", ActorState.RUNNING)
    metrics.increment_actor("ns1", "tmpl2", ActorState.RUNNING)
    metrics.increment_actor("ns2", "tmpl1", ActorState.RUNNING)

    assert metrics.get_current_count("ns1", "tmpl1", ActorState.RUNNING) == 1
    assert metrics.get_current_count("ns1", "tmpl2", ActorState.RUNNING) == 1
    assert metrics.get_current_count("ns2", "tmpl1", ActorState.RUNNING) == 1


def test_all_states(metrics):
    for state in ActorState:
        metrics.increment_actor("ns1", "tmpl1", state)
        assert metrics.get_current_count("ns1", "tmpl1", state) == 1
        metrics.decrement_actor("ns1", "tmpl1", state)
        assert metrics.get_current_count("ns1", "tmpl1", state) == 0


def test_record_crash(metrics):
    metrics.record_crash("ns1", "tmpl1")
    # Counter incremented (no direct assertion on prometheus client in unit test)


def test_record_transition(metrics):
    metrics.record_transition(ActorState.SUSPENDED, ActorState.RUNNING, "ns1", "tmpl1")
    metrics.record_transition(ActorState.RUNNING, ActorState.PAUSED, "ns1", "tmpl1")
    # Counters incremented


def test_record_durations(metrics):
    metrics.record_pause_duration("ns1", "tmpl1", 10.5)
    metrics.record_suspend_duration("ns1", "tmpl1", 3600.0)
    metrics.record_running_duration("ns1", "tmpl1", 5.2)
    # Histograms observed
def test_metrics_integration_via_api():
    """Integration test: verify metrics are updated correctly through API endpoints."""
    from fastapi.testclient import TestClient
    from backend.app.main import app
    from backend.app.core.database import Base, engine
    from backend.app.services.actor_metrics import actor_metrics

    Base.metadata.create_all(bind=engine)
    client = TestClient(app)

    # Create an actor
    response = client.post("/actors", json={
        "actor_uid": "metrics-integration-1",
        "actor_name": "test-actor",
        "actor_atespace": "default",
        "actor_template_namespace": "ns1",
        "actor_template_name": "tmpl1",
        "container_name": "container1"
    })
    assert response.status_code == 201
    assert response.json()["state"] == "SUSPENDED"

    # Check metrics after create
    response = client.get("/metrics")
    metrics_text = response.text
    assert 'ate_actors{actor_template_name="tmpl1",actor_template_namespace="ns1",status="SUSPENDED"} 1.0' in metrics_text

    # Transition to RUNNING
    response = client.post("/actors/metrics-integration-1/transition", json={"to_state": "RUNNING"})
    assert response.status_code == 200
    assert response.json()["state"] == "RUNNING"

    # Check metrics after RUNNING
    response = client.get("/metrics")
    metrics_text = response.text
    assert 'ate_actors{actor_template_name="tmpl1",actor_template_namespace="ns1",status="SUSPENDED"} 0.0' in metrics_text
    assert 'ate_actors{actor_template_name="tmpl1",actor_template_namespace="ns1",status="RUNNING"} 1.0' in metrics_text

    # Transition to PAUSED
    response = client.post("/actors/metrics-integration-1/transition", json={"to_state": "PAUSED"})
    assert response.status_code == 200
    assert response.json()["state"] == "PAUSED"

    # Check metrics after PAUSED
    response = client.get("/metrics")
    metrics_text = response.text
    assert 'ate_actors{actor_template_name="tmpl1",actor_template_namespace="ns1",status="RUNNING"} 0.0' in metrics_text
    assert 'ate_actors{actor_template_name="tmpl1",actor_template_namespace="ns1",status="PAUSED"} 1.0' in metrics_text

    # Commit to SUSPENDED
    response = client.post("/actors/metrics-integration-1/commit", json={"tag": "v1", "scope": "data"})
    assert response.status_code == 200
    assert response.json()["state"] == "SUSPENDED"

    # Check metrics after SUSPENDED
    response = client.get("/metrics")
    metrics_text = response.text
    assert 'ate_actors{actor_template_name="tmpl1",actor_template_namespace="ns1",status="PAUSED"} 0.0' in metrics_text
    assert 'ate_actors{actor_template_name="tmpl1",actor_template_namespace="ns1",status="SUSPENDED"} 1.0' in metrics_text

    # Crash from RUNNING (need to resume first)
    response = client.post("/actors/metrics-integration-1/transition", json={"to_state": "RUNNING"})
    assert response.status_code == 200
    response = client.post("/actors/metrics-integration-1/transition", json={"to_state": "CRASHED"})
    assert response.status_code == 200
    assert response.json()["state"] == "CRASHED"

    # Check metrics after CRASHED
    response = client.get("/metrics")
    metrics_text = response.text
    assert 'ate_actors{actor_template_name="tmpl1",actor_template_namespace="ns1",status="RUNNING"} 0.0' in metrics_text
    assert 'ate_actors{actor_template_name="tmpl1",actor_template_namespace="ns1",status="CRASHED"} 1.0' in metrics_text

    # Revert to SUSPENDED
    response = client.post("/actors/metrics-integration-1/revert", json={"tag": "v1"})
    assert response.status_code == 200
    assert response.json()["state"] == "SUSPENDED"

    # Check metrics after revert to SUSPENDED
    response = client.get("/metrics")
    metrics_text = response.text
    assert 'ate_actors{actor_template_name="tmpl1",actor_template_namespace="ns1",status="CRASHED"} 0.0' in metrics_text
    assert 'ate_actors{actor_template_name="tmpl1",actor_template_namespace="ns1",status="SUSPENDED"} 1.0' in metrics_text

    # Delete
    response = client.delete("/actors/metrics-integration-1")
    assert response.status_code == 204

    # Check metrics after delete
    response = client.get("/metrics")
    metrics_text = response.text
    assert 'ate_actors{actor_template_name="tmpl1",actor_template_namespace="ns1",status="SUSPENDED"} 0.0' in metrics_text

    Base.metadata.drop_all(bind=engine)