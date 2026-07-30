# Guia da API

A documentação interativa fica disponível em `/docs`. O health check e os endpoints de autenticação são públicos; as rotas financeiras exigem JWT.

## Fluxo básico

1. Crie o primeiro administrador em `POST /api/v1/auth/bootstrap`.
2. Obtenha um token em `POST /api/v1/auth/login`.
3. Envie `Authorization: Bearer TOKEN` nas chamadas protegidas.
4. Informe `company_id` nos recursos isolados por empresa.

Não registre tokens, senhas ou conteúdo financeiro em logs e exemplos públicos.
