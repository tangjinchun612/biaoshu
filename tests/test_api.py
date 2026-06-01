import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert data["service"] == "标书对比分析服务"


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_create_task_with_invalid_files():
    response = client.post(
        "/api/v1/tasks/create",
        json={
            "tender_file_id": "invalid-id",
            "bid_file_id": "invalid-id"
        }
    )
    assert response.status_code == 404


def test_get_nonexistent_task():
    response = client.get("/api/v1/tasks/nonexistent-id")
    assert response.status_code == 404
