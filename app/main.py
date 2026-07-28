import os

from fastapi import Depends, FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.error_handlers import app_error_handler
from app.api.middleware import RequestLoggingMiddleware
from app.api.routes.accounts import router as accounts_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.auth import router as auth_router
from app.api.routes.budgets import router as budgets_router
from app.api.routes.categories import router as categories_router
from app.api.routes.companies import router as companies_router
from app.api.routes.health import router as health_router
from app.api.routes.imports import router as imports_router
from app.api.routes.monitoring import router as monitoring_router
from app.api.routes.predictive import router as predictive_router
from app.api.routes.transactions import router as transactions_router
from app.api.security_headers import SecurityHeadersMiddleware
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging
from app.core.security import get_current_user, require_roles
from app.schemas.auth import UserRole

configure_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.app_debug,
    description="API da plataforma de analytics financeiro.",
)
app.add_exception_handler(AppError, app_error_handler)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
if settings.app_env == "production":
    allowed_hosts = {host.strip() for host in settings.allowed_hosts.split(",") if host.strip()}
    allowed_hosts.update(
        host
        for host in (
            os.getenv("RENDER_EXTERNAL_HOSTNAME"),
            os.getenv("INTERNAL_HOST"),
        )
        if host
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=sorted(allowed_hosts),
    )
app.include_router(health_router, prefix="/api/v1")
app.include_router(monitoring_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
authenticated = [Depends(get_current_user)]
editor = [Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST))]
app.include_router(analytics_router, prefix="/api/v1", dependencies=authenticated)
app.include_router(accounts_router, prefix="/api/v1", dependencies=authenticated)
app.include_router(budgets_router, prefix="/api/v1", dependencies=authenticated)
app.include_router(companies_router, prefix="/api/v1", dependencies=authenticated)
app.include_router(categories_router, prefix="/api/v1", dependencies=authenticated)
app.include_router(transactions_router, prefix="/api/v1", dependencies=authenticated)
app.include_router(imports_router, prefix="/api/v1", dependencies=editor)
app.include_router(predictive_router, prefix="/api/v1", dependencies=authenticated)
