import streamlit as st
from utils.utils import (
    setup_page,
    get_auth,
    grid_filme,
    setup_header,
    load_css,
    api_request
)

load_css(['styles/geral.css', 'styles/components.css', 'styles/badges.css',
          'styles/sidebar.css'])
setup_page(titulo="Recomendações Para Você", protegida=True, layout="wide")
setup_header(" Para Você",
             "Com base no seu histórico e no gosto de usuários parecidos.")

if st.button("Gerar Recomendações Personalizadas",
             type="primary",
             use_container_width=True):
    headers = get_auth()

    with st.spinner("Consultando o oráculo de filmes..."):
        filmes = api_request(
            "GET", "recomendar/hibrido", ignore_status=[404], headers=headers)

        if filmes is not None:
            if isinstance(filmes, dict) and filmes.get("success") is False:
                st.info(
                    "Ainda não temos dados suficientes sobre você."
                    " Avalie mais filmes!")
            else:
                st.session_state['foryou'] = filmes

if st.session_state.get('foryou'):
    st.success("Aqui estão filmes que achamos que você vai dar 5 estrelas!")
    grid_filme(st.session_state['foryou'], 5, contexto='for_you')


st.header("Descobertas")
st.caption("Filmes que pessoas com gosto parecido com o seu adoraram."
           " Quanto mais filmes avaliados, melhor a recomendação.")

if st.button("Carregar Descobertas", type="secondary"):
    headers = get_auth()
    with st.spinner("Analisando padrões ocultos..."):
        filmes_svd = api_request(
            "GET",
            "recomendar/colaborativo",
            headers=headers,
            timeout=30)

        if filmes_svd:
            grid_filme(filmes_svd, 5, contexto='colaborativo')
