from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from app.schemas.account import AccountBalance
from app.schemas.alert import AlertSeverity, FinancialAlert
from app.schemas.budget import BudgetComparison
from app.schemas.category import TransactionType
from app.services.analytics_service import AnalyticsService

DELINQUENCY_WARNING = Decimal("5")
DELINQUENCY_CRITICAL = Decimal("10")
BUDGET_WARNING = Decimal("10")
BUDGET_CRITICAL = Decimal("20")


class AlertService:
    def __init__(self, analytics: AnalyticsService) -> None:
        self.analytics = analytics

    def list_alerts(
        self, company_id: uuid.UUID, start_date: date, end_date: date
    ) -> list[FinancialAlert]:
        alerts: list[FinancialAlert] = []
        summary = self.analytics.executive_summary(company_id, start_date, end_date)
        alerts.extend(self._result_alert(summary.net_result, end_date))
        alerts.extend(self._delinquency_alert(summary.delinquency_rate_percentage, end_date))
        alerts.extend(
            self._budget_alerts(self.analytics.budget_comparison(company_id, start_date, end_date))
        )
        alerts.extend(
            self._balance_alerts(
                self.analytics.account_balances(company_id, start_date, end_date),
                end_date,
            )
        )
        return sorted(
            alerts,
            key=lambda alert: (
                {
                    AlertSeverity.CRITICAL: 0,
                    AlertSeverity.WARNING: 1,
                    AlertSeverity.INFO: 2,
                }[alert.severity],
                alert.code,
            ),
        )

    @staticmethod
    def _result_alert(net_result: Decimal, reference_date: date) -> list[FinancialAlert]:
        if net_result >= 0:
            return []
        return [
            FinancialAlert(
                code="negative_net_result",
                severity=AlertSeverity.CRITICAL,
                title="Resultado financeiro negativo",
                message=f"O período apresenta prejuízo de R$ {abs(net_result):,.2f}.",
                reference_date=reference_date,
                context={"net_result": net_result},
            )
        ]

    @staticmethod
    def _delinquency_alert(rate: Decimal | None, reference_date: date) -> list[FinancialAlert]:
        if rate is None or rate < DELINQUENCY_WARNING:
            return []
        severity = AlertSeverity.CRITICAL if rate >= DELINQUENCY_CRITICAL else AlertSeverity.WARNING
        return [
            FinancialAlert(
                code="high_delinquency",
                severity=severity,
                title="Inadimplência elevada",
                message=f"A taxa de inadimplência atingiu {rate:.2f}%.",
                reference_date=reference_date,
                context={"delinquency_rate_percentage": rate},
            )
        ]

    @staticmethod
    def _budget_alerts(comparisons: list[BudgetComparison]) -> list[FinancialAlert]:
        alerts: list[FinancialAlert] = []
        for item in comparisons:
            variance = item.variance_percentage
            is_expense_over = (
                item.transaction_type == TransactionType.EXPENSE
                and variance is not None
                and variance > 0
            )
            is_revenue_under = (
                item.transaction_type == TransactionType.REVENUE
                and variance is not None
                and variance < 0
            )
            deviation = abs(variance) if variance is not None else Decimal(0)
            if not (is_expense_over or is_revenue_under) or deviation < BUDGET_WARNING:
                continue
            severity = (
                AlertSeverity.CRITICAL if deviation >= BUDGET_CRITICAL else AlertSeverity.WARNING
            )
            direction = "acima" if is_expense_over else "abaixo"
            alerts.append(
                FinancialAlert(
                    code=f"budget_deviation:{item.category_id}",
                    severity=severity,
                    title=f"Desvio orçamentário em {item.category_name}",
                    message=f"O realizado ficou {deviation:.2f}% {direction} do planejado.",
                    reference_date=item.reference_month,
                    context={
                        "category_id": item.category_id,
                        "variance_percentage": variance,
                        "transaction_type": item.transaction_type,
                    },
                )
            )
        return alerts

    @staticmethod
    def _balance_alerts(
        balances: list[AccountBalance], reference_date: date
    ) -> list[FinancialAlert]:
        alerts: list[FinancialAlert] = []
        for account in balances:
            balance = account.current_balance
            if balance >= 0:
                continue
            alerts.append(
                FinancialAlert(
                    code=f"negative_account_balance:{account.account_id}",
                    severity=AlertSeverity.CRITICAL,
                    title=f"Saldo negativo em {account.account_name}",
                    message=f"A conta está com saldo negativo de R$ {abs(balance):,.2f}.",
                    reference_date=reference_date,
                    context={
                        "account_id": account.account_id,
                        "current_balance": balance,
                    },
                )
            )
        return alerts
