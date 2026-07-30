# Solução de problemas

## API não inicia

Confirme `DATABASE_URL`, disponibilidade do PostgreSQL e migrações Alembic.

## Resposta 401 ou 403

Renove o token, confirme o perfil do usuário e verifique se ele possui acesso à empresa solicitada.

## Importação rejeitada

Confira tamanho, separador, cabeçalhos, UUID da categoria, formato de data, valor monetário e status.

## Dashboard sem dados

Valide `DASHBOARD_API_URL`, sessão, empresa selecionada e período dos filtros.

Use o `X-Request-ID` para correlacionar a resposta com os logs da API.
