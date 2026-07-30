from decimal import Decimal

import pandas as pd
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

configure_page("Lançamentos")
require_login()
client = get_client()

st.title("Lançamentos financeiros")
st.caption("Consulte, filtre e exporte receitas e despesas cadastradas.")

company = company_selector(load_companies(client), "transactions")
start_date, end_date = period_selector("transactions")

try:
    categories = client.category_options(company["id"])
    accounts = client.account_options(company["id"])
    cost_centers = client.cost_center_options(company["id"])
except DashboardAPIError as exc:
    st.error(str(exc))
    st.stop()

type_labels = {"Todos": None, "Receitas": "revenue", "Despesas": "expense"}
status_labels = {
    "Todos": None,
    "Pago": "paid",
    "Pendente": "pending",
    "Vencido": "overdue",
    "Parcial": "partially_paid",
    "Cancelado": "cancelled",
}
category_lookup = {"Todas": None, **{item["name"]: item["id"] for item in categories}}
account_lookup = {"Todas": None, **{item["name"]: item["id"] for item in accounts}}
center_lookup = {
    "Todos": None,
    **{item["name"]: item["id"] for item in cost_centers},
}

selected_type = st.sidebar.selectbox("Tipo", list(type_labels))
selected_status = st.sidebar.selectbox("Status", list(status_labels))
selected_category = st.sidebar.selectbox("Categoria", list(category_lookup))
selected_account = st.sidebar.selectbox("Conta", list(account_lookup))
selected_center = st.sidebar.selectbox("Centro de custo", list(center_lookup))

try:
    result = client.transactions(
        company["id"],
        start_date,
        end_date,
        type_labels[selected_type],
        status_labels[selected_status],
        category_lookup[selected_category],
        account_lookup[selected_account],
        center_lookup[selected_center],
    )
except DashboardAPIError as exc:
    st.error(str(exc))
    st.stop()

items = result["items"]
if not items:
    st.info("Nenhum lançamento encontrado para os filtros selecionados.")
    st.stop()

frame = pd.DataFrame(items)
frame["amount"] = frame["amount"].astype(float)
revenue = frame.loc[frame["transaction_type"] == "revenue", "amount"].sum()
expense = frame.loc[frame["transaction_type"] == "expense", "amount"].sum()

col1, col2, col3 = st.columns(3)
col1.metric("Lançamentos", result["total"])
col2.metric("Receitas", format_currency(Decimal(str(revenue))))
col3.metric("Despesas", format_currency(Decimal(str(expense))))

category_names = {item["id"]: item["name"] for item in categories}
account_names = {item["id"]: item["name"] for item in accounts}
center_names = {item["id"]: item["name"] for item in cost_centers}
display = frame[
    [
        "competence_date",
        "description",
        "transaction_type",
        "status",
        "amount",
        "category_id",
        "account_id",
        "cost_center_id",
    ]
].copy()
display["category_id"] = display["category_id"].map(category_names)
display["account_id"] = display["account_id"].map(account_names)
display["cost_center_id"] = display["cost_center_id"].map(center_names)
display = display.rename(
    columns={
        "competence_date": "Competência",
        "description": "Descrição",
        "transaction_type": "Tipo",
        "status": "Status",
        "amount": "Valor",
        "category_id": "Categoria",
        "account_id": "Conta",
        "cost_center_id": "Centro de custo",
    }
)
st.dataframe(display, hide_index=True, width="stretch")
st.download_button(
    "Exportar CSV",
    data=display.to_csv(index=False).encode("utf-8-sig"),
    file_name=f"lancamentos-{start_date}-{end_date}.csv",
    mime="text/csv",
)
