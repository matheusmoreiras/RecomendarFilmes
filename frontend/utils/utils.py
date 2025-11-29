import streamlit as st
import re
import os
from time import sleep
from typing import List
import requests
from requests.exceptions import HTTPError, Timeout, RequestException, ConnectionError

API_URL = os.environ.get("API_URL", "http://127.0.0.1:5000")
IMAGEM_URL = "https://image.tmdb.org/t/p/w500"


def validar_senha(senha):
    if len(senha) < 6:
        return False, "A senha deve ter pelo menos 6 caracteres"
    if not any(c.isalpha() for c in senha):
        return False, "A senha deve conter pelo menos uma letra"
    if not any(c.isdigit() for c in senha):
        return False, "A senha deve conter pelo menos um número"
    return True, "Senha válida"


def validar_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def is_logged_in():
    return st.session_state.get('access_token') not in [None, ""]


def atualizar_mapa_avaliacoes():
    """
    Busca todas as avaliações do usuario e transforma em um dict
    para o session_state: {tmdb_id (int): nota (int)}
    """
    if not is_logged_in():
        return

    token = st.session_state.get('access_token')
    headers = {'Authorization': f'Bearer {token}'}

    try:
        response = requests.get(f"{API_URL}/usuario/minhas-avaliacoes",
                                headers=headers)

        if response.status_code == 200:
            dados = response.json()

            if isinstance(dados, list):
                st.session_state['mapa_avaliacoes'] = {
                    item['tmdb_id']: item['nota_pessoal'] for item in dados
                }
            else:
                st.session_state['mapa_avaliacoes'] = {}
        else:
            st.session_state['mapa_avaliacoes'] = {}

    except Exception as e:
        print(f"Erro ao atualizar mapa: {e}")
        st.session_state['mapa_avaliacoes'] = {}


def get_auth():
    if is_logged_in():
        if 'mapa_avaliacoes' not in st.session_state:
            atualizar_mapa_avaliacoes()
        token = st.session_state.get('access_token')
        if token:
            return {'Authorization': f'Bearer {token}'}
    return {}


def logout():
    st.session_state.clear()
    st.switch_page("app.py")


def api_request(method, endpoint, ignore_status=None, **kwargs):
    """
    Padronização para chamadas da API
    Args:
        method: metodo http ex: 'GET'
        endpoint: final da URL, ex: "favoritos"(não precisa do "/" inicial)
        **kwargs: Argumentos extras do requests (headers, json, params, etc)
    Returns:
        JSON response data ou None em caso de erro.
    """

    url = f"{API_URL}/{endpoint}"
    if ignore_status is None:
        ignore_status = []
    timeout = kwargs.pop('timeout', 10)
    try:
        response = requests.request(method, url, timeout=timeout, **kwargs)
        if response.status_code in ignore_status:
            return response.json()
        response.raise_for_status()
        return response.json()
    except ConnectionError:
        st.error("Verifique se o Backend está rodando.")
        return None
    except Timeout:
        st.error("O tempo limite da conexão expirou. Tente novamente.")
    except HTTPError as e:
        if e.response.status_code == 404:
            st.error("Recurso não encontrado (404).")
        elif e.response.status_code == 401:
            st.error("Sessão expirada ou não autorizada.")
        else:
            st.error(f"Erro na requisição ({e.response.status_code}): {e}")
    except RequestException as e:
        st.error(f"Erro de conexão: {e}")
    except Exception as e:
        st.error(f"Erro inesperado: {e}")


def setup_page(titulo: str, layout: str = "centered",
               protegida: bool = False, hide_sidebar: bool = False):
    """
    Args:
        titulo: titulo da pagina
        layout: centered ou wide
        protegida: se true, precisa estar logado para ver a página
        hide_sidebar: se true, a barra lateral será escondida
    """
    st.set_page_config(
        page_title=titulo,
        layout=layout,
        initial_sidebar_state="collapsed" if hide_sidebar else "auto"
    )

    st.markdown(
        """
        <style>
            [data-testid="stSidebarNavItems"] {display: none;}
        <style>
        """, unsafe_allow_html=True
    )

    if hide_sidebar:
        st.markdown(
            """
            <style>
                [data-testid="stSidebar"] {display: none;}
            <style>
            """, unsafe_allow_html=True,
        )
    if protegida and not is_logged_in():
        st.error("Por favor, faça login primeiro.")
        sleep(4)
        st.switch_page("app.py")

    if is_logged_in() and not hide_sidebar:
        st.sidebar.success(f"Logado como: {st.session_state.get('username')}")
        st.sidebar.header("Menu de navegação")

        st.sidebar.page_link("pages/busca_filmes.py", label="Buscar filmes")
        st.sidebar.page_link("pages/para_voce.py", label="Para você")
        st.sidebar.page_link("pages/recomendador.py", label="Recomendador")
        st.sidebar.page_link("pages/favoritos.py", label="Meus Favoritos")
        st.sidebar.page_link("pages/avaliacoes.py", label="Avaliações")

        st.sidebar.divider()

        if st.sidebar.button("Logout", width='stretch', type="primary"):
            logout()
            st.switch_page("app.py")


