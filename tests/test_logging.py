import json
import logging

from fastapi.testclient import TestClient

from app.core.logging import JsonFormatter
from app.main import app


def test_json_formatter_includes_structured_context() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="finanalytics.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="import_completed",
        args=(),
        exc_info=None,
    )
    record.batch_id = "batch-123"
    record.valid_rows = 100

    payload = json.loads(formatter.format(record))

    assert payload["event"] == "import_completed"
    assert payload["level"] == "INFO"
    assert payload["batch_id"] == "batch-123"
    assert payload["valid_rows"] == 100
    assert "timestamp" in payload


def test_request_middleware_returns_request_id() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health", headers={"X-Request-ID": "test-request"})

    assert response.headers["X-Request-ID"] == "test-request"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_security_headers_enable_hsts_over_https() -> None:
    with TestClient(app, base_url="https://testserver") as client:
        response = client.get("/api/v1/health")
    assert response.headers["Strict-Transport-Security"].startswith("max-age=")
