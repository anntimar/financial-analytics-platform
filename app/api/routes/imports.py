import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status

from app.api.dependencies import get_import_service
from app.schemas.common import Page
from app.schemas.import_batch import (
    DataQualityIssueResponse,
    ImportBatchResponse,
)
from app.services.import_service import ImportService

router = APIRouter(prefix="/imports", tags=["imports"])
Service = Annotated[ImportService, Depends(get_import_service)]


@router.post(
    "/transactions",
    response_model=ImportBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_transactions(
    service: Service,
    company_id: Annotated[uuid.UUID, Form()],
    file: Annotated[UploadFile, File()],
) -> ImportBatchResponse:
    content = await file.read()
    return ImportBatchResponse.model_validate(
        service.import_transactions(company_id, file.filename or "upload.csv", content)
    )


@router.get("", response_model=Page[ImportBatchResponse])
def list_imports(
    company_id: uuid.UUID,
    service: Service,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[ImportBatchResponse]:
    return service.list(company_id, page, page_size)


@router.get("/{batch_id}", response_model=ImportBatchResponse)
def get_import(batch_id: uuid.UUID, service: Service) -> ImportBatchResponse:
    return ImportBatchResponse.model_validate(service.get(batch_id))


@router.get("/{batch_id}/issues", response_model=Page[DataQualityIssueResponse])
def list_import_issues(
    batch_id: uuid.UUID,
    service: Service,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[DataQualityIssueResponse]:
    return service.list_issues(batch_id, page, page_size)
