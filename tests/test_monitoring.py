from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.api.routes.health import database_is_ready
from app.main import app


def test_liveness_does_not_depend_on_database() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/live")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_readiness_returns_healthy_when_database_responds() -> None:
    with (
        patch("app.api.routes.health.database_is_ready", return_value=True),
        TestClient(app) as client,
    ):
        response = client.get("/api/v1/ready")

    assert response.status_code == 200
    assert response.json()["database"] == "connected"


def test_readiness_returns_503_when_database_is_unavailable() -> None:
    with (
        patch("app.api.routes.health.database_is_ready", return_value=False),
        TestClient(app) as client,
    ):
        response = client.get("/api/v1/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"


def test_database_probe_handles_sqlalchemy_error() -> None:
    connection = Mock()
    connection.__enter__ = Mock(side_effect=OperationalError("SELECT 1", {}, Exception("offline")))
    connection.__exit__ = Mock(return_value=None)
    with patch("app.api.routes.health.engine.connect", return_value=connection):
        assert database_is_ready() is False


def test_metrics_endpoint_exposes_http_metrics_with_route_template() -> None:
    with TestClient(app) as client:
        client.get("/api/v1/live")
        response = client.get("/api/v1/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "finanalytics_http_requests_total" in response.text
    assert 'route="/live"' in response.text
    assert 'status="200"' in response.text
