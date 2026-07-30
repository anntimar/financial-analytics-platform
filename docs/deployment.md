# Checklist de deploy

Antes de publicar:

- confirme que CI, testes, Ruff e MyPy passaram;
- configure banco, `DATABASE_URL`, `SECRET_KEY` e `ALLOWED_HOSTS`;
- aplique todas as migrações Alembic;
- mantenha debug desativado;
- termine TLS no proxy ou na plataforma;
- configure backups, alertas e rotação de segredos;
- valide `/api/v1/health` após o deploy;
- crie o administrador inicial uma única vez.

Nunca reutilize credenciais do ambiente de desenvolvimento em produção.
