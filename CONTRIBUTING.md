# Como contribuir

Obrigado pelo interesse em contribuir com o FinAnalytics.

## Preparação do ambiente

1. Crie uma branch a partir de `master`.
2. Instale as dependências de desenvolvimento com `python -m pip install -e ".[dev]"`.
3. Faça alterações pequenas e focadas.
4. Não inclua dados financeiros reais, credenciais ou arquivos `.env`.

## Verificações

Antes de abrir um pull request, execute:

```bash
pytest
ruff check .
mypy app
```

Descreva no pull request o problema resolvido, a abordagem adotada e como a alteração foi validada.
