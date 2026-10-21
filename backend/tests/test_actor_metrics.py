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