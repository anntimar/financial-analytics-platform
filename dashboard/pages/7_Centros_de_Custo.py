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

configure_page("Centros de Custo")
require_login()
client = get_client()

st.title("Despesas por centro de custo")
st.caption("Distribuição das despesas pagas entre áreas e unidades internas.")

company = company_selector(load_companies(client), "cost_center_analytics")
start_date, end_date = period_selector("cost_center_analytics")

try:
    items = client.cost_centers(company["id"], start_date, end_date)
except DashboardAPIError as exc:
    st.error(str(exc))
    st.stop()

if not items:
    st.info("Não há despesas pagas vinculadas a centros de custo no período.")
    st.stop()

frame = pd.DataFrame(items)
frame["total_amount"] = frame["total_amount"].astype(float)
total = frame["total_amount"].sum()

col1, col2 = st.columns(2)
col1.metric("Despesa alocada", format_currency(total))
col2.metric("Centros com movimento", len(frame))

figure = px.bar(
    frame,
    x="cost_center_name",
    y="total_amount",
    color="share_percentage",
    labels={
        "cost_center_name": "Centro de custo",
        "total_amount": "Despesa",
        "share_percentage": "Participação (%)",
    },
    color_continuous_scale="Teal",
)
st.plotly_chart(figure, width="stretch")
st.dataframe(
    frame.rename(
        columns={
            "cost_center_name": "Centro de custo",
            "cost_center_code": "Código",
            "total_amount": "Total",
            "transaction_count": "Lançamentos",
            "share_percentage": "Participação (%)",
        }
    ),
    hide_index=True,
    width="stretch",
)
