from decimal import Decimal

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.api_client import DashboardAPIError
from dashboard.components import (
    company_selector,
    configure_page,
    format_currency,
    get_client,
    load_companies,
    period_selector,
    require_login,
)

configure_page("Planejado vs. Realizado")
require_login()
client = get_client()

st.title("Planejado vs. realizado")
st.caption("Acompanhe o orçamento mensal e identifique os maiores desvios por categoria.")

company = company_selector(load_companies(client), "budget")
start_date, end_date = period_selector("budget")

try:
    comparison = client.budget_comparison(company["id"], start_date, end_date)
except DashboardAPIError as exc:
    st.error(str(exc))
    st.stop()

if not comparison:
    st.info(
        "Não há orçamento no período. Cadastre valores mensais pelo endpoint "
        "`POST /api/v1/budgets` disponível no Swagger."
    )
    st.stop()

frame = pd.DataFrame(comparison)
for column in ("planned_amount", "realized_amount", "variance_amount"):
    frame[column] = frame[column].astype(float)
frame["reference_month"] = pd.to_datetime(frame["reference_month"])

planned = Decimal(str(frame["planned_amount"].sum()))
realized = Decimal(str(frame["realized_amount"].sum()))
variance = realized - planned

col1, col2, col3 = st.columns(3)
col1.metric("Total planejado", format_currency(planned))
col2.metric("Total realizado", format_currency(realized))
col3.metric(
    "Desvio",
    format_currency(variance),
    delta="Acima do plano" if variance > 0 else "Dentro do plano",
    delta_color="inverse" if variance > 0 else "normal",
)

chart_data = frame.melt(
    id_vars=["reference_month", "category_name"],
    value_vars=["planned_amount", "realized_amount"],
    var_name="series",
    value_name="amount",
)
chart_data["series"] = chart_data["series"].map(
    {"planned_amount": "Planejado", "realized_amount": "Realizado"}
)
figure = px.bar(
    chart_data,
    x="reference_month",
    y="amount",
    color="series",
    barmode="group",
    facet_row="category_name",
    labels={"reference_month": "Mês", "amount": "Valor", "series": ""},
    color_discrete_map={"Planejado": "#94A3B8", "Realizado": "#0F766E"},
)
figure.update_layout(height=max(420, frame["category_name"].nunique() * 220))
st.plotly_chart(figure, width="stretch")

display = frame[
    [
        "reference_month",
        "category_name",
        "transaction_type",
        "planned_amount",
        "realized_amount",
        "variance_amount",
        "variance_percentage",
    ]
].rename(
    columns={
        "reference_month": "Mês",
        "category_name": "Categoria",
        "transaction_type": "Tipo",
        "planned_amount": "Planejado",
        "realized_amount": "Realizado",
        "variance_amount": "Desvio",
        "variance_percentage": "Desvio (%)",
    }
)
st.dataframe(display, width="stretch", hide_index=True)
st.download_button(
    "Exportar comparação em CSV",
    data=display.to_csv(index=False).encode("utf-8-sig"),
    file_name="planejado_vs_realizado.csv",
    mime="text/csv",
)
