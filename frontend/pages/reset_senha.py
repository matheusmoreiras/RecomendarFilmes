import streamlit as st
from utils.utils import (
    validar_email,
    setup_page,
    load_css,
    setup_header,
    api_request
)

setup_page(titulo="Esqueci minha senha", hide_sidebar=True)
load_css(["styles/geral.css", "styles/components.css"])
setup_header("Recupere sua senha",
             "Informe seu email para recuperação")

with st.form("reset_form"):
    email = st.text_input("Email", placeholder="Digite seu email")
    submitted = st.form_submit_button("Enviar", width='stretch')

    if submitted:
        if not email or not validar_email(email):
            st.error("Digite um email válido!")
        else:
            resp = api_request("POST", "reset_senha", json={"email": email})
            if resp:
                if resp.get("success"):
                    st.success("Se este email estiver cadastrado, enviaremos"
                               " instruções de redefinição.")
                else:
                    st.error(
                        f"Erro: {resp.get('message', 'Falha na redefinição')}")

if st.button("Voltar para Login", width='stretch'):
    st.switch_page("app.py")