def load_css(file_paths: List[str]):
    """
    Args:
        file_paths: Uma lista para os arquivos css.
    """
    full_css = ""
    for file_path in file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                full_css += f.read()
        except FileNotFoundError:
            st.error(f"Arquivo CSS não encontrado em: {file_path}")

    st.markdown(f"<style>{full_css}</style>", unsafe_allow_html=True)


def add_favorito(tmdb_id):
    """
    Args:
        tmdb_id = id do filme
    """
    url = f"{API_URL}/favoritos"
    payload = {"tmdb_id": tmdb_id}
    headers = get_auth()

    try:
        response = requests.post(
            url, json=payload, headers=headers, timeout=10)
        data = response.json()
        if response.status_code == 200:
            st.toast(f"{data.get('message')}")

        elif response.status_code == 409:
            st.toast(f"{data.get('message')}")

        else:
            response.raise_for_status()

    except requests.RequestException as e:
        st.error(f"Erro ao comunicar com a API: {e}")
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {e}")


def carregar_favoritos():
    headers = get_auth()
    return api_request('GET', 'favoritos', headers=headers)


def remover_favorito(tmdb_id):
    endpoint = f"favoritos/{tmdb_id}"
    headers = get_auth()
    dados = api_request("DELETE", endpoint, headers=headers)

    if dados.get("success"):
        st.toast("Filme removido com sucesso!")
        sleep(1)
        st.rerun()
    else:
        st.toast(dados.get('message', 'Erro desconhecido ao remover.'))


def get_list_recomendar():
    if 'list_recomendacao' not in st.session_state:
        st.session_state['list_recomendacao'] = []
    return st.session_state['list_recomendacao']


def add_list_recomendar(filme: dict):
    """Adiciona o dict de um filme na lista
    a partir da página de pesquisa, onde recupera o filme.
    """
    list_recomendacao = get_list_recomendar()
    if not any(f['tmdb_id'] == filme['tmdb_id'] for f in list_recomendacao):
        list_recomendacao.append(filme)
        st.toast(f"{filme['titulo']} adicionado à lista de recomendação!")
    else:
        st.toast(f"{filme['titulo']} já está na lista.", icon="✅")


def remove_list_recomendar(tmdb_id: int):
    """Remove um filme da lista de recomendação onde recupera tmdb_id.
    """
    lista = get_list_recomendar()
    remover_filme = next((f for f in lista if f['tmdb_id'] == tmdb_id), None)
    if remover_filme:
        lista.remove(remover_filme)
        st.toast("Filme removido da lista.")
        st.rerun()


def limpar_lista_recomendacao():
    st.session_state['list_recomendacao'] = []


def callback_remover_avaliacao(tmdb_id, key_star):
    """
    Função executada ANTES da interface renderizar quando clica na lixeira.
    """
    if deletar_avaliacao_api(tmdb_id):
        mapa = st.session_state.get('mapa_avaliacoes', {})

        if str(tmdb_id) in mapa:
            del st.session_state['mapa_avaliacoes'][str(tmdb_id)]
        elif tmdb_id in mapa:
            del st.session_state['mapa_avaliacoes'][tmdb_id]

        if key_star in st.session_state:
            del st.session_state[key_star]

        st.session_state['_msg_remocao'] = "Avaliação removida."
    else:
        st.session_state['_msg_erro'] = "Erro ao remover avaliação."


