import math
import uuid
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import numpy as np

from app.core.exceptions import AppError, NotFoundError
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.company_repository import CompanyRepository
from app.schemas.analytics import (
    ExpenseAnomaly,
    ForecastMetric,
    RevenueForecast,
    RevenueForecastPoint,
)

MONEY = Decimal("0.01")
PERCENT = Decimal("0.01")


def _decimal(value: float) -> Decimal:
    return Decimal(str(max(value, 0))).quantize(MONEY, rounding=ROUND_HALF_UP)


def _add_months(value: date, months: int) -> date:
    month_index = value.year * 12 + value.month - 1 + months
    return date(month_index // 12, month_index % 12 + 1, 1)


def _fit_trend(values: np.ndarray) -> tuple[float, float]:
    x = np.arange(len(values), dtype=float)
    slope, intercept = np.polyfit(x, values, 1)
    return float(slope), float(intercept)


def _predict(values: np.ndarray, horizon: int) -> np.ndarray:
    slope, intercept = _fit_trend(values)
    future_x = np.arange(len(values), len(values) + horizon, dtype=float)
    return np.maximum(intercept + slope * future_x, 0)


def _forecast_metrics(values: np.ndarray) -> tuple[ForecastMetric, float]:
    validation_months = min(3, max(1, len(values) // 4))
    train = values[:-validation_months]
    actual = values[-validation_months:]
    predicted = _predict(train, validation_months)
    errors = actual - predicted
    mae = float(np.mean(np.abs(errors)))
    rmse = math.sqrt(float(np.mean(np.square(errors))))
    nonzero = actual != 0
    mape = (
        float(np.mean(np.abs(errors[nonzero] / actual[nonzero])) * 100) if np.any(nonzero) else None
    )
    metric = ForecastMetric(
        mae=_decimal(mae),
        rmse=_decimal(rmse),
        mape_percentage=Decimal(str(mape)).quantize(PERCENT, rounding=ROUND_HALF_UP)
        if mape is not None
        else None,
        validation_months=validation_months,
    )
    return metric, rmse


class PredictiveService:
    def __init__(
        self,
        repository: AnalyticsRepository,
        company_repository: CompanyRepository,
    ) -> None:
        self.repository = repository
        self.company_repository = company_repository

    def _validate(self, company_id: uuid.UUID, start_date: date, end_date: date) -> None:
        if start_date > end_date:
            raise AppError("start_date não pode ser posterior a end_date.")
        if self.company_repository.get(company_id) is None:
            raise NotFoundError("Empresa")

    def revenue_forecast(
        self,
        company_id: uuid.UUID,
        start_date: date,
        end_date: date,
        horizon: int,
    ) -> RevenueForecast:
        self._validate(company_id, start_date, end_date)
        rows = self.repository.monthly_summary(company_id, start_date, end_date)
        if len(rows) < 8:
            raise AppError("A previsão exige pelo menos 8 meses de histórico.")

        values = np.array([float(row["total_revenue"]) for row in rows], dtype=float)
        metrics, residual_rmse = _forecast_metrics(values)
        predictions = _predict(values, horizon)
        last_month = rows[-1]["reference_month"]
        interval = 1.96 * residual_rmse
        points = [
            RevenueForecastPoint(
                reference_month=_add_months(last_month, index + 1),
                predicted_revenue=_decimal(prediction),
                lower_bound=_decimal(prediction - interval),
                upper_bound=_decimal(prediction + interval),
            )
            for index, prediction in enumerate(predictions)
        ]
        return RevenueForecast(
            company_id=company_id,
            training_start=rows[0]["reference_month"],
            training_end=last_month,
            method="regressão linear com tendência temporal",
            historical_months=len(rows),
            metrics=metrics,
            forecast=points,
            limitation=(
                "Estimativa exploratória baseada somente no histórico sintético; "
                "não deve orientar decisões financeiras reais."
            ),
        )

    def expense_anomalies(
        self,
        company_id: uuid.UUID,
        start_date: date,
        end_date: date,
        limit: int,
    ) -> list[ExpenseAnomaly]:
        self._validate(company_id, start_date, end_date)
        rows = self.repository.expense_transactions(company_id, start_date, end_date)
        grouped: dict[uuid.UUID, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[row["category_id"]].append(row)

        anomalies: list[ExpenseAnomaly] = []
        for category_rows in grouped.values():
            if len(category_rows) < 4:
                continue
            amounts = np.array([float(row["amount"]) for row in category_rows])
            q1, median, q3 = np.percentile(amounts, [25, 50, 75])
            threshold = float(q3 + 1.5 * (q3 - q1))
            if threshold <= 0:
                continue
            for row in category_rows:
                amount = float(row["amount"])
                if amount <= threshold:
                    continue
                deviation = ((amount / median) - 1) * 100 if median > 0 else 0
                deviation_decimal = Decimal(str(deviation)).quantize(
                    PERCENT, rounding=ROUND_HALF_UP
                )
                anomalies.append(
                    ExpenseAnomaly(
                        transaction_id=row["id"],
                        competence_date=row["competence_date"],
                        description=row["description"],
                        category_id=row["category_id"],
                        category_name=row["category_name"],
                        amount=_decimal(amount),
                        category_median=_decimal(float(median)),
                        upper_threshold=_decimal(threshold),
                        deviation_percentage=deviation_decimal,
                        explanation=(
                            f"Despesa {deviation_decimal}% acima da mediana histórica "
                            f"da categoria {row['category_name']}."
                        ),
                    )
                )
        anomalies.sort(key=lambda item: item.deviation_percentage, reverse=True)
        return anomalies[:limit]
