import uuid
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_predictive_service
from app.core.exceptions import AppError
from app.main import app
from app.schemas.analytics import ForecastMetric, RevenueForecast, RevenueForecastPoint
from app.services.predictive_service import PredictiveService


def _service() -> tuple[PredictiveService, Mock, uuid.UUID]:
    company_id = uuid.uuid4()
    repository = Mock()
    company_repository = Mock()
    company_repository.get.return_value = SimpleNamespace(id=company_id)
    return PredictiveService(repository, company_repository), repository, company_id


def _monthly_rows(months: int = 12) -> list[dict[str, object]]:
    return [
        {
            "reference_month": date(2025 + index // 12, index % 12 + 1, 1),
            "total_revenue": Decimal(1000 + index * 100),
        }
        for index in range(months)
    ]


def test_revenue_forecast_follows_linear_trend() -> None:
    service, repository, company_id = _service()
    repository.monthly_summary.return_value = _monthly_rows()

    result = service.revenue_forecast(company_id, date(2025, 1, 1), date(2025, 12, 31), horizon=3)

    assert result.historical_months == 12
    assert [point.predicted_revenue for point in result.forecast] == [
        Decimal("2200.00"),
        Decimal("2300.00"),
        Decimal("2400.00"),
    ]
    assert result.metrics.mae == Decimal("0.00")


def test_revenue_forecast_requires_enough_history() -> None:
    service, repository, company_id = _service()
    repository.monthly_summary.return_value = _monthly_rows(7)
    with pytest.raises(AppError, match="8 meses"):
        service.revenue_forecast(company_id, date(2025, 1, 1), date(2025, 7, 31), 3)


def test_expense_anomalies_uses_category_iqr() -> None:
    service, repository, company_id = _service()
    category_id = uuid.uuid4()
    values = [100, 105, 95, 110, 98, 102, 1000]
    repository.expense_transactions.return_value = [
        {
            "id": uuid.uuid4(),
            "competence_date": date(2025, 1, index + 1),
            "description": f"Despesa {index}",
            "amount": Decimal(value),
            "category_id": category_id,
            "category_name": "Tecnologia",
        }
        for index, value in enumerate(values)
    ]

    result = service.expense_anomalies(company_id, date(2025, 1, 1), date(2025, 12, 31), limit=20)

    assert len(result) == 1
    assert result[0].amount == Decimal("1000.00")
    assert "mediana histórica" in result[0].explanation


def test_revenue_forecast_endpoint() -> None:
    company_id = uuid.uuid4()
    service = Mock()
    service.revenue_forecast.return_value = RevenueForecast(
        company_id=company_id,
        training_start=date(2025, 1, 1),
        training_end=date(2025, 12, 1),
        method="regressão linear",
        historical_months=12,
        metrics=ForecastMetric(
            mae=Decimal("10"),
            rmse=Decimal("12"),
            mape_percentage=Decimal("2"),
            validation_months=3,
        ),
        forecast=[
            RevenueForecastPoint(
                reference_month=date(2026, 1, 1),
                predicted_revenue=Decimal("2000"),
                lower_bound=Decimal("1900"),
                upper_bound=Decimal("2100"),
            )
        ],
        limitation="Uso exploratório.",
    )
    app.dependency_overrides[get_predictive_service] = lambda: service
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/predictive/revenue-forecast",
            params={
                "company_id": str(company_id),
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
            },
        )
    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["forecast"][0]["predicted_revenue"] == "2000"
