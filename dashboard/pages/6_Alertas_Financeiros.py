from collections import Counter
from datetime import date

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
workflow_counts = Counter(alert["workflow_status"] for alert in alerts)
critical, warning, open_items, resolved = st.columns(4)
critical.metric("Críticos", counts["critical"])
warning.metric("Atenção", counts["warning"])
open_items.metric("Em aberto", workflow_counts["open"])
resolved.metric("Resolvidos", workflow_counts["resolved"])

renderers = {
    "critical": st.error,
    "warning": st.warning,
    "info": st.info,
}
for alert in alerts:
    status_labels = {
        "open": "Em aberto",
        "acknowledged": "Reconhecido",
        "resolved": "Resolvido",
    }
    renderers[alert["severity"]](
        f"**{alert['title']}** — {alert['message']}  \n"
        f"Status: **{status_labels[alert['workflow_status']]}**"
    )
    with (
        st.expander(f"Registrar tratamento — {alert['title']}"),
        st.form(f"alert_action_{alert['code']}_{alert['reference_date']}"),
    ):
        status_by_label = {label: status for status, label in status_labels.items()}
        status_options: list[str] = list(status_by_label)
        selected_label = st.selectbox(
            "Status",
            options=status_options,
            index=status_options.index(status_labels[alert["workflow_status"]]),
        )
        selected_status = status_by_label[selected_label]
        note = st.text_area(
            "Nota",
            value=alert.get("workflow_note") or "",
            max_chars=500,
            placeholder="Registre a análise ou providência tomada.",
        )
        if st.form_submit_button("Salvar tratamento", type="primary"):
            try:
                client.update_alert_action(
                    company["id"],
                    alert["code"],
                    date.fromisoformat(alert["reference_date"]),
                    start_date,
                    end_date,
                    selected_status,
                    note,
                )
            except DashboardAPIError as exc:
                st.error(str(exc))
            else:
                st.success("Tratamento registrado.")
                st.rerun()

frame = pd.DataFrame(alerts)
st.dataframe(
    frame[
        [
            "severity",
            "workflow_status",
            "reference_date",
            "title",
            "message",
            "workflow_note",
        ]
    ].rename(
        columns={
            "severity": "Severidade",
            "workflow_status": "Tratamento",
            "reference_date": "Referência",
            "title": "Alerta",
            "message": "Detalhes",
            "workflow_note": "Nota",
        }
    ),
    width="stretch",
    hide_index=True,
)
