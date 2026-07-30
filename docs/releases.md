# Processo de release

## Versão atual

`v1.0.0` é a primeira versão estável do FinAnalytics. Ela consolida o pipeline
de dados, a API, o dashboard, analytics, previsões, alertas, autenticação,
isolamento por empresa, auditoria, observabilidade e execução por Docker.

1. Confirme que a branch `master` está estável.
2. Revise mudanças desde a última versão.
3. Execute testes, Ruff e MyPy.
4. Verifique migrações e compatibilidade de configuração.
5. Atualize documentação e notas da versão.
6. Crie uma tag seguindo versionamento semântico.
7. Publique e valide o health check.
8. Monitore erros e métricas após a publicação.

Correções urgentes devem seguir o mesmo conjunto mínimo de verificações e registrar claramente o risco aceito.
