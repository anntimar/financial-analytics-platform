import pandas as pd
import streamlit as st

from dashboard.api_client import DashboardAPIError
from dashboard.components import (
    company_selector,
    configure_page,
    get_client,
    load_companies,
    require_login,
    status_badge,
)

configure_page("Importações")
require_login()
client = get_client()

st.title("Importações e qualidade")
st.caption("Envie transações em CSV e acompanhe validações e rejeições.")

company = company_selector(load_companies(client), "imports")

with st.container(border=True):
    st.subheader("Nova importação")
    uploaded_file = st.file_uploader(
        "Arquivo CSV",
        type=["csv"],
        help="Limite de 5 MB. Use UTF-8 e o modelo disponível no repositório.",
    )
    if uploaded_file and st.button("Importar transações", type="primary", width="stretch"):
        try:
            batch = client.import_transactions(
                company["id"], uploaded_file.name, uploaded_file.getvalue()
            )
            st.success(
                f"Importação concluída: {batch['valid_rows']} válidas e "
                f"{batch['rejected_rows']} rejeitadas."
            )
            st.cache_data.clear()
        except DashboardAPIError as exc:
            st.error(str(exc))

st.subheader("Histórico")
try:
    imports = client.imports(company["id"])
except DashboardAPIError as exc:
    st.error(str(exc))
    st.stop()

if not imports["items"]:
    st.info("Nenhuma importação registrada para esta empresa.")
    st.stop()

history = pd.DataFrame(imports["items"])
history["status"] = history["status"].map(status_badge)
history = history.rename(
    columns={
        "file_name": "Arquivo",
        "status": "Status",
        "total_rows": "Total",
        "valid_rows": "Válidas",
        "rejected_rows": "Rejeitadas",
        "started_at": "Início",
    }
)
st.dataframe(
    history[["Arquivo", "Status", "Total", "Válidas", "Rejeitadas", "Início"]],
    hide_index=True,
    width="stretch",
)

batch_options = {f"{item['file_name']} — {item['started_at']}": item for item in imports["items"]}
selected_label = st.selectbox(
    "Inspecionar rejeições", options=["Selecione um lote", *batch_options]
)
if selected_label != "Selecione um lote":
    selected_batch = batch_options[selected_label]
    try:
        issues = client.import_issues(selected_batch["id"])
    except DashboardAPIError as exc:
        st.error(str(exc))
    else:
        if issues["items"]:
            issues_df = pd.DataFrame(issues["items"]).rename(
                columns={
                    "row_number": "Linha",
                    "field_name": "Campo",
                    "issue_type": "Código",
                    "issue_description": "Problema",
                    "raw_value": "Valor original",
                    "severity": "Severidade",
                }
            )
            st.dataframe(
                issues_df[
                    [
                        "Linha",
                        "Campo",
                        "Código",
                        "Problema",
                        "Valor original",
                        "Severidade",
                    ]
                ],
                hide_index=True,
                width="stretch",
            )
        else:
            st.success("Este lote não possui rejeições.")
