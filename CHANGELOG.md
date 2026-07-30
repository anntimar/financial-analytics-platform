# Changelog

Todas as mudanças relevantes do FinAnalytics são documentadas neste arquivo.
O projeto segue versionamento semântico.

## [1.0.0] - 2026-07-30

### Adicionado

- Pipeline de importação CSV com camadas `raw` e `core`, validação e deduplicação.
- Modelo financeiro com empresas, contas, categorias, subcategorias, centros de
  custo, transações e orçamentos.
- API FastAPI autenticada com paginação, filtros, isolamento por empresa e RBAC.
- Dashboard Streamlit com nove áreas funcionais e exportações JSON/CSV.
- KPIs, fluxo de caixa, inadimplência, orçamento, saldos e centros de custo.
- Previsão de receitas, detecção de anomalias e alertas com fluxo de resolução.
- Administração de usuários e trilha imutável de auditoria de acessos.
- PostgreSQL 16, dez migrações Alembic, Docker Compose e dados sintéticos.
- Health checks, métricas Prometheus, logs estruturados e documentação operacional.
- GitHub Actions com lint, formatação, tipagem, PostgreSQL e cobertura mínima de 95%.

### Segurança

- Senhas com hash bcrypt e autenticação JWT.
- Perfis de administrador, analista e gestor.
- Validação de acesso por empresa e proteção contra desativação do próprio administrador.
- Auditoria administrativa sem armazenamento de senhas ou tokens.
