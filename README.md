# FinAnalytics

Plataforma de analytics financeiro que transforma dados de receitas e despesas em
indicadores gerenciais. O projeto é um produto de portfólio com dados sintéticos e
arquitetura ponta a ponta: ingestão, PostgreSQL, API e, nas próximas etapas, dashboard.

## Estado atual

As duas primeiras entregas estabelecem a fundação e a API operacional:

- API FastAPI com endpoint de saúde;
- CRUD de empresas, categorias e transações;
- filtros financeiros e paginação com limite de 100 registros;
- validações de vínculo entre empresa, categoria e tipo de transação;
- respostas de erro padronizadas para recursos ausentes e conflitos;
- pipeline CSV com camada bruta, validação por linha e deduplicação;
- histórico de lotes e relatório consultável de problemas de qualidade;
- KPIs financeiros, série mensal, categorias, fluxo de caixa e inadimplência;
- configuração por variáveis de ambiente;
- PostgreSQL 16 em Docker Compose;
- modelos SQLAlchemy de empresas, categorias e transações;
- migração inicial com schemas `raw`, `core` e `analytics`;
- transformadores reutilizáveis de texto e valores monetários;
- testes automatizados, Ruff e MyPy.

## Arquitetura

```text
CSV / Excel / API
        |
        v
Pipeline Python  -->  raw  -->  core  -->  analytics
                                           |
                                           v
                                      API FastAPI
                                           |
                                           v
                                  Dashboard (próxima fase)
```

## Execução com Docker

Pré-requisito: Docker Desktop com Docker Compose.

```bash
cp .env.example .env
docker compose up --build
```

Depois de iniciado:

- API: <http://localhost:8000>
- Swagger: <http://localhost:8000/docs>
- Saúde: <http://localhost:8000/api/v1/health>
- Dashboard: <http://localhost:8501>

## Autenticação e perfis

As rotas financeiras exigem um token JWT. O health check, o login e a criação
controlada do primeiro administrador permanecem públicos. Senhas são armazenadas
somente como hashes bcrypt.

Crie o primeiro administrador uma única vez em `POST /api/v1/auth/bootstrap`:

```json
{
  "name": "Administrador",
  "email": "admin@example.com",
  "password": "uma-senha-forte",
  "role": "admin"
}
```

Depois, use `POST /api/v1/auth/login` e envie o token como
`Authorization: Bearer TOKEN`. Administradores gerenciam empresas e usuários;
administradores e analistas alteram/importam dados; gestores possuem acesso de
consulta aos dashboards e indicadores.

Em produção, `SECRET_KEY` deve receber um valor longo, aleatório e exclusivo.

## Importação CSV

Use o modelo em `data/sample/transactions_template.csv` e substitua `category_id`
pelo UUID de uma categoria cadastrada para a empresa. O arquivo aceita separador
vírgula ou ponto e vírgula, datas `AAAA-MM-DD` ou `DD/MM/AAAA` e valores como
`R$ 1.250,90`.

Colunas obrigatórias:

- `category_id`;
- `description`;
- `transaction_type`: `revenue` ou `expense`;
- `amount`;
- `competence_date`;
- `status`: `paid`, `pending`, `overdue`, `cancelled` ou `partially_paid`.

Importação pela API:

```bash
curl -X POST http://localhost:8000/api/v1/imports/transactions \
  -F "company_id=UUID_DA_EMPRESA" \
  -F "file=@data/sample/transactions_template.csv"
```

Cada linha original é armazenada em `raw.imported_transactions`. Registros válidos
seguem para `core.transactions`; problemas ficam em `core.data_quality_issues`.
O limite atual por arquivo é 5 MB.

## Analytics

Todos os endpoints analíticos exigem `company_id`, `start_date` e `end_date`:

- `GET /api/v1/analytics/executive-summary`;
- `GET /api/v1/analytics/monthly`;
- `GET /api/v1/analytics/categories`;
- `GET /api/v1/analytics/cash-flow`;
- `GET /api/v1/analytics/overdue`.
- `GET /api/v1/analytics/budget-comparison`.

### Planejamento orçamentário

Orçamentos mensais são gerenciados em `/api/v1/budgets`. Cada combinação de
empresa, categoria, tipo e mês é única. O comparativo calcula o desvio como
`realizado - planejado`, considera apenas transações pagas e pode ser exportado
em CSV pela página **Planejado vs. realizado** do dashboard.

Endpoints preditivos:

- `GET /api/v1/predictive/revenue-forecast`: tendência de receita para 1 a 6 meses;
- `GET /api/v1/predictive/expense-anomalies`: despesas acima do limite IQR da categoria.

Receitas e despesas realizadas consideram transações com status `paid`. A margem
é calculada por `(resultado / receita) × 100`; quando não há receita, o valor é
retornado como `null`. A taxa de inadimplência representa o valor vencido dividido
pelo total de contas a receber no período.

As views `analytics.monthly_financial_summary`,
`analytics.category_financial_summary` e `analytics.overdue_summary` também deixam
as agregações disponíveis diretamente no PostgreSQL para exploração em ferramentas
de BI.

