import json
import os
import uuid
from datetime import date

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from dashboard.api_client import DashboardAPIError, FinAnalyticsClient
from dashboard.components import dashboard_api_url, format_currency, format_percentage, status_badge


def test_dashboard_client_builds_analytics_query() -> None:
    company_id = uuid.uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/analytics/executive-summary"
        assert request.url.params["company_id"] == str(company_id)
        assert request.url.params["start_date"] == "2026-01-01"
        return httpx.Response(
            200,
            json={"net_result": "100.00"},
        )

    client = FinAnalyticsClient("http://test/api/v1", transport=httpx.MockTransport(handler))
    result = client.executive_summary(company_id, date(2026, 1, 1), date(2026, 12, 31))

    assert result["net_result"] == "100.00"


def test_dashboard_client_sends_csv_as_multipart() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read()
        assert b"transactions.csv" in body
        assert b"company_id" in body
        return httpx.Response(201, json={"status": "completed"})

    client = FinAnalyticsClient("http://test/api/v1", transport=httpx.MockTransport(handler))
    result = client.import_transactions(uuid.uuid4(), "transactions.csv", b"a,b\n1,2")

    assert result["status"] == "completed"


def test_dashboard_client_exposes_api_error_detail() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            409,
            content=json.dumps({"detail": "Arquivo duplicado."}).encode(),
            headers={"content-type": "application/json"},
        )

    client = FinAnalyticsClient("http://test/api/v1", transport=httpx.MockTransport(handler))

    with pytest.raises(DashboardAPIError, match="Arquivo duplicado"):
        client.companies()


def test_dashboard_formatters() -> None:
    assert format_currency("1250.9") == "R$ 1.250,90"
    assert format_percentage("12.5") == "12,50%"
    assert format_percentage(None) == "—"
    assert status_badge("completed") == "✅ Concluído"
    assert status_badge("unknown") == "unknown"


def test_dashboard_api_url_normalizes_render_hostport() -> None:
    previous = os.environ.get("DASHBOARD_API_URL")
    os.environ["DASHBOARD_API_URL"] = "finanalytics-api:10000"
    try:
        assert dashboard_api_url() == "http://finanalytics-api:10000/api/v1"
    finally:
        if previous is None:
            os.environ.pop("DASHBOARD_API_URL", None)
        else:
            os.environ["DASHBOARD_API_URL"] = previous


def test_dashboard_home_page_smoke() -> None:
    app_test = AppTest.from_file("dashboard/Home.py").run(timeout=10)
    assert not app_test.exception
    assert app_test.title[0].value == "FinAnalytics"
