import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import Base, engine
from backend.app.services.telemetry_relay import TelemetryRelayService, telemetry_relay


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def relay_service():
    return TelemetryRelayService()


def test_telemetry_relay_service_instance(relay_service):
    assert isinstance(relay_service, TelemetryRelayService)


def test_attribute_actor(relay_service):
    input_data = {"actor_uid": "uid1", "actor_name": "Alice"}
    attributed = relay_service.attribute_actor(input_data)
    assert attributed["actor_uid"] == "uid1"
    assert attributed["actor_name"] == "Alice"
    assert attributed.get("actor_atespace") == "unknown"
    assert attributed.get("container_name") == "unknown"


def test_enforce_cardinality(relay_service):
    metrics = {"labels": {"foo": "bar"}, "value": 42}
    result = relay_service.enforce_cardinality(metrics)
    # Stub passes through unchanged
    assert result == metrics


def test_enforce_delta_temporality(relay_service):
    metrics = {"series": "delta"}
    result = relay_service.enforce_delta_temporality(metrics)
    assert result == metrics


def test_parse_otlp(relay_service):
    # Stub returns empty dict regardless of input
    result = relay_service.parse_otlp(b"")
    assert result == {}


def test_otel_traces_endpoint(client):
    # Send a simple JSON payload
    payload = {
        "actor_uid": "trace-actor-1",
        "actor_name": "Trace Actor",
        "actor_atespace": "space1",
        "actor_template_namespace": "ns",
        "actor_template_name": "tmpl",
        "container_name": "container1",
        "foo": "bar"
    }
    response = client.post("/otel/traces", json=payload)
    # Stub implementation returns 200 and echoes the payload
    assert response.status_code == 200
    data = response.json()
    # Attributes are added
    assert data["actor_uid"] == "trace-actor-1"
    assert data["actor_name"] == "Trace Actor"
    assert data["actor_atespace"] == "space1"
    assert data["actor_template_namespace"] == "ns"
    assert data["actor_template_name"] == "tmpl"
    assert data["container_name"] == "container1"
    # Additional fields preserved
    assert data["foo"] == "bar"


def test_otel_metrics_endpoint(client):
    payload = {
        "actor_uid": "metric-actor-2",
        "actor_template_namespace": "metrics-ns",
        "actor_template_name": "metrics-tmpl",
    }
    response = client.post("/otel/metrics", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["actor_uid"] == "metric-actor-2"
    assert data["actor_template_namespace"] == "metrics-ns"
    assert data["actor_template_name"] == "metrics-tmpl"


def test_otel_health_endpoint(client):
    response = client.get("/otel/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "telemetry_relay"
