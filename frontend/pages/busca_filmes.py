import streamlit as st
import requests
from utils.utils import (
    setup_page,
    load_css,
    add_favorito,
    get_auth,
    add_list_recomendar,
    setup_header,
    grid_filme,
    API_URL
)

setup_page(titulo="Rotacine", layout="wide", protegida=True)
load_css(['styles/geral.css', 'styles/components.css', 'styles/badges.css'])
setup_header("RotaCine", "Descubra filmes com Aprendizado de Máquina!", "🎬 ")


def fav_recomendar_button(filme):
    col1, col2 = st.columns(2)
    favoritado = filme.get("favoritos", False)

    with col1:
        texto_botao = "Favoritado" if favoritado else "Favoritar"
        if st.button(
            texto_botao,
            key=f"fav_{filme['tmdb_id']}",
            use_container_width=True,
            disabled=favoritado,
        ):
            add_favorito(filme['tmdb_id'])

    with col2:
        if st.button(
            "Recomendar",
            key=f"add_{filme['tmdb_id']}",
            use_container_width=True,
        ):
            add_list_recomendar(filme)


headers = get_auth()

col_search, col_button, col_filtro = st.columns([5, 1.5, 2])

with col_search:
    termo_pesquisa = st.text_input(
        "Digite o nome do filme:",
        placeholder="Ex: Batman, O Senhor dos Anéis, Interestelar...",
        label_visibility="collapsed",
        key="search_input"
    )

with col_button:
    buscar = st.button("Buscar", width="stretch")

with col_filtro:
    nota_minima = st.selectbox(
        "Filtrar por nota",
        options=[0, 5, 6, 7, 8],
        format_func=lambda x: f"Nota mínima: {x}" if x > 0 else "Todas as notas",
        label_visibility='collapsed'
    )

st.divider()

# Busca
if buscar or (termo_pesquisa and len(termo_pesquisa) > 2):
    if termo_pesquisa.strip():
        try:
            with st.spinner('Buscando filmes...'):
                url = f"{API_URL}/filmes/pesquisar"
                response = requests.get(url, params={'q': termo_pesquisa},
                                        timeout=10, headers=headers)
                response.raise_for_status()
                resultados = response.json()

            # Filtro por nota
            if nota_minima > 0:
                resultados = [f for f in resultados if f.get('media_votos', 0) >= nota_minima]

            if resultados:
                st.markdown(
                    f'<div class="result-count">{len(resultados)} filme(s) encontrado(s) para "{termo_pesquisa}"</div>',
                    unsafe_allow_html=True
                )

                grid_filme(resultados, 4, fav_recomendar_button)

            else:
                st.warning(
                    f"Nenhum filme encontrado para **'{termo_pesquisa}'**")
                st.info("**Dicas:**\n- Verifique a ortografia"
                        "\n- Tente palavras-chave diferentes"
                        "\n- Reduza a nota mínima no filtro")

        except requests.Timeout:
            st.error("Tempo limite excedido. Tente novamente.")
        except requests.RequestException as e:
            st.error(f"Erro ao comunicar com a API: {e}")
        except Exception as e:
            st.error(f"Erro inesperado: {e}")
    else:
        st.warning("Por favor, digite o nome de um filme para pesquisar.")
else:
    # Tela inicial
    st.info("Como funciona?")
    st.caption("Digite o nome de um filme que você gosta no campo acima e"
               " descubra recomendações similares.")
    st.caption("Use o filtro para refinar sua busca!")