def deletar_avaliacao_api(tmdb_id):
    headers = get_auth()
    if headers:
        try:
            response = requests.delete(
                f"{API_URL}/avaliar/{tmdb_id}",
                headers=headers,
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    return False


def card_filme(filme, contexto='geral'):
    """
    Gera o card do filme
    Args:
        filme: filme que será renderizado
        contexto: memória do st.session para não confundir entre as pág
        ex: contexto='busca' se estiver na pagina de busca de filmes
    """
    if filme.get("poster_path"):
        st.image(
            f"{IMAGEM_URL}{filme['poster_path']}",
        )

    st.markdown(
        f'<div class="movie-title">{filme["titulo"]}</div>',
        unsafe_allow_html=True
    )

    if filme['generos']:
        st.markdown(
            f'<span class="genero-badge">🎭 {filme["generos"]}</span>',
            unsafe_allow_html=True
        )

    nota = filme['media_votos']
    if nota >= 8:
        classe_nota = "nota-alta"
    elif nota >= 6:
        classe_nota = "nota-media"
    else:
        classe_nota = "nota-baixa"
    st.markdown(
        f"<span class='votos-badge {classe_nota}'>⭐ {nota:.1f}/10</span>"
        f"<span class='vote-count'>({filme['qtd_votos']:,} votos)</span>",
        unsafe_allow_html=True
    )

    st.write("**Sua avaliação:**")

    tmdb_id = filme.get('tmdb_id')
    key_star = f"star_{contexto}_{tmdb_id}"

    mapa = st.session_state.get('mapa_avaliacoes', {})
    if isinstance(mapa, list):
        mapa = {}

    nota_salva = mapa.get(str(tmdb_id)) or mapa.get(tmdb_id)

    # inicia as estrelinhas com cor se tiver nota salva
    if nota_salva is not None:
        if key_star not in st.session_state or st.session_state[key_star] is None:
            st.session_state[key_star] = int(nota_salva) - 1

    if nota_salva is not None:
        c1, c2 = st.columns([5, 1])
    else:
        c1, c2 = st.columns([1, 0.01])

    with c1:
        nota_selecionada = st.feedback("stars", key=key_star)

        if nota_selecionada is not None:
            nota_real = nota_selecionada + 1
            nota_atual_mapa = mapa.get(str(tmdb_id)) or mapa.get(tmdb_id)

            if nota_atual_mapa != nota_real:
                headers = get_auth()
                if headers:
                    try:
                        payload = {'tmdb_id': tmdb_id, 'nota': nota_real}
                        res = requests.post(f"{API_URL}/avaliar",
                                            json=payload, headers=headers)

                        if res.status_code == 200:
                            st.toast(f"Nota {nota_real} salva!", icon="⭐")
                            if 'mapa_avaliacoes' not in st.session_state:
                                st.session_state['mapa_avaliacoes'] = {}
                            st.session_state['mapa_avaliacoes'][
                                str(tmdb_id)] = nota_real
                        else:
                            st.error("Erro ao salvar.")
                    except requests.RequestException:
                        st.error("Erro de conexão.")
                else:
                    st.warning("Faça login.")

    with c2:
        if nota_salva is not None:
            if st.button(
                "🗑️",
                key=f"del_star_{contexto}_{tmdb_id}",
                help="Remover avaliação",
            ):
                callback_remover_avaliacao(tmdb_id, key_star)
                st.rerun()

    with st.expander("Ver sinopse"):
        sinopse = filme.get('sinopse')
        if sinopse:
            st.write(sinopse)
        else:
            st.info("Sinopse não disponível")


def setup_header(titulo, subtitulo=None, emoji=""):
    """
    Args:
        titulo: titulo da pagina
        subtitulo: subtitulo, pode ser NONE
        emoji: será adicionado a ESQUERDA do titulo, padrao vazio
    """
    titulo_completo = f"{emoji}{titulo}" if emoji else titulo
    st.markdown(f'<h1 class="titulo">{titulo_completo}</h1>',
                unsafe_allow_html=True)
    if subtitulo:
        st.markdown(f'<p class="subtitulo">{subtitulo}</p>',
                    unsafe_allow_html=True)


def msg_lista_vazia(message, button="Buscar Filmes",
                    page="pages/busca_filmes.py"):
    st.info(message)
    if button and page:
        if st.button(button):
            st.switch_page(page)


def grid_filme(lista_filme, colunas, button=None, contexto='grid'):
    """
    Args:
    lista_filme: Dict dos filmes
    colunas: qtd de colunas do grid(ex: 4 ou 5)
    button: Função para renderizar botões do grid
    contexto: memória do st.session para não confundir entre as pág
        ex: contexto='busca' se estiver na pagina de busca de filmes
    """
    if not lista_filme:
        return
    cols = st.columns(colunas, gap="medium")
    for i, filme in enumerate(lista_filme):
        col = cols[i % colunas]
        with col:
            with st.container(border=True):
                motivo = filme.get('motivo')
                if motivo:
                    st.caption(motivo)
                if button:
                    button(filme)
                card_filme(filme, contexto=contexto)


def limpar_cache_recomendacao():
    if 'resultados_lista' in st.session_state:
        del st.session_state['resultados_lista']
