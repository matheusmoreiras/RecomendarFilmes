import streamlit as st
from utils.utils import (
    setup_page,
    load_css,
    remover_favorito,
    carregar_favoritos,
    setup_header,
    msg_lista_vazia,
    grid_filme
)

setup_page(titulo="Meus Favoritos", protegida=True, layout="wide")
load_css(['styles/geral.css', 'styles/components.css', 'styles/badges.css'])
setup_header("Filmes Favoritos", "Seus filmes favoritos.", "❤️")
st.divider()


def button_remover(filme):
    if st.button("Remover",
                 key=f"rem_{filme['tmdb_id']}",
                 width='content',
                 type="primary"):
        remover_favorito(filme['tmdb_id'])


favoritos = carregar_favoritos()

if favoritos is not None:
    if not favoritos:
        msg_lista_vazia("Você ainda não adicionou nenhum filme aos favoritos.")
    else:
        st.markdown(
            f'<div class="result-count">Você tem {len(favoritos)} filme(s) na sua lista.</div>',
            unsafe_allow_html=True
        )

        grid_filme(favoritos, 5, button=button_remover)
