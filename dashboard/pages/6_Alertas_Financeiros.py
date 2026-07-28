from collections import Counter

import pandas as pd
import streamlit as st

from dashboard.api_client import DashboardAPIError
from dashboard.components import (
    company_selector,
    configure_page,
    get_client,
    load_companies,
    period_selector,
    require_login,
)

configure_page("Alertas Financeiros")
require_login()
client = get_client()

st.title("Alertas financeiros")
st.caption("Sinais calculados para antecipar desvios e priorizar decisões.")

company = company_selector(load_companies(client), "alerts")
start_date, end_date = period_selector("alerts")

try:
    alerts = client.alerts(company["id"], start_date, end_date)
except DashboardAPIError as exc:
    st.error(str(exc))
    st.stop()

if not alerts:
    st.success("Nenhum alerta financeiro foi identificado no período.")
    st.stop()

counts = Counter(alert["severity"] for alert in alerts)
critical, warning, total = st.columns(3)
critical.metric("Críticos", counts["critical"])
warning.metric("Atenção", counts["warning"])
total.metric("Total", len(alerts))

renderers = {
    "critical": st.error,
    "warning": st.warning,
    "info": st.info,
}
for alert in alerts:
    renderers[alert["severity"]](f"**{alert['title']}** — {alert['message']}")

frame = pd.DataFrame(alerts)
st.dataframe(
    frame[["severity", "reference_date", "title", "message"]].rename(
        columns={
            "severity": "Severidade",
            "reference_date": "Referência",
            "title": "Alerta",
            "message": "Detalhes",
        }
    ),
    width="stretch",
    hide_index=True,
)
