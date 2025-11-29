import streamlit as st
from time import sleep
from utils.utils import (
    validar_senha,
    setup_page,
    load_css,
    setup_header,
    api_request
)

setup_page(titulo="Redefinição de senha", hide_sidebar=True)
load_css(["styles/geral.css", "styles/components.css"])
token = st.query_params.get("token")

# Verifica o token
if not token:
    st.error("Token de redefinição não encontrado na URL.")
    st.info("Use o link enviado para o seu email.")
    sleep(3)
    st.switch_page("app.py")
else:
    setup_header("Crie sua nova senha")

    with st.form("redefinir_form"):
        nova_senha = st.text_input(
            "Nova Senha",
            type="password",
            placeholder="Mínimo 6 caracteres, com letras e números"
        )
        confirmar_senha = st.text_input(
            "Confirmar Nova Senha",
            type="password",
            placeholder="Digite a senha novamente"
        )

        submitted = st.form_submit_button("Alterar Senha")

        if submitted:
            senha_valida, msg_validacao = validar_senha(nova_senha)

            if not nova_senha or not confirmar_senha:
                st.error("Por favor, preencha ambos os campos.")
            elif not senha_valida:
                st.error(f"Senha inválida: {msg_validacao}")
            elif nova_senha != confirmar_senha:
                st.error("As senhas não coincidem.")
            else:
                payload = {"token": token, "new_pw": nova_senha}
                with st.spinner("Atualizando sua senha..."):
                    resp = api_request("POST", "redefinir", json=payload)

                if resp:
                    st.success("Senha redefinida com sucesso! ✅")
                    st.info("Você já pode fazer login com sua nova senha.")
                    sleep(4)
                    st.switch_page("app.py")
