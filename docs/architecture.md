# Arquitetura

O FinAnalytics separa responsabilidades em camadas:

- `api/routes`: contratos HTTP e controle de acesso;
- `services`: regras de negócio e coordenação de casos de uso;
- `repositories`: consultas e persistência;
- `models`: entidades SQLAlchemy;
- `schemas`: validação e serialização;
- `pipelines`: leitura, transformação e validação de importações;
- `dashboard`: interface Streamlit consumindo a API.

Os schemas PostgreSQL `raw`, `core` e `analytics` preservam, respectivamente, dados recebidos, dados normalizados e agregações.
