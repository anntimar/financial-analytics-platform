# Dados de demonstração

O projeto fornece dados inteiramente sintéticos para apresentação e testes. A carga inclui três empresas, 24 meses e cenários de sazonalidade, inadimplência, pagamentos pendentes e despesas atípicas.

Com os contêineres ativos:

```bash
docker compose exec api python scripts/seed_demo_data.py
```

O comando é idempotente para empresas que já possuem transações de origem `synthetic`. Não substitua essa carga por dados pessoais, bancários ou empresariais reais.
