# Modelo de dados

As entidades centrais incluem empresas, usuários, categorias, subcategorias, centros de custo, contas, orçamentos e transações.

Regras importantes:

- recursos financeiros pertencem a uma empresa;
- valores monetários usam `NUMERIC(14,2)`;
- datas de negócio usam `DATE`;
- auditoria usa `TIMESTAMPTZ`;
- categorias e centros de custo devem pertencer à mesma empresa da transação;
- migrações Alembic são a fonte de verdade para mudanças estruturais.

Nunca crie relacionamentos que permitam acesso cruzado entre empresas.
