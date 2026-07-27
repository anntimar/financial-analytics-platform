import os
from datetime import date
from decimal import Decimal
from typing import Any

import streamlit as st

from dashboard.api_client import DashboardAPIError, FinAnalyticsClient


@st.cache_resource
def _client(base_url: str, access_token: str | None) -> FinAnalyticsClient:
    return FinAnalyticsClient(base_url, access_token=access_token)


def get_client() -> FinAnalyticsClient:
    base_url = dashboard_api_url()
    return _client(base_url, st.session_state.get("access_token"))


def dashboard_api_url() -> str:
    value = os.getenv("DASHBOARD_API_URL", "http://localhost:8000/api/v1").rstrip("/")
    if not value.startswith(("http://", "https://")):
        value = f"http://{value}"
    if not value.endswith("/api/v1"):
        value = f"{value}/api/v1"
    return value


def require_login() -> None:
    if st.session_state.get("access_token"):
        user = st.session_state.get("user", {})
        st.sidebar.success(f"Conectado como {user.get('name', 'usuário')}")
        if st.sidebar.button("Sair"):
            st.session_state.pop("access_token", None)
            st.session_state.pop("user", None)
            st.rerun()
        return

    st.title("Acesso ao FinAnalytics")
    st.caption("Entre com seu usuário para acessar os dados financeiros.")
    with st.form("login"):
        email = st.text_input("E-mail")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar", type="primary")
    if submitted:
        base_url = dashboard_api_url()
        try:
            result = FinAnalyticsClient(base_url).login(email, password)
        except DashboardAPIError as exc:
            st.error(str(exc))
        else:
            st.session_state["access_token"] = result["access_token"]
            st.session_state["user"] = result["user"]
            st.rerun()
    st.info("O primeiro administrador pode ser criado em `/api/v1/auth/bootstrap` no Swagger.")
    st.stop()


def configure_page(title: str) -> None:
    st.set_page_config(
        page_title=f"{title} | FinAnalytics",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def format_currency(value: Any) -> str:
    amount = Decimal(str(value or 0))
    formatted = f"{amount:,.2f}"
    return f"R$ {formatted.replace(',', 'X').replace('.', ',').replace('X', '.')}"


def format_percentage(value: Any) -> str:
    if value is None:
        return "—"
    return f"{Decimal(str(value)):.2f}%".replace(".", ",")


def load_companies(client: FinAnalyticsClient) -> list[dict[str, Any]]:
    try:
        return client.companies()
    except DashboardAPIError as exc:
        st.error(str(exc))
        st.stop()


def company_selector(companies: list[dict[str, Any]], key: str = "company") -> dict[str, Any]:
    if not companies:
        st.warning(
            "Nenhuma empresa ativa foi encontrada. Cadastre uma empresa pela API "
            "antes de usar o dashboard."
        )
        st.stop()
    lookup = {company["name"]: company for company in companies}
    selected_name = st.sidebar.selectbox("Empresa", options=list(lookup), key=f"{key}_selector")
    return lookup[selected_name]


def period_selector(key: str = "period") -> tuple[date, date]:
    today = date.today()
    default_start = date(today.year - 1, today.month, 1)
    start_date = st.sidebar.date_input("Data inicial", value=default_start, key=f"{key}_start")
    end_date = st.sidebar.date_input("Data final", value=today, key=f"{key}_end")
    if start_date > end_date:
        st.sidebar.error("A data inicial deve ser anterior à data final.")
        st.stop()
    return start_date, end_date


def status_badge(status: str) -> str:
    labels = {
        "completed": "✅ Concluído",
        "completed_with_errors": "⚠️ Concluído com rejeições",
        "processing": "⏳ Processando",
        "failed": "❌ Falhou",
    }
    return labels.get(status, status)
