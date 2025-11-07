import streamlit as st
import requests
from utils.utils import (
    setup_page,
    load_css,
    get_auth,
    get_list_recomendar,
    remove_list_recomendar,
    limpar_lista_recomendacao,
    card_filme
)

setup_page(titulo="Recomendador", protegida=True, layout="wide")
load_css(['styles/geral.css', 'styles/components.css', 'styles/badges.css'])

# URLs
API_URL = "http://127.0.0.1:5000"
IMAGEM_URL = "https://image.tmdb.org/t/p/w500"

st.markdown('<h1 class="titulo">Recomendador</h1>',
            unsafe_allow_html=True)
st.markdown('<p class="subtitulo">Adicione filmes para gerar recomendações.</p>',
            unsafe_allow_html=True)

lista_recomendacao = get_list_recomendar()

if not lista_recomendacao:
    st.info("Você ainda não adicionou filmes para basearmos a recomendação!")
    if st.button("Buscar Filmes"):
        st.switch_page("pages/busca_filmes.py")
else:
    st.info(f"Basearemos a recomendação em {len(lista_recomendacao)} filme(s).")

    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("Gerar Recomendações com base nos filmes da lista",
                     width='stretch'):
            with st.spinner("Buscando filmes parecidos..."):
                lista_tmdb_ids = [filme['tmdb_id'] for filme in lista_recomendacao]

                headers = get_auth()

                try:
                    response = requests.post(
                        f"{API_URL}/recomendar/multiplos",  # EM CRIAÇÃO
                        headers=headers,
                        json={"lista_tmdb_ids": lista_tmdb_ids}
                    )
                    response.raise_for_status()
                    resultados = response.json()

                    # AREA TESTE
                    st.divider()
                    st.success("Aqui estão os seus resultados!")
                    st.write(resultados)  # TODO: TESTEE

                except requests.HTTPError:
                    st.error("FUNÇÃO EM CRIAÇÃO")

    with col2:
        if st.button("Limpar lista", width="stretch"):
            limpar_lista_recomendacao()
            st.rerun()

    st.divider()

    cols = st.columns(5, gap="medium")
    for i, filme in enumerate(lista_recomendacao):
        col = cols[i % 5]
        with col:
            with st.container(border=True):
                if st.button("Remover",
                             key=f"rem_{filme['tmdb_id']}",
                             width='content',
                             ):
                    remove_list_recomendar(filme['tmdb_id'])

                card_filme(filme)
