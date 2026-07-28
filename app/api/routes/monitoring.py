from fastapi import APIRouter, Response

from app.core.metrics import render_metrics

router = APIRouter(tags=["monitoring"])


@router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(
        content=render_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
