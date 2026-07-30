import json
from decimal import Decimal

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.api_client import DashboardAPIError
from dashboard.components import (
    company_selector,
    configure_page,
    format_currency,
    format_percentage,
    get_client,
    load_companies,
    period_selector,
    require_login,
)

configure_page("Visão Executiva")
require_login()
client = get_client()

st.title("Visão executiva")
st.caption("Principais indicadores financeiros e sua evolução no período.")

company = company_selector(load_companies(client), "executive")
start_date, end_date = period_selector("executive")

try:
    summary = client.executive_summary(company["id"], start_date, end_date)
    monthly = client.monthly(company["id"], start_date, end_date)
    categories = client.categories(company["id"], start_date, end_date)
    cash_flow = client.cash_flow(company["id"], start_date, end_date)
    overdue = client.overdue(company["id"], start_date, end_date)
    report = client.executive_report(company["id"], start_date, end_date)
    report_csv = client.executive_report_csv(company["id"], start_date, end_date)
except DashboardAPIError as exc:
    st.error(str(exc))
    st.stop()

revenue = Decimal(summary["realized_revenue"])
expense = Decimal(summary["realized_expense"])
result = Decimal(summary["net_result"])

col1, col2, col3, col4 = st.columns(4)
col1.metric("Receita realizada", format_currency(revenue))
col2.metric("Despesa realizada", format_currency(expense))
col3.metric(
    "Resultado",
    format_currency(result),
    delta="Positivo" if result >= 0 else "Negativo",
    delta_color="normal" if result >= 0 else "inverse",
)
col4.metric("Margem", format_percentage(summary["margin_percentage"]))

col5, col6, col7 = st.columns(3)
col5.metric("A receber", format_currency(summary["pending_receivables"]))
col6.metric("Valor vencido", format_currency(overdue["overdue_amount"]))
col7.metric(
    "Taxa de inadimplência",
    format_percentage(overdue["delinquency_rate_percentage"]),
)

st.divider()
left, right = st.columns((2, 1))

with left:
    st.subheader("Receitas e despesas por mês")
    if monthly:
        monthly_df = pd.DataFrame(monthly)
        monthly_df["reference_month"] = pd.to_datetime(monthly_df["reference_month"])
        monthly_df["Receitas"] = monthly_df["total_revenue"].astype(float)
        monthly_df["Despesas"] = monthly_df["total_expense"].astype(float)
        chart_df = monthly_df.melt(
            id_vars="reference_month",
            value_vars=["Receitas", "Despesas"],
            var_name="Tipo",
            value_name="Valor",
        )
        figure = px.bar(
            chart_df,
            x="reference_month",
            y="Valor",
            color="Tipo",
            barmode="group",
            color_discrete_map={"Receitas": "#14B8A6", "Despesas": "#F97316"},
            labels={"reference_month": "Mês"},
        )
        figure.update_layout(legend_title_text="", hovermode="x unified")
        st.plotly_chart(figure, width="stretch")
    else:
        st.info("Não há movimentações no período selecionado.")

with right:
    st.subheader("Despesas por categoria")
    if categories:
        categories_df = pd.DataFrame(categories)
        figure = px.pie(
            categories_df,
            names="category_name",
            values="total_amount",
            hole=0.58,
            color_discrete_sequence=px.colors.sequential.Teal,
        )
        figure.update_traces(textposition="inside", textinfo="percent+label")
        figure.update_layout(showlegend=False)
        st.plotly_chart(figure, width="stretch")
    else:
        st.info("Não há despesas pagas no período.")

st.subheader("Fluxo de caixa acumulado")
if cash_flow:
    cash_df = pd.DataFrame(cash_flow)
    cash_df["reference_month"] = pd.to_datetime(cash_df["reference_month"])
    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=cash_df["reference_month"],
            y=cash_df["net_cash_flow"].astype(float),
            name="Fluxo mensal",
            marker_color="#94A3B8",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=cash_df["reference_month"],
            y=cash_df["accumulated_cash_flow"].astype(float),
            name="Acumulado",
            line={"color": "#0F766E", "width": 3},
        )
    )
    figure.update_layout(hovermode="x unified", legend_title_text="")
    st.plotly_chart(figure, width="stretch")
else:
    st.info("Não há dados de fluxo de caixa no período.")

st.divider()
st.subheader("Exportar relatório executivo")
st.caption("Baixe o consolidado do período para análise, auditoria ou compartilhamento.")
csv_col, json_col = st.columns(2)
csv_col.download_button(
    "Baixar CSV",
    data=report_csv,
    file_name=f"relatorio-executivo-{start_date}-{end_date}.csv",
    mime="text/csv",
    width="stretch",
)
json_col.download_button(
    "Baixar JSON",
    data=json.dumps(report, ensure_ascii=False, indent=2).encode(),
    file_name=f"relatorio-executivo-{start_date}-{end_date}.json",
    mime="application/json",
    width="stretch",
)
