import streamlit as st

from dashboard.api_client import DashboardAPIError
from dashboard.components import configure_page, get_client

configure_page("Início")
client = get_client()

st.title("FinAnalytics")
st.caption("Dados financeiros transformados em decisões claras.")

try:
    health = client.health()
    if health["status"] == "healthy":
        st.success("API e PostgreSQL conectados.", icon="✅")
    else:
        st.warning("API ativa, mas o PostgreSQL está indisponível.", icon="⚠️")
except DashboardAPIError as exc:
    st.error(str(exc), icon="🚨")

st.markdown(
    """
    ### Uma visão financeira completa

    A plataforma centraliza receitas, despesas e dados importados, aplica regras de
    qualidade e disponibiliza indicadores gerenciais em uma experiência navegável.
    """
)

col1, col2, col3 = st.columns(3)
with col1:
    st.info("**Visão executiva**\n\nKPIs, evolução mensal e composição por categoria.")
with col2:
    st.info("**Fluxo de caixa**\n\nEntradas, saídas, saldo mensal e resultado acumulado.")
with col3:
    st.info("**Qualidade de dados**\n\nImportação CSV, rejeições e rastreabilidade por lote.")

st.markdown(
    """
    Use o menu lateral para abrir a visão executiva ou importar dados. Para começar,
    cadastre uma empresa e suas categorias pela documentação da API em
    [http://localhost:8000/docs](http://localhost:8000/docs).
    """
)
