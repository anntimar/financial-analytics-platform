# Dashboard

O dashboard Streamlit consome exclusivamente a API. Configure a URL antes da execução local:

```powershell
$env:DASHBOARD_API_URL = "http://localhost:8000/api/v1"
streamlit run dashboard/Home.py
```

Faça login com um usuário válido e selecione a empresa autorizada. As páginas apresentam visão executiva, importações, previsões, orçamento, contas, alertas, centros de custo e lançamentos.

Erros de autorização devem ser corrigidos na sessão ou no perfil do usuário, nunca contornados no cliente.