## Desenvolvimento local

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
pytest
ruff check .
mypy app
```

O PostgreSQL precisa estar disponível para iniciar a API localmente. Ajuste
`DATABASE_URL` no arquivo `.env`.

Para iniciar o dashboard fora do Docker:

```bash
set DASHBOARD_API_URL=http://localhost:8000/api/v1
streamlit run dashboard/Home.py
```

No PowerShell, use
`$env:DASHBOARD_API_URL = "http://localhost:8000/api/v1"` antes do comando
`streamlit`.

## Dados sintéticos de demonstração

O projeto inclui uma carga determinística com três empresas, 24 meses e 20 mil
transações. Os dados simulam crescimento mensal, sazonalidade de dezembro,
impostos maiores em janeiro, inadimplência, pagamentos pendentes e despesas
atípicas. Nenhum dado pessoal ou empresarial real é utilizado.

Com os contêineres ativos:

```bash
docker compose exec api python scripts/seed_demo_data.py
```

O comando é idempotente: empresas que já possuem transações com origem
`synthetic` não são carregadas novamente.

## Qualidade, CI e observabilidade

O workflow `.github/workflows/ci.yml` é executado em pushes para `main` ou
`master` e em pull requests. Ele:

- instala Python 3.12 e dependências pelo `uv.lock`;
- executa Ruff e verifica a formatação;
- executa MyPy na API, dashboard e scripts;
- inicia PostgreSQL 16;
- aplica todas as migrações Alembic;
- executa testes unitários, de API e de integração;
- exige cobertura global mínima de 95%.

A API escreve logs JSON em `stdout`. Cada requisição recebe um `X-Request-ID` e
registra método, caminho, status e duração. Importações também registram lote,
empresa, linhas válidas, rejeições e duração, sem incluir o conteúdo financeiro
do arquivo.

## Execução em produção

O arquivo `docker-compose.prod.yml` aplica configuração de produção sobre o
Compose principal: reinício automático, debug desativado, segredos obrigatórios,
 validade menor do token e hosts permitidos explicitamente.

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Antes de executar, configure `POSTGRES_DB`, `POSTGRES_USER`,
`POSTGRES_PASSWORD`, `DATABASE_URL`, `SECRET_KEY` e `ALLOWED_HOSTS` no ambiente
da plataforma de hospedagem. Os containers da API e do dashboard executam com
usuário sem privilégios de root. A API também envia cabeçalhos contra MIME
sniffing, framing, vazamento de referência e acesso indevido a recursos do
navegador; HSTS é habilitado quando a requisição chega por HTTPS.

TLS deve terminar no proxy reverso ou na plataforma de nuvem. Backups do volume
PostgreSQL e rotação de segredos continuam sendo responsabilidades operacionais
do ambiente escolhido.

### Deploy pelo Render Blueprint

O arquivo `render.yaml` provisiona PostgreSQL, API e dashboard na região Oregon.
Ele gera o segredo JWT automaticamente, conecta a API ao banco pela rede privada,
executa as migrações Alembic e só realiza novos deploys depois de o CI passar.

No Render, escolha **New > Blueprint**, conecte este repositório e confirme o
Blueprint encontrado na raiz. Após o primeiro deploy:

1. abra a URL pública da API e execute `POST /api/v1/auth/bootstrap` uma única vez;
2. crie uma senha administrativa exclusiva para produção;
3. faça login no dashboard usando esse administrador;
4. troque os planos `free` por planos persistentes antes de usar a aplicação como
   demonstração permanente;
5. configure domínio, alertas e backups no painel da plataforma.

## Ciência de dados

A previsão utiliza regressão linear sobre a série mensal de receitas pagas e exige
ao menos oito meses de histórico. Os últimos meses são reservados para backtest,
com MAE, RMSE e MAPE expostos junto ao resultado. A faixa estimada usa o erro
observado no backtest.

A detecção de anomalias calcula o intervalo interquartil (IQR) separadamente por
categoria e sinaliza despesas pagas acima de `Q3 + 1,5 × IQR`. Cada resultado
informa a mediana, o limite calculado e uma explicação legível. Os modelos usam
somente dados sintéticos e não devem orientar decisões financeiras reais.

## Modelo inicial

- `core.companies`: empresas fictícias isoladas por identificador;
- `core.categories`: categorias de receita ou despesa por empresa;
- `core.transactions`: lançamentos financeiros com competência, vencimento e status.

Valores monetários são armazenados como `NUMERIC(14,2)`. Datas de negócio usam `DATE`;
datas de auditoria usam `TIMESTAMPTZ`.

## Roadmap

1. Fundação e modelo inicial — concluído.
2. CRUD de empresas, categorias e transações — concluído.
3. Pipeline de importação CSV com validação e relatório de rejeições — concluído.
4. Views e endpoints analíticos — concluído.
5. Dashboard Streamlit — concluído.
6. Dados sintéticos, cobertura ampliada e CI — concluído.
7. Previsão de receita e detecção de anomalias — concluído.
8. Autenticação e RBAC — concluído; deploy e monitoramento — próximos passos.

## Dados e segurança

O projeto deve usar apenas dados sintéticos. O arquivo `.env` não é versionado e
credenciais de produção nunca devem ser adicionadas ao repositório.
