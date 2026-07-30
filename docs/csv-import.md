# Importação CSV

Use `data/sample/transactions_template.csv` como referência. O arquivo aceita vírgula ou ponto e vírgula e tem limite de 5 MB.

Campos obrigatórios:

- `category_id`;
- `description`;
- `transaction_type`;
- `amount`;
- `competence_date`;
- `status`.

Cada linha é preservada em `raw.imported_transactions`. Linhas válidas seguem para `core.transactions`; rejeições são registradas em `core.data_quality_issues`. Consulte o lote após a importação para confirmar contagens e erros.
