import streamlit as st
from utils.utils import (
    setup_page,
    load_css,
    remover_favorito,
    carregar_favoritos,
    card_filme
)

setup_page(titulo="Meus Favoritos", protegida=True, layout="wide")
load_css(['styles/geral.css', 'styles/components.css', 'styles/badges.css'])

# URLs
API_URL = "http://127.0.0.1:5000"
IMAGEM_URL = "https://image.tmdb.org/t/p/w500"

st.markdown('<h1 class="titulo">❤️Filmes Favoritos</h1>',
            unsafe_allow_html=True)
st.markdown('<p class="subtitulo">Seus filmes favoritos.</p>',
            unsafe_allow_html=True)
st.divider()

favoritos = carregar_favoritos()

if favoritos is not None:
    if not favoritos:
        st.info("Você ainda não adicionou nenhum filme aos favoritos."
                " Busque no botão abaixo")
        if st.button("Buscar Filmes"):
            st.switch_page("pages/busca_filmes.py")
    else:
        st.markdown(
            f'<div class="result-count">Você tem {len(favoritos)} filme(s) na sua lista.</div>',
            unsafe_allow_html=True
        )

        cols = st.columns(5, gap="medium")
        for i, filme in enumerate(favoritos):
            col = cols[i % 5]
            with col:
                with st.container(border=True):
                    if st.button("Remover",
                                 key=f"rem_{filme['tmdb_id']}",
                                 width='content',
                                 type="primary"):
                        remover_favorito(filme['tmdb_id'])

                    card_filme(filme)
