import uuid
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_analytics_service
from app.core.exceptions import AppError, NotFoundError
from app.main import app
from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import ExecutiveSummary
from app.schemas.category import TransactionType
from app.services.analytics_service import AnalyticsService, percentage

START_DATE = date(2026, 1, 1)
END_DATE = date(2026, 12, 31)


def service_with_repository() -> tuple[AnalyticsService, Mock, uuid.UUID]:
    company_id = uuid.uuid4()
    repository = Mock()
    company_repository = Mock()
    company_repository.get.return_value = SimpleNamespace(id=company_id)
    return AnalyticsService(repository, company_repository), repository, company_id


def test_percentage_handles_values_and_zero() -> None:
    assert percentage(Decimal("25"), Decimal("100")) == Decimal("25.00")
    assert percentage(Decimal("1"), Decimal("3")) == Decimal("33.33")
    assert percentage(Decimal("5"), Decimal("0")) is None


def test_executive_summary_calculates_derived_kpis() -> None:
    service, repository, company_id = service_with_repository()
    repository.executive_summary.return_value = {
        "realized_revenue": Decimal("1000"),
        "realized_expense": Decimal("600"),
        "pending_receivables": Decimal("200"),
        "overdue_receivables": Decimal("100"),
        "total_receivables": Decimal("2000"),
    }

    result = service.executive_summary(company_id, START_DATE, END_DATE)

    assert result.net_result == Decimal("400")
    assert result.margin_percentage == Decimal("40.00")
    assert result.delinquency_rate_percentage == Decimal("5.00")


def test_monthly_summary_calculates_margin() -> None:
    service, repository, company_id = service_with_repository()
    repository.monthly_summary.return_value = [
        {
            "reference_month": date(2026, 1, 1),
            "total_revenue": Decimal("500"),
            "total_expense": Decimal("300"),
        },
        {
            "reference_month": date(2026, 2, 1),
            "total_revenue": Decimal("0"),
            "total_expense": Decimal("50"),
        },
    ]

    result = service.monthly_summary(company_id, START_DATE, END_DATE)

    assert result[0].net_result == Decimal("200")
    assert result[0].margin_percentage == Decimal("40.00")
    assert result[1].margin_percentage is None


def test_category_summary_calculates_share() -> None:
    service, repository, company_id = service_with_repository()
    repository.category_summary.return_value = [
        {
            "category_id": uuid.uuid4(),
            "category_name": "Pessoal",
            "transaction_type": "expense",
            "total_amount": Decimal("750"),
            "transaction_count": 3,
        },
        {
            "category_id": uuid.uuid4(),
            "category_name": "Marketing",
            "transaction_type": "expense",
            "total_amount": Decimal("250"),
            "transaction_count": 2,
        },
    ]

    result = service.category_summary(company_id, START_DATE, END_DATE, TransactionType.EXPENSE)

    assert result[0].share_percentage == Decimal("75.00")
    assert result[1].share_percentage == Decimal("25.00")


def test_cash_flow_accumulates_monthly_results() -> None:
    service, repository, company_id = service_with_repository()
    repository.cash_flow.return_value = [
        {
            "reference_month": date(2026, 1, 1),
            "inflows": Decimal("100"),
            "outflows": Decimal("40"),
        },
        {
            "reference_month": date(2026, 2, 1),
            "inflows": Decimal("50"),
            "outflows": Decimal("70"),
        },
    ]

    result = service.cash_flow(company_id, START_DATE, END_DATE)

    assert result[0].accumulated_cash_flow == Decimal("60")
    assert result[1].accumulated_cash_flow == Decimal("40")


def test_overdue_summary_calculates_rate_and_average() -> None:
    service, repository, company_id = service_with_repository()
    repository.overdue_summary.return_value = {
        "overdue_amount": Decimal("125"),
        "overdue_count": 2,
        "average_days_overdue": 12.345,
        "total_receivables": Decimal("1000"),
    }

    result = service.overdue_summary(company_id, START_DATE, END_DATE)

    assert result.average_days_overdue == Decimal("12.35")
    assert result.delinquency_rate_percentage == Decimal("12.50")


def test_analytics_validates_period_and_company() -> None:
    service, _, company_id = service_with_repository()
    with pytest.raises(AppError, match="start_date"):
        service.executive_summary(company_id, END_DATE, START_DATE)

    service.company_repository.get.return_value = None
    with pytest.raises(NotFoundError):
        service.executive_summary(company_id, START_DATE, END_DATE)


def test_analytics_repository_builds_all_queries() -> None:
    session = MagicMock()
    mappings = session.execute.return_value.mappings.return_value
    mappings.one.return_value = {
        "realized_revenue": Decimal("0"),
        "realized_expense": Decimal("0"),
        "pending_receivables": Decimal("0"),
        "overdue_receivables": Decimal("0"),
        "total_receivables": Decimal("0"),
    }
    mappings.__iter__.return_value = iter([])
    repository = AnalyticsRepository(session)
    company_id = uuid.uuid4()

    assert repository.executive_summary(company_id, START_DATE, END_DATE)["realized_revenue"] == 0
    assert repository.monthly_summary(company_id, START_DATE, END_DATE) == []
    assert (
        repository.category_summary(company_id, START_DATE, END_DATE, TransactionType.EXPENSE) == []
    )
    assert repository.cash_flow(company_id, START_DATE, END_DATE) == []
    assert repository.overdue_summary(company_id, START_DATE, END_DATE)["total_receivables"] == 0


def test_executive_summary_endpoint() -> None:
    company_id = uuid.uuid4()
    service = Mock()
    service.executive_summary.return_value = ExecutiveSummary(
        company_id=company_id,
        start_date=START_DATE,
        end_date=END_DATE,
        realized_revenue=Decimal("100"),
        realized_expense=Decimal("40"),
        net_result=Decimal("60"),
        margin_percentage=Decimal("60"),
        pending_receivables=Decimal("10"),
        overdue_receivables=Decimal("5"),
        delinquency_rate_percentage=Decimal("5"),
    )
    app.dependency_overrides[get_analytics_service] = lambda: service

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/analytics/executive-summary",
            params={
                "company_id": str(company_id),
                "start_date": START_DATE.isoformat(),
                "end_date": END_DATE.isoformat(),
            },
        )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["net_result"] == "60"
