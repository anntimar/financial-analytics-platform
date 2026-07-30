# Desenvolvimento local

## Requisitos

- Python 3.12;
- PostgreSQL 16;
- Docker Desktop, quando a execução for feita por contêineres.

## Ambiente Python

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
```

Copie `.env.example` para `.env` e ajuste `DATABASE_URL`. Antes de enviar alterações, execute `pytest`, `ruff check .` e `mypy app`.
