import streamlit as st
from utils.utils import (
    setup_page,
    load_css,
    setup_header,
    get_auth,
    grid_filme,
    msg_lista_vazia,
    add_favorito,
    add_list_recomendar,
    api_request
)

setup_page(titulo="Minhas Avaliações", protegida=True, layout="wide")
load_css(['styles/geral.css', 'styles/components.css', 'styles/badges.css',
          'styles/sidebar.css'])
setup_header("Histórico de Avaliações", "Filmes que você já classificou.", "⭐")


def fav_recomendar_button(filme):
    col1, col2 = st.columns(2)
    favoritado = filme.get("favoritos", False)

    with col1:
        texto_botao = "Favoritado" if favoritado else "Favoritar"
        if st.button(
            texto_botao,
            key=f"fav_{filme['tmdb_id']}",
            width='stretch',
            disabled=favoritado,
        ):
            add_favorito(filme['tmdb_id'])
    with col2:
        if st.button(
            "Recomendar",
            key=f"add_{filme['tmdb_id']}",
            width='stretch',
        ):
            add_list_recomendar(filme)


def carregar_filmes_avaliados():
    headers = get_auth()
    dados = api_request('GET', 'usuario/minhas-avaliacoes', headers=headers)
    return dados if dados else []


filmes_avaliados = carregar_filmes_avaliados()

if not filmes_avaliados:
    msg_lista_vazia("Você ainda não avaliou nenhum filme.",
                    button="Avaliar Agora")
else:
    total_avaliados = len(filmes_avaliados)
    media_usuario = sum(
        f['nota_pessoal'] for f in filmes_avaliados) / total_avaliados

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Avaliado", f"{total_avaliados} filmes")
    col2.metric("Sua Nota Média", f"{media_usuario:.1f}/5.0")

    filmes_5_estrelas = sum(
        1 for f in filmes_avaliados if f['nota_pessoal'] == 5)
    col3.metric("Obras Primas (5 estrelas)", f"{filmes_5_estrelas}")

    st.divider()

    filtro = st.radio("Filtrar:",
                      ["Todos",
                       "5 Estrelas",
                       "4 Estrelas",
                       "3 Estrelas",
                       "2 Estrelas",
                       "1 Estrela"], horizontal=True)

    if filtro == "Todos":
        lista_final = filmes_avaliados
    else:
        nota = int(filtro.split()[0])
        lista_final = [f for f in filmes_avaliados
                       if f["nota_pessoal"] == nota]

    grid_filme(lista_final, 4, fav_recomendar_button, contexto="historico")
