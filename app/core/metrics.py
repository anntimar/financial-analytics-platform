from prometheus_client import Counter, Histogram, generate_latest

HTTP_REQUESTS = Counter(
    "finanalytics_http_requests_total",
    "Total de requisições HTTP processadas.",
    ("method", "route", "status"),
)
HTTP_DURATION = Histogram(
    "finanalytics_http_request_duration_seconds",
    "Duração das requisições HTTP.",
    ("method", "route"),
)
IMPORT_ROWS = Counter(
    "finanalytics_import_rows_total",
    "Linhas processadas em importações financeiras.",
    ("result",),
)
IMPORT_DURATION = Histogram(
    "finanalytics_import_duration_seconds",
    "Duração das importações financeiras.",
)


def render_metrics() -> bytes:
    return generate_latest()
