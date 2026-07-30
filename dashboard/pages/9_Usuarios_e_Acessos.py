import pandas as pd
import streamlit as st

from dashboard.api_client import DashboardAPIError
from dashboard.components import configure_page, get_client, load_companies, require_login

configure_page("Usuários e Acessos")
require_login()

current_user = st.session_state.get("user", {})
if current_user.get("role") != "admin":
    st.warning("Esta página é exclusiva para administradores.")
    st.stop()

client = get_client()
companies = load_companies(client)
company_by_name = {company["name"]: company for company in companies}
company_name_by_id = {company["id"]: company["name"] for company in companies}
role_labels = {"admin": "Administrador", "analyst": "Analista", "manager": "Gestor"}
role_by_label = {label: role for role, label in role_labels.items()}

st.title("Usuários e acessos")
st.caption("Crie acessos, altere perfis e controle quais usuários permanecem ativos.")

try:
    users = client.users()
except DashboardAPIError as exc:
    st.error(str(exc))
    st.stop()

active_count = sum(user["is_active"] for user in users)
col1, col2, col3 = st.columns(3)
col1.metric("Usuários", len(users))
col2.metric("Ativos", active_count)
col3.metric("Inativos", len(users) - active_count)

create_tab, manage_tab = st.tabs(["Novo usuário", "Gerenciar acessos"])

with create_tab:
    with st.form("create_user"):
        name = st.text_input("Nome")
        email = st.text_input("E-mail")
        password = st.text_input("Senha inicial", type="password")
        role_label = st.selectbox("Perfil", list(role_by_label))
        role = role_by_label[role_label]
        company_options = list(company_by_name) if role != "admin" else ["Sem vínculo"]
        company_name = st.selectbox("Empresa", company_options)
        submitted = st.form_submit_button("Criar usuário", type="primary")
    if submitted:
        company_id = company_by_name[company_name]["id"] if role != "admin" else None
        try:
            client.create_user(name, email, password, role, company_id)
        except DashboardAPIError as exc:
            st.error(str(exc))
        else:
            st.success("Usuário criado com sucesso.")
            st.rerun()

with manage_tab:
    if not users:
        st.info("Nenhum usuário cadastrado.")
    else:
        user_lookup = {f"{user['name']} · {user['email']}": user for user in users}
        selected_label = st.selectbox("Usuário", list(user_lookup))
        selected = user_lookup[selected_label]
        selected_role_label = role_labels[selected["role"]]
        with st.form("update_user"):
            updated_name = st.text_input("Nome", value=selected["name"])
            updated_role_label = st.selectbox(
                "Perfil",
                list(role_by_label),
                index=list(role_by_label).index(selected_role_label),
            )
            updated_role = role_by_label[updated_role_label]
            edit_company_options = (
                list(company_by_name) if updated_role != "admin" else ["Sem vínculo"]
            )
            current_company = company_name_by_id.get(selected["company_id"])
            company_index = (
                edit_company_options.index(current_company)
                if current_company in edit_company_options
                else 0
            )
            updated_company_name = st.selectbox(
                "Empresa",
                edit_company_options,
                index=company_index,
            )
            updated_active = st.checkbox("Acesso ativo", value=selected["is_active"])
            updated = st.form_submit_button("Salvar alterações", type="primary")
        if updated:
            updated_company_id = (
                company_by_name[updated_company_name]["id"] if updated_role != "admin" else None
            )
            try:
                client.update_user(
                    selected["id"],
                    name=updated_name,
                    role=updated_role,
                    company_id=updated_company_id,
                    is_active=updated_active,
                )
            except DashboardAPIError as exc:
                st.error(str(exc))
            else:
                st.success("Acesso atualizado com sucesso.")
                st.rerun()

if users:
    frame = pd.DataFrame(users)
    frame["role"] = frame["role"].map(role_labels)
    frame["company_id"] = frame["company_id"].map(company_name_by_id).fillna("Todas")
    frame["is_active"] = frame["is_active"].map({True: "Ativo", False: "Inativo"})
    st.dataframe(
        frame[["name", "email", "role", "company_id", "is_active"]].rename(
            columns={
                "name": "Nome",
                "email": "E-mail",
                "role": "Perfil",
                "company_id": "Empresa",
                "is_active": "Status",
            }
        ),
        hide_index=True,
        width="stretch",
    )
