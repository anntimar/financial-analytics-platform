from decimal import Decimal

import pandas as pd
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

configure_page("Previsões e Anomalias")
require_login()
client = get_client()

st.title("Previsões e anomalias")
st.caption("Modelos exploratórios e explicáveis aplicados aos dados financeiros sintéticos.")

company = company_selector(load_companies(client), "predictive")
start_date, end_date = period_selector("predictive")
horizon = st.sidebar.slider("Horizonte da previsão (meses)", 1, 6, 3)

try:
    forecast = client.revenue_forecast(company["id"], start_date, end_date, horizon)
    anomalies = client.expense_anomalies(company["id"], start_date, end_date)
    history = client.monthly(company["id"], start_date, end_date)
except DashboardAPIError as exc:
    st.error(str(exc))
    st.stop()

metrics = forecast["metrics"]
col1, col2, col3, col4 = st.columns(4)
col1.metric("Meses de histórico", forecast["historical_months"])
col2.metric("MAE", format_currency(metrics["mae"]))
col3.metric("RMSE", format_currency(metrics["rmse"]))
col4.metric("MAPE", format_percentage(metrics["mape_percentage"]))

st.subheader("Previsão de receita")
history_df = pd.DataFrame(history)
forecast_df = pd.DataFrame(forecast["forecast"])
figure = go.Figure()
if not history_df.empty:
    history_df["reference_month"] = pd.to_datetime(history_df["reference_month"])
    figure.add_trace(
        go.Scatter(
            x=history_df["reference_month"],
            y=history_df["total_revenue"].astype(float),
            name="Receita histórica",
            line={"color": "#0F766E", "width": 3},
        )
    )
if not forecast_df.empty:
    forecast_df["reference_month"] = pd.to_datetime(forecast_df["reference_month"])
    figure.add_trace(
        go.Scatter(
            x=forecast_df["reference_month"],
            y=forecast_df["upper_bound"].astype(float),
            line={"width": 0},
            showlegend=False,
        )
    )
    figure.add_trace(
        go.Scatter(
            x=forecast_df["reference_month"],
            y=forecast_df["lower_bound"].astype(float),
            name="Intervalo estimado",
            fill="tonexty",
            fillcolor="rgba(20, 184, 166, 0.18)",
            line={"width": 0},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=forecast_df["reference_month"],
            y=forecast_df["predicted_revenue"].astype(float),
            name="Receita prevista",
            line={"color": "#F97316", "width": 3, "dash": "dash"},
        )
    )
figure.update_layout(hovermode="x unified", legend_title_text="", yaxis_title="Receita (R$)")
st.plotly_chart(figure, width="stretch")
st.caption(f"Método: {forecast['method']}. {forecast['limitation']}")

st.divider()
st.subheader("Despesas fora do padrão")
if anomalies:
    anomaly_df = pd.DataFrame(anomalies)
    anomaly_df["Valor"] = anomaly_df["amount"].map(format_currency)
    anomaly_df["Mediana da categoria"] = anomaly_df["category_median"].map(format_currency)
    anomaly_df["Desvio"] = anomaly_df["deviation_percentage"].map(format_percentage)
    st.metric("Anomalias identificadas", len(anomalies))
    st.dataframe(
        anomaly_df[
            [
                "competence_date",
                "category_name",
                "description",
                "Valor",
                "Mediana da categoria",
                "Desvio",
                "explanation",
            ]
        ].rename(
            columns={
                "competence_date": "Data",
                "category_name": "Categoria",
                "description": "Descrição",
                "explanation": "Explicação",
            }
        ),
        width="stretch",
        hide_index=True,
    )
    largest = max(Decimal(item["amount"]) for item in anomalies)
    st.caption(f"Maior despesa anômala no período: {format_currency(largest)}.")
else:
    st.success("Nenhuma despesa acima do limite estatístico foi encontrada no período.")
