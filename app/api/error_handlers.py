from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError


async def app_error_handler(_request: Request, error: Exception) -> JSONResponse:
    if not isinstance(error, AppError):
        raise error
    exc = error
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
