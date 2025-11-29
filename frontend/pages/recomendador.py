import streamlit as st
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
    limpar_cache_recomendacao,
    api_request
)

setup_page(titulo="Recomendador", protegida=True, layout="wide")
load_css(['styles/geral.css', 'styles/components.css', 'styles/badges.css',
          'styles/sidebar.css'])
setup_header("Recomendador", "Adicione filmes para gerar recomendações")


def del_recomendacao(filme):
    if st.button("Remover",
                 key=f"rem_{filme['tmdb_id']}",
                 width='content',
                 ):
        remove_list_recomendar(filme['tmdb_id'])


lista_recomendacao = get_list_recomendar()

if not lista_recomendacao:
    msg_lista_vazia(
        "Você ainda não adicionou filmes para basearmos a recomendação!")
    limpar_cache_recomendacao()
else:
    st.info(f"Basearemos a recomendação em {len(lista_recomendacao)} filme(s)")

    col1, col2 = st.columns([3, 1])
    with col1:
        avaliados = st.toggle("Incluir filmes que já avaliei?",
                              value=False,
                              on_change=limpar_cache_recomendacao)
        if st.button("Gerar Recomendações com base nos filmes da lista",
                     width='stretch'):
            with st.spinner("Buscando filmes parecidos..."):
                lista_tmdb_ids = [filme['tmdb_id']
                                  for filme in lista_recomendacao]

                headers = get_auth()
                if headers and lista_tmdb_ids:
                    payload = {
                        "lista_tmdb_ids": lista_tmdb_ids,
                        "incluir_avaliados": avaliados
                    }
                    resultado = api_request(
                        "POST",
                        "recomendar/multiplos",
                        json=payload,
                        ignore_status=[404],
                        headers=headers,
                        timeout=15
                    )
                    if resultado is not None:
                        st.session_state['resultados_lista'] = resultado
    with col2:
        if st.button("Limpar lista", width="stretch"):
            limpar_lista_recomendacao()
            if 'resultados_lista' in st.session_state:
                del st.session_state['resultados_lista']
            st.rerun()
    resultados_salvos = st.session_state.get('resultados_lista')

    if resultados_salvos:
        st.divider()
        st.success("Filmes recomendados:")
        if st.button("Limpar resultados", key="limpar_res_lista"):
            del st.session_state['resultados_lista']
            st.rerun()
        grid_filme(resultados_salvos, 5, contexto='rec_resultados')

    st.divider()

    grid_filme(lista_recomendacao, 5, del_recomendacao, 'rec_lista')
