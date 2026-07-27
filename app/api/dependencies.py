from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.import_repository import ImportRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_repository import UserRepository
from app.services.analytics_service import AnalyticsService
from app.services.auth_service import AuthService
from app.services.category_service import CategoryService
from app.services.company_service import CompanyService
from app.services.import_service import ImportService
from app.services.predictive_service import PredictiveService
from app.services.transaction_service import TransactionService

DatabaseSession = Annotated[Session, Depends(get_db)]


def get_auth_service(session: DatabaseSession) -> AuthService:
    return AuthService(UserRepository(session), CompanyRepository(session))


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


def get_company_service(session: DatabaseSession) -> CompanyService:
    return CompanyService(CompanyRepository(session))


def get_category_service(session: DatabaseSession) -> CategoryService:
    return CategoryService(CategoryRepository(session), CompanyRepository(session))


def get_transaction_service(session: DatabaseSession) -> TransactionService:
    return TransactionService(
        TransactionRepository(session),
        CompanyRepository(session),
        CategoryRepository(session),
    )


def get_import_service(session: DatabaseSession) -> ImportService:
    return ImportService(
        ImportRepository(session),
        CompanyRepository(session),
        CategoryRepository(session),
    )
