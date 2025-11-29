import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import text
from flask_jwt_extended import get_jwt_identity

CACHE_VETORES_USUARIOS = {}


def calcular_vetor_usuario(user_id, db_session, embeddings, indices_map):
    sql = text("""
        SELECT id_filme FROM avaliacoes WHERE id_usuario = :uid AND nota >= 4
        UNION
        SELECT id_filme FROM favoritos WHERE id_usuario = :uid
    """)
    result = db_session.execute(sql, {'uid': user_id}).fetchall()
    ids_curtidos = [row[0] for row in result]

    if not ids_curtidos:
        return None

    indices_validos = []
    for tmdb_id in ids_curtidos:
        if tmdb_id in indices_map:
            indices_validos.append(indices_map[tmdb_id])

    if not indices_validos:
        return None

    vetores = embeddings[indices_validos]
    vetor_medio = np.mean(vetores, axis=0).reshape(1, -1)

    CACHE_VETORES_USUARIOS[user_id] = vetor_medio
    return vetor_medio


def encontrar_vizinhos_cache(
        user_id, db_session, embeddings, indices_map, k=30):
    """
    Compara o usuário atual com o cache.
    Precisa de embeddings/map se calcular na hora.
    """
    meu_vetor = CACHE_VETORES_USUARIOS.get(user_id)

    if meu_vetor is None:
        meu_vetor = calcular_vetor_usuario(
            user_id, db_session, embeddings, indices_map)

    if meu_vetor is None:
        return []

    outros_ids = []
    outros_vetores = []

    for uid, vec in CACHE_VETORES_USUARIOS.items():
        if uid != user_id:
            outros_ids.append(uid)
            outros_vetores.append(vec)

    if not outros_ids:
        return []

    matriz_outros = np.vstack(outros_vetores)
    scores = cosine_similarity(meu_vetor, matriz_outros)[0]

    top_indices = scores.argsort()[-k:][::-1]

    return [outros_ids[i] for i in top_indices]


def div_genero(filmes_lista, max_por_genero=3):
    resultado = []
    contador_generos = {}
    for filme in filmes_lista:
        generos = filme.generos.split(',') if filme.generos else []
        generos = [g.strip() for g in generos]
        pode_adicionar = True
        for gen in generos:
            if contador_generos.get(gen, 0) >= max_por_genero:
                pode_adicionar = False
                break
        if pode_adicionar:
            resultado.append(filme)
            for gen in generos:
                contador_generos[gen] = contador_generos.get(gen, 0) + 1
    return resultado


def get_user_id():
    raw_id = get_jwt_identity()
    try:
        return int(raw_id)
    except (ValueError, TypeError, RuntimeError):
        return None
