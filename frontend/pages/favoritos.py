import streamlit as st
from utils.utils import (
    setup_page,
    load_css,
    remover_favorito,
    setup_header,
    msg_lista_vazia,
    grid_filme,
    add_list_recomendar,
    carregar_favoritos
)

setup_page(titulo="Meus Favoritos", protegida=True, layout="wide")
load_css(['styles/geral.css', 'styles/components.css', 'styles/badges.css',
          'styles/sidebar.css'])
setup_header("Filmes Favoritos", "Seus filmes favoritos.", "❤️")


def button_remover(filme):
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Remover",
                     key=f"rem_{filme['tmdb_id']}",
                     width='stretch',
                     type="primary"):
            remover_favorito(filme['tmdb_id'])
    with col2:
        if st.button(
            "Recomendar",
            key=f"add_{filme['tmdb_id']}",
            width='stretch',
        ):
            add_list_recomendar(filme)


favoritos = carregar_favoritos()

if favoritos is not None:
    if not favoritos:
        msg_lista_vazia("Você ainda não adicionou nenhum filme aos favoritos.")
    else:
        st.markdown(
            f'<div class="result-count">Você tem {len(favoritos)} filme(s) na sua lista.</div>',
            unsafe_allow_html=True
        )

        grid_filme(favoritos, 4, button=button_remover, contexto='fav')
