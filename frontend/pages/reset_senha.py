import streamlit as st
import requests
from utils.utils import validar_email, setup_page, load_css

setup_page(titulo="Esqueci minha senha", hide_sidebar=True)
load_css(["styles/geral.css", "styles/components.css"])
API_URL = "http://127.0.0.1:5000"
URL_RESET = f"{API_URL}/reset_senha"


def solicitar_reset(email: str):
    try:
        response = requests.post(URL_RESET, json={"email": email}, timeout=10)
        return response.status_code, response.json()
    except requests.exceptions.RequestException as e:
        return 500, {"success": False, "message": f"Erro de conexão: {e}"}


st.markdown('<h1 class="titulo">Recupere sua senha</h1>',
            unsafe_allow_html=True)
st.markdown('<p class="subtitulo">Informe seu email para recuperação</p>',
            unsafe_allow_html=True)

with st.form("reset_form"):
    email = st.text_input("Email", placeholder="Digite seu email")
    submitted = st.form_submit_button("Enviar", width='stretch')

    if submitted:
        if not email or not validar_email(email):
            st.error("Digite um email válido!")
        else:
            status, resp = solicitar_reset(email)
            if status == 200 and resp.get("success"):
                st.success("Se este email estiver cadastrado, enviaremos"
                           " instruções de redefinição.")
            else:
                st.error(f"Erro: {resp.get('message','Falha ao solicitar redefinição')}")

if st.button("Voltar para Login", width='stretch'):
    st.switch_page("app.py")
