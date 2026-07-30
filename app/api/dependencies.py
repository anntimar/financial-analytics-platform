from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.account_repository import AccountRepository
from app.repositories.alert_action_repository import AlertActionRepository
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.budget_repository import BudgetRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.cost_center_repository import CostCenterRepository
from app.repositories.import_repository import ImportRepository
from app.repositories.subcategory_repository import SubcategoryRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_repository import UserRepository
from app.services.account_service import AccountService
from app.services.alert_service import AlertService
from app.services.analytics_service import AnalyticsService
from app.services.auth_service import AuthService
from app.services.budget_service import BudgetService
from app.services.category_service import CategoryService
from app.services.company_service import CompanyService
from app.services.cost_center_service import CostCenterService
from app.services.import_service import ImportService
from app.services.predictive_service import PredictiveService
from app.services.report_service import ReportService
from app.services.subcategory_service import SubcategoryService
from app.services.transaction_service import TransactionService

DatabaseSession = Annotated[Session, Depends(get_db)]


def get_account_service(session: DatabaseSession) -> AccountService:
    return AccountService(AccountRepository(session), CompanyRepository(session))


def get_alert_service(session: DatabaseSession) -> AlertService:
    return AlertService(
        get_analytics_service(session),
        AlertActionRepository(session),
    )


def get_auth_service(session: DatabaseSession) -> AuthService:
    return AuthService(UserRepository(session), CompanyRepository(session))


def get_budget_service(session: DatabaseSession) -> BudgetService:
    return BudgetService(
        BudgetRepository(session),
        CompanyRepository(session),
        CategoryRepository(session),
    )


def get_analytics_service(session: DatabaseSession) -> AnalyticsService:
    return AnalyticsService(
        AnalyticsRepository(session),
        CompanyRepository(session),
    )


def get_predictive_service(session: DatabaseSession) -> PredictiveService:
    return PredictiveService(
        AnalyticsRepository(session),
        CompanyRepository(session),
    )


def get_report_service(session: DatabaseSession) -> ReportService:
    analytics = get_analytics_service(session)
    return ReportService(
        analytics,
        AlertService(analytics, AlertActionRepository(session)),
        CompanyRepository(session),
    )


def get_company_service(session: DatabaseSession) -> CompanyService:
    return CompanyService(CompanyRepository(session))


def get_category_service(session: DatabaseSession) -> CategoryService:
    return CategoryService(CategoryRepository(session), CompanyRepository(session))


def get_cost_center_service(session: DatabaseSession) -> CostCenterService:
    return CostCenterService(
        CostCenterRepository(session),
        CompanyRepository(session),
    )


def get_subcategory_service(session: DatabaseSession) -> SubcategoryService:
    return SubcategoryService(
        SubcategoryRepository(session),
        CategoryRepository(session),
    )


def get_transaction_service(session: DatabaseSession) -> TransactionService:
    return TransactionService(
        TransactionRepository(session),
        CompanyRepository(session),
        CategoryRepository(session),
        AccountRepository(session),
        SubcategoryRepository(session),
        CostCenterRepository(session),
    )


def get_import_service(session: DatabaseSession) -> ImportService:
    return ImportService(
        ImportRepository(session),
        CompanyRepository(session),
        CategoryRepository(session),
        SubcategoryRepository(session),
        CostCenterRepository(session),
    )
