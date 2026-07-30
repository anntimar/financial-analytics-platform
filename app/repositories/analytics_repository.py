import uuid
from datetime import date
from typing import Any

from sqlalchemy import Date, case, func, literal, select
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.budget import Budget
from app.models.category import Category
from app.models.cost_center import CostCenter
from app.models.transaction import Transaction
from app.schemas.category import TransactionType


class AnalyticsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _base_filters(company_id: uuid.UUID, start_date: date, end_date: date) -> list[Any]:
        return [
            Transaction.company_id == company_id,
            Transaction.competence_date >= start_date,
            Transaction.competence_date <= end_date,
            Transaction.status != "cancelled",
        ]

    def executive_summary(
        self, company_id: uuid.UUID, start_date: date, end_date: date
    ) -> dict[str, Any]:
        filters = self._base_filters(company_id, start_date, end_date)
        statement = select(
            func.coalesce(
                func.sum(
                    case(
                        (
                            (Transaction.transaction_type == "revenue")
                            & (Transaction.status == "paid"),
                            Transaction.amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("realized_revenue"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            (Transaction.transaction_type == "expense")
                            & (Transaction.status == "paid"),
                            Transaction.amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("realized_expense"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            (Transaction.transaction_type == "revenue")
                            & (Transaction.status.in_(("pending", "partially_paid"))),
                            Transaction.amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("pending_receivables"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            (Transaction.transaction_type == "revenue")
                            & (Transaction.status == "overdue"),
                            Transaction.amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("overdue_receivables"),
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.transaction_type == "revenue", Transaction.amount),
                        else_=0,
                    )
                ),
                0,
            ).label("total_receivables"),
        ).where(*filters)
        row = self.session.execute(statement).mappings().one()
        return dict(row)

    def monthly_summary(
        self, company_id: uuid.UUID, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        reference_month = (
            func.date_trunc("month", Transaction.competence_date)
            .cast(Date)
            .label("reference_month")
        )
        revenue = func.sum(
            case(
                (
                    (Transaction.transaction_type == "revenue") & (Transaction.status == "paid"),
                    Transaction.amount,
                ),
                else_=0,
            )
        ).label("total_revenue")
        expense = func.sum(
            case(
                (
                    (Transaction.transaction_type == "expense") & (Transaction.status == "paid"),
                    Transaction.amount,
                ),
                else_=0,
            )
        ).label("total_expense")
        statement = (
            select(reference_month, revenue, expense)
            .where(*self._base_filters(company_id, start_date, end_date))
            .group_by(reference_month)
            .order_by(reference_month)
        )
        return [dict(row) for row in self.session.execute(statement).mappings()]

    def category_summary(
        self,
        company_id: uuid.UUID,
        start_date: date,
        end_date: date,
        transaction_type: TransactionType,
    ) -> list[dict[str, Any]]:
        statement = (
            select(
                Category.id.label("category_id"),
                Category.name.label("category_name"),
                Category.transaction_type,
                func.sum(Transaction.amount).label("total_amount"),
                func.count(Transaction.id).label("transaction_count"),
            )
            .join(Category, Category.id == Transaction.category_id)
            .where(
                *self._base_filters(company_id, start_date, end_date),
                Transaction.transaction_type == transaction_type,
                Transaction.status == "paid",
            )
            .group_by(Category.id, Category.name, Category.transaction_type)
            .order_by(func.sum(Transaction.amount).desc())
        )
        return [dict(row) for row in self.session.execute(statement).mappings()]

    def cash_flow(
        self, company_id: uuid.UUID, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        cash_date = func.coalesce(
            Transaction.payment_date,
            Transaction.due_date,
            Transaction.competence_date,
        )
        reference_month = func.date_trunc("month", cash_date).cast(Date)
        inflows = func.sum(
            case(
                (Transaction.transaction_type == "revenue", Transaction.amount),
                else_=0,
            )
        ).label("inflows")
        outflows = func.sum(
            case(
                (Transaction.transaction_type == "expense", Transaction.amount),
                else_=0,
            )
        ).label("outflows")
        statement = (
            select(reference_month.label("reference_month"), inflows, outflows)
            .where(
                Transaction.company_id == company_id,
                cash_date >= start_date,
                cash_date <= end_date,
                Transaction.status != "cancelled",
            )
            .group_by(reference_month)
            .order_by(reference_month)
        )
        return [dict(row) for row in self.session.execute(statement).mappings()]

    def cost_center_summary(
        self, company_id: uuid.UUID, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        statement = (
            select(
                CostCenter.id.label("cost_center_id"),
                CostCenter.name.label("cost_center_name"),
                CostCenter.code.label("cost_center_code"),
                func.sum(Transaction.amount).label("total_amount"),
                func.count(Transaction.id).label("transaction_count"),
            )
            .join(CostCenter, CostCenter.id == Transaction.cost_center_id)
            .where(
                *self._base_filters(company_id, start_date, end_date),
                Transaction.transaction_type == "expense",
                Transaction.status == "paid",
            )
            .group_by(CostCenter.id, CostCenter.name, CostCenter.code)
            .order_by(func.sum(Transaction.amount).desc())
        )
        return [dict(row) for row in self.session.execute(statement).mappings()]

    def overdue_summary(
        self, company_id: uuid.UUID, start_date: date, end_date: date
    ) -> dict[str, Any]:
        filters = [
            *self._base_filters(company_id, start_date, end_date),
            Transaction.transaction_type == "revenue",
        ]
        statement = select(
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.status == "overdue", Transaction.amount),
                        else_=0,
                    )
                ),
                0,
            ).label("overdue_amount"),
            func.count(case((Transaction.status == "overdue", Transaction.id))).label(
                "overdue_count"
            ),
            func.avg(
                case(
                    (
                        Transaction.status == "overdue",
                        literal(end_date) - Transaction.due_date,
                    )
                )
            ).label("average_days_overdue"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total_receivables"),
        ).where(*filters)
        return dict(self.session.execute(statement).mappings().one())

    def budget_comparison(
        self, company_id: uuid.UUID, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        reference_month = func.date_trunc("month", Transaction.competence_date).cast(Date)
        realized = (
            select(
                Transaction.company_id.label("company_id"),
                Transaction.category_id.label("category_id"),
                Transaction.transaction_type.label("transaction_type"),
                reference_month.label("reference_month"),
                func.sum(Transaction.amount).label("realized_amount"),
            )
            .where(
                Transaction.company_id == company_id,
                Transaction.competence_date >= start_date,
                Transaction.competence_date <= end_date,
                Transaction.status == "paid",
            )
            .group_by(
                Transaction.company_id,
                Transaction.category_id,
                Transaction.transaction_type,
                reference_month,
            )
            .subquery()
        )
        statement = (
            select(
                Budget.reference_month,
                Budget.category_id,
                Category.name.label("category_name"),
                Budget.transaction_type,
                Budget.amount.label("planned_amount"),
                func.coalesce(realized.c.realized_amount, 0).label("realized_amount"),
            )
            .join(Category, Category.id == Budget.category_id)
            .outerjoin(
                realized,
                (realized.c.company_id == Budget.company_id)
                & (realized.c.category_id == Budget.category_id)
                & (realized.c.transaction_type == Budget.transaction_type)
                & (realized.c.reference_month == Budget.reference_month),
            )
            .where(
                Budget.company_id == company_id,
                Budget.reference_month >= start_date,
                Budget.reference_month <= end_date,
            )
            .order_by(Budget.reference_month, Budget.transaction_type, Category.name)
        )
        return [dict(row) for row in self.session.execute(statement).mappings()]

    def account_balances(
        self, company_id: uuid.UUID, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        statement = (
            select(
                Account.id.label("account_id"),
                Account.name.label("account_name"),
                Account.account_type,
                Account.opening_balance,
                func.coalesce(
                    func.sum(
                        case(
                            (Transaction.transaction_type == "revenue", Transaction.amount),
                            else_=0,
                        )
                    ),
                    0,
                ).label("inflows"),
                func.coalesce(
                    func.sum(
                        case(
                            (Transaction.transaction_type == "expense", Transaction.amount),
                            else_=0,
                        )
                    ),
                    0,
                ).label("outflows"),
            )
            .outerjoin(
                Transaction,
                (Transaction.account_id == Account.id)
                & (Transaction.status == "paid")
                & (Transaction.competence_date >= start_date)
                & (Transaction.competence_date <= end_date),
            )
            .where(Account.company_id == company_id, Account.is_active.is_(True))
            .group_by(
                Account.id,
                Account.name,
                Account.account_type,
                Account.opening_balance,
            )
            .order_by(Account.name)
        )
        return [dict(row) for row in self.session.execute(statement).mappings()]

    def expense_transactions(
        self, company_id: uuid.UUID, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        statement = (
            select(
                Transaction.id,
                Transaction.competence_date,
                Transaction.description,
                Transaction.amount,
                Category.id.label("category_id"),
                Category.name.label("category_name"),
            )
            .join(Category, Category.id == Transaction.category_id)
            .where(
                *self._base_filters(company_id, start_date, end_date),
                Transaction.transaction_type == "expense",
                Transaction.status == "paid",
            )
            .order_by(Transaction.competence_date.desc(), Transaction.amount.desc())
        )
        return [dict(row) for row in self.session.execute(statement).mappings()]
