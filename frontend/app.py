import streamlit as st
from utils.utils import (
    setup_page,
    load_css,
    is_logged_in,
    setup_header,
    api_request
)

# Configuração da página
setup_page(titulo="RotaCine Login", hide_sidebar=True)
load_css(["styles/components.css", "styles/geral.css"])


# Checar o login
def check_login(username, password):
    payload = {'username': username, "password": password}
    return api_request('POST', 'login', json=payload, ignore_status=[401])


def main():
    # Verificar se já está logado
    if is_logged_in():
        st.switch_page("pages/busca_filmes.py")

    # Interface de Login
    setup_header("RotaCine", "Faça seu login para continuar", "🎬 ")
    st.markdown("Descubra novos filmes personalizados para você!")

    # Colunas do front end
    col1, col2 = st.columns([2, 1], gap="large")

    with col1:
        with st.container():
            with st.form("login_form"):
                st.markdown("#### Acesse sua conta")
                username = st.text_input(
                    "Nome de usuário",
                    placeholder="Digite seu usuário",
                    help="Insira seu nome de usuário"
                )
                password = st.text_input(
                    "Senha",
                    type="password",
                    placeholder="Digite sua senha",
                    help="Insira sua senha"
                )

                st.markdown("<br>", unsafe_allow_html=True)
                submitted = st.form_submit_button("Entrar", width='stretch')

                if submitted:
                    if not username or not password:
                        st.error(" Por favor, preencha todos os campos!")
                    else:
                        with st.spinner("Autenticando..."):
                            resultado = check_login(username, password)

                        if resultado.get("success"):
                            st.session_state["access_token"] = resultado.get(
                                'access_token')
                            st.session_state["username"] = username
                            st.success("Login realizado com sucesso!")
                            st.rerun()
                        else:
                            st.error(
                                f"{resultado.get('message', 'Falha login')}")

        st.divider()
        if st.button("Esqueci minha senha", width='stretch'):
            st.switch_page("pages/reset_senha.py")

    with col2:
        with st.container():
            st.info("Não tem conta?")
            if st.button("Criar Conta", width='stretch'):
                st.switch_page("pages/cadastro.py")


if __name__ == "__main__":
    main()
