import streamlit as st
import requests
from utils.utils import (
    setup_page,
    load_css,
    get_auth,
    get_list_recomendar,
    remove_list_recomendar,
    limpar_lista_recomendacao,
    setup_header,
    msg_lista_vazia,
    grid_filme,
    API_URL
)

setup_page(titulo="Recomendador", protegida=True, layout="wide")
load_css(['styles/geral.css', 'styles/components.css', 'styles/badges.css'])
setup_header("Recomendador", "Adicione filmes para gerar recomendações")


def del_recomendacao(filme):
    if st.button("Remover",
                 key=f"rem_{filme['tmdb_id']}",
                 width='content',
                 ):
        remove_list_recomendar(filme['tmdb_id'])


lista_recomendacao = get_list_recomendar()

resultados = None

if not lista_recomendacao:
    msg_lista_vazia(
        "Você ainda não adicionou filmes para basearmos a recomendação!")
else:
    st.info(f"Basearemos a recomendação em {len(lista_recomendacao)} filme(s)")

    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("Gerar Recomendações com base nos filmes da lista",
                     width='stretch'):
            with st.spinner("Buscando filmes parecidos..."):
                lista_tmdb_ids = [filme['tmdb_id']
                                  for filme in lista_recomendacao]

                headers = get_auth()
                if headers and lista_tmdb_ids:
                    try:
                        response = requests.post(
                            f"{API_URL}/recomendar/multiplos",
                            headers=headers,
                            json={"lista_tmdb_ids": lista_tmdb_ids},
                            timeout=15
                        )
                        response.raise_for_status()
                        resultados = response.json()
                    except requests.HTTPError:
                        st.error("Erro 404")

    with col2:
        if st.button("Limpar lista", width="stretch"):
            limpar_lista_recomendacao()
            st.rerun()

    if resultados:
        st.divider()
        st.success("Filmes recomendados:")
        grid_filme(resultados, 5)

    st.divider()

    grid_filme(lista_recomendacao, 5, del_recomendacao)
