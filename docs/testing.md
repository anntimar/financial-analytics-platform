# Testes e qualidade

Execute a suíte completa antes de abrir um pull request:

```bash
pytest
ruff check .
mypy app
```

Os testes cobrem API, serviços, repositórios, autenticação, isolamento entre empresas, pipelines, analytics e dashboard. Testes de integração exigem PostgreSQL e migrações atualizadas.

Uma correção deve incluir um teste que falhe antes da mudança e passe depois dela. Evite depender de horário, rede ou dados externos não controlados.
