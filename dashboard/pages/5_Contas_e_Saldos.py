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

configure_page("Contas e Saldos")
require_login()
client = get_client()

st.title("Contas e saldos")
st.caption("Saldos por conta a partir do saldo inicial e das movimentações pagas.")

company = company_selector(load_companies(client), "accounts")
start_date, end_date = period_selector("accounts")

try:
    balances = client.account_balances(company["id"], start_date, end_date)
except DashboardAPIError as exc:
    st.error(str(exc))
    st.stop()

if not balances:
    st.info("Nenhuma conta ativa foi cadastrada. Use o endpoint `/api/v1/accounts` no Swagger.")
    st.stop()

frame = pd.DataFrame(balances)
for column in ("opening_balance", "inflows", "outflows", "current_balance"):
    frame[column] = frame[column].astype(float)

total = Decimal(str(frame["current_balance"].sum()))
inflows = Decimal(str(frame["inflows"].sum()))
outflows = Decimal(str(frame["outflows"].sum()))

col1, col2, col3 = st.columns(3)
col1.metric("Saldo consolidado", format_currency(total))
col2.metric("Entradas no período", format_currency(inflows))
col3.metric("Saídas no período", format_currency(outflows))

figure = px.bar(
    frame,
    x="account_name",
    y="current_balance",
    color="account_type",
    labels={
        "account_name": "Conta",
        "current_balance": "Saldo",
        "account_type": "Tipo",
    },
    color_discrete_sequence=px.colors.sequential.Teal,
)
st.plotly_chart(figure, width="stretch")

st.dataframe(
    frame.rename(
        columns={
            "account_name": "Conta",
            "account_type": "Tipo",
            "opening_balance": "Saldo inicial",
            "inflows": "Entradas",
            "outflows": "Saídas",
            "current_balance": "Saldo atual",
        }
    ),
    width="stretch",
    hide_index=True,
)
