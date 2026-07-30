# Operações

Monitore disponibilidade, latência, códigos HTTP, falhas de importação e uso do banco. A API emite logs JSON em `stdout` e identifica requisições com `X-Request-ID`.

Em incidentes:

1. registre horário, ambiente e identificador da requisição;
2. verifique saúde da API e do PostgreSQL;
3. correlacione logs sem expor dados financeiros;
4. confirme migrações e configuração;
5. aplique correção reversível;
6. documente causa, impacto e prevenção.

Teste periodicamente a restauração dos backups; um backup não validado não constitui estratégia de recuperação.
