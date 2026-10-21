import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import Base, engine


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


def test_list_actors_empty(client):
    response = client.get("/actors")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_create_actor(client):
    response = client.post("/actors", json={
        "actor_uid": "api-test-001",
        "actor_name": "API Test Actor",
        "actor_atespace": "default",
        "actor_template_namespace": "default",
        "actor_template_name": "example",
        "container_name": "main",
        "snapshot_scope": "data",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["actor_uid"] == "api-test-001"
    assert data["state"] == "SUSPENDED"


def test_get_actor(client):
    client.post("/actors", json={
        "actor_uid": "api-test-002", "actor_name": "Get Test", "actor_atespace": "default",
        "actor_template_namespace": "default", "actor_template_name": "example", "container_name": "main",
    })
    response = client.get("/actors/api-test-002")
    assert response.status_code == 200
    data = response.json()
    assert data["actor_uid"] == "api-test-002"


def test_get_actor_not_found(client):
    response = client.get("/actors/nonexistent")
    assert response.status_code == 404


def test_transition_actor(client):
    client.post("/actors", json={
        "actor_uid": "api-test-003", "actor_name": "Transition Test", "actor_atespace": "default",
        "actor_template_namespace": "default", "actor_template_name": "example", "container_name": "main",
    })
    # SUSPENDED -> RUNNING
    response = client.post("/actors/api-test-003/transition", json={
        "to_state": "RUNNING", "reason": "resume"
    })
    assert response.status_code == 200
    assert response.json()["state"] == "RUNNING"

    # RUNNING -> PAUSED
    response = client.post("/actors/api-test-003/transition", json={
        "to_state": "PAUSED", "reason": "pause"
    })
    assert response.status_code == 200
    assert response.json()["state"] == "PAUSED"


def test_invalid_transition(client):
    client.post("/actors", json={
        "actor_uid": "api-test-004", "actor_name": "Invalid Transition", "actor_atespace": "default",
        "actor_template_namespace": "default", "actor_template_name": "example", "container_name": "main",
    })
    # SUSPENDED -> CRASHED invalid
    response = client.post("/actors/api-test-004/transition", json={
        "to_state": "CRASHED", "reason": "crash"
    })
    assert response.status_code == 400


def test_pause_actor(client):
    client.post("/actors", json={
        "actor_uid": "api-test-005", "actor_name": "Pause Test", "actor_atespace": "default",
        "actor_template_namespace": "default", "actor_template_name": "example", "container_name": "main",
    })
    client.post("/actors/api-test-005/transition", json={"to_state": "RUNNING"})
    response = client.post("/actors/api-test-005/pause", json={"timer_seconds": 3600})
    assert response.status_code == 200
    assert response.json()["state"] == "PAUSED"
    assert response.json()["tags"] == "auto_commit_after=3600"


def test_commit_actor(client):
    client.post("/actors", json={
        "actor_uid": "api-test-006", "actor_name": "Commit Test", "actor_atespace": "default",
        "actor_template_namespace": "default", "actor_template_name": "example", "container_name": "main",
        "snapshot_scope": "full",
    })
    client.post("/actors/api-test-006/transition", json={"to_state": "RUNNING"})
    response = client.post("/actors/api-test-006/commit", json={"tag": "v1", "scope": "data"})
    assert response.status_code == 200
    assert response.json()["state"] == "SUSPENDED"
    assert response.json()["tags"] == "v1"
    assert response.json()["snapshot_scope"] == "data"


def test_commit_scope_validation(client):
    client.post("/actors", json={
        "actor_uid": "api-test-007", "actor_name": "Scope Test", "actor_atespace": "default",
        "actor_template_namespace": "default", "actor_template_name": "example", "container_name": "main",
        "snapshot_scope": "data",
    })
    client.post("/actors/api-test-007/transition", json={"to_state": "RUNNING"})
    # onPause=data cannot commit with scope=full
    response = client.post("/actors/api-test-007/commit", json={"scope": "full"})
    assert response.status_code == 400


def test_resume_actor(client):
    client.post("/actors", json={
        "actor_uid": "api-test-008", "actor_name": "Resume Test", "actor_atespace": "default",
        "actor_template_namespace": "default", "actor_template_name": "example", "container_name": "main",
    })
    response = client.post("/actors/api-test-008/resume", json={"node_name": "node-1"})
    assert response.status_code == 200
    assert response.json()["state"] == "RUNNING"
    assert response.json()["node_name"] == "node-1"


def test_revert_actor(client):
    client.post("/actors", json={
        "actor_uid": "api-test-009", "actor_name": "Revert Test", "actor_atespace": "default",
        "actor_template_namespace": "default", "actor_template_name": "example", "container_name": "main",
    })
    client.post("/actors/api-test-009/transition", json={"to_state": "RUNNING"})
    client.post("/actors/api-test-009/commit", json={"tag": "v1"})
    client.post("/actors/api-test-009/transition", json={"to_state": "RUNNING"})
    response = client.post("/actors/api-test-009/revert", json={"tag": "v1"})
    assert response.status_code == 200
    assert response.json()["state"] == "SUSPENDED"
    assert response.json()["tags"] == "v1"


def test_dump_actor(client):
    client.post("/actors", json={
        "actor_uid": "api-test-010", "actor_name": "Dump Test", "actor_atespace": "default",
        "actor_template_namespace": "default", "actor_template_name": "example", "container_name": "main",
    })
    client.post("/actors/api-test-010/transition", json={"to_state": "RUNNING"})
    response = client.post("/actors/api-test-010/dump", json={"tag": "debug-1"})
    assert response.status_code == 200
    assert response.json()["state"] == "SUSPENDED"
    assert response.json()["tags"] == "debug-1"


def test_delete_actor(client):
    client.post("/actors", json={
        "actor_uid": "api-test-011", "actor_name": "Delete Test", "actor_atespace": "default",
        "actor_template_namespace": "default", "actor_template_name": "example", "container_name": "main",
    })
    response = client.delete("/actors/api-test-011")
    assert response.status_code == 204
    response = client.get("/actors/api-test-011")
    assert response.status_code == 404


def test_list_actors_pagination(client):
    for i in range(25):
        client.post("/actors", json={
            "actor_uid": f"page-test-{i:03d}", "actor_name": f"Page Test {i}", "actor_atespace": "default",
            "actor_template_namespace": "default", "actor_template_name": "example", "container_name": "main",
        })
    response = client.get("/actors?skip=0&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 10
    assert data["total"] == 25
    assert data["skip"] == 0
    assert data["limit"] == 10

    response = client.get("/actors?skip=10&limit=10")
    data = response.json()
    assert len(data["items"]) == 10
    assert data["skip"] == 10


def test_list_actors_filter_by_state(client):
    client.post("/actors", json={
        "actor_uid": "filter-state-1", "actor_name": "Filter State 1", "actor_atespace": "default",
        "actor_template_namespace": "default", "actor_template_name": "example", "container_name": "main",
    })
    client.post("/actors", json={
        "actor_uid": "filter-state-2", "actor_name": "Filter State 2", "actor_atespace": "default",
        "actor_template_namespace": "default", "actor_template_name": "example", "container_name": "main",
    })
    client.post("/actors/filter-state-2/transition", json={"to_state": "RUNNING"})

    response = client.get("/actors?state=RUNNING")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["actor_uid"] == "filter-state-2"

    response = client.get("/actors?state=SUSPENDED")
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["actor_uid"] == "filter-state-1"


def test_get_snapshots(client):
    client.post("/actors", json={
        "actor_uid": "snap-test-1", "actor_name": "Snapshot Test", "actor_atespace": "default",
        "actor_template_namespace": "default", "actor_template_name": "example", "container_name": "main",
    })
    client.post("/actors/snap-test-1/transition", json={"to_state": "RUNNING"})
    client.post("/actors/snap-test-1/commit", json={"tag": "v1"})

    response = client.get("/actors/snap-test-1/snapshots")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["tag"] == "v1"


def test_get_transitions(client):
    client.post("/actors", json={
        "actor_uid": "trans-test-1", "actor_name": "Transition Test", "actor_atespace": "default",
        "actor_template_namespace": "default", "actor_template_name": "example", "container_name": "main",
    })

    response = client.get("/actors/trans-test-1/transitions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["to_state"] == "SUSPENDED"