import os
import math
import smtplib
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from email.mime.text import MIMEText
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    JWTManager,
    decode_token
)
from flask_migrate import Migrate
from jwt.exceptions import ExpiredSignatureError, DecodeError
from werkzeug.security import generate_password_hash, check_password_hash
from sklearn.metrics.pairwise import cosine_similarity
import joblib
from sqlalchemy import text
from database import db
from models import Usuario, Filmes, Favoritos, Avaliacao
from utils import (
    calcular_vetor_usuario,
    encontrar_vizinhos_cache,
    div_genero,
    get_user_id)

# Carregando modelos e metadata
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
model_embedding = os.path.join(BASE_DIR, 'modelo_recomendacao.pkl')
model = joblib.load(model_embedding)
embeddings = model['embeddings']
tmdb_ids = model['tmdb_ids']
indices_map = {tmdb_id: i for i, tmdb_id in enumerate(tmdb_ids)}
meta_por_id = {m["tmdb_id"]: m for m in model["metadata"]}
MODELO_COLAB_PATH = os.path.join(BASE_DIR, 'modelo_colaborativo.pkl')
algo_svd = None
dados_modelo = joblib.load(MODELO_COLAB_PATH)
algo_svd = dados_modelo.get('model')
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Iniciando o Flask
app = Flask(__name__)

# Conexão com o banco de dados
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv("SECRET_KEY")
db.init_app(app)
migrate = Migrate(app, db)

app.config['JWT_SECRET_KEY'] = os.getenv("JWT_KEY")
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=2)
jwt = JWTManager(app)

with app.app_context():
    sql_users = text("""SELECT DISTINCT id_usuario
                    FROM avaliacoes
                    UNION SELECT DISTINCT id_usuario FROM favoritos""")
    all_users_ids = [row[0] for row in db.session.execute(
        sql_users).fetchall()]

    count = 0
    for uid in all_users_ids:
        if calcular_vetor_usuario(
         uid, db.session, embeddings, indices_map) is not None:
            count += 1


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    usuario_db = Usuario.query.filter_by(username=username).first()

    if usuario_db and check_password_hash(usuario_db.pw_hash, password):
        access_token = create_access_token(identity=str(usuario_db.id))
        return jsonify({"success": True,
                        "message": "Login realizado com sucesso",
                        "access_token": access_token})
    else:
        return jsonify({"success": False,
                        "message": "Usuário ou senha incorretos"}), 401


@app.route('/cadastro', methods=['POST'])
def cadastro():
    data = request.get_json()
    user = data.get("user")
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    generos = data.get("generos_fav")

    if Usuario.query.filter_by(username=user).first() is not None:
        return jsonify({"success": False,
                        "message": "Nome de usuário já existe"}), 409
    if Usuario.query.filter_by(email=email).first() is not None:
        return jsonify({"success": False,
                        "message": "Email já cadastrado"}), 401

    hashed_password = generate_password_hash(password)

    generos_str = ",".join(generos) if generos else ""

    novo_usuario = Usuario(
        username=user,
        name=name,
        email=email,
        pw_hash=hashed_password,
        generos_fav=generos_str)

    db.session.add(novo_usuario)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "usuario cadastrado com sucesso!"}), 200


@app.route('/reset_senha', methods=['POST'])
def resetar_senha():
    data = request.get_json()
    email = data.get("email")

    usuario_db = Usuario.query.filter_by(email=email).first()
    if not usuario_db:
        return jsonify({"success": True,
                        "message": f"Um link será enviado para{email}"})

    reset_jwt_token = create_access_token(
        identity=email,
        additional_claims={"purpose": "password_reset"},
        expires_delta=timedelta(minutes=30)
    )

    link = f"http://localhost:8501/redefinir?token={reset_jwt_token}"

    msg = MIMEText(f"Clique no link para redefinir sua senha: {link}")
    msg['Subject'] = f"Redefinição de senha para {usuario_db.username}"
    msg['From'] = os.getenv("EMAIL_USER")
    msg['To'] = email

    try:
        with smtplib.SMTP(
                os.getenv("SMTP_SERVER"), os.getenv("SMTP_PORT")) as server:
            server.starttls()
            server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASSWORD"))
            server.sendmail(msg['From'], msg['To'], msg.as_string())
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Erro ao enviar o email: {e}"
        })
    return jsonify({
        "success": True,
        "message": f"Email enviado com instruções para {email}"
    })


@app.route('/redefinir', methods=["POST"])
def confirmar_reset():
    data = request.get_json()
    token = data.get("token")
    new_pw = data.get("new_pw")

    try:
        decoded_token = decode_token(token)
        if decoded_token.get("purpose") != "password_reset":
            return jsonify({"success": False,
                            "message": "Token inválido para a sessão"}), 403
        email = decoded_token['sub']

    except ExpiredSignatureError:
        return jsonify({"success": False,
                        "message": "Token expirado"}), 401
    except DecodeError:
        return jsonify({"success": False,
                        "message": "Token inválido"}), 422

    usuario_db = Usuario.query.filter_by(email=email).first()
    if not usuario_db:
        return jsonify(
            {"success": False,
             "message": "Email não existe no banco de dados"})

    usuario_db.pw_hash = generate_password_hash(new_pw)
    db.session.commit()

    return jsonify({
        "sucess": True,
        "message": "senha redefinida com sucesso!"
    }), 200


@app.route('/filmes/pesquisar', methods=['GET'])
@jwt_required(optional=True)
def pesquisar_filme():
    termo_pesquisa = request.args.get('q')  # URL/?q=talfilme

    if not termo_pesquisa:
        return jsonify({
            "success": False,
            "message": "Termo de pesquisa não fornecido"}), 400

    id_usuario_atual = get_user_id()

    termo_like = f"%{termo_pesquisa}%"
    filmes_encontrados = Filmes.query.filter(
        Filmes.titulo.ilike(termo_like)
        ).order_by(
            Filmes.qtd_votos.desc()
        ).limit(20).all()

    if not filmes_encontrados:
        return jsonify([])

    ids_favoritos = set()
    if id_usuario_atual:
        favoritos = Favoritos.query.filter_by(
            id_usuario=id_usuario_atual).all()
        ids_favoritos = {fav.id_filme for fav in favoritos}

    filmes_json = [
        {
            'tmdb_id': filme.tmdb_id,
            'titulo': filme.titulo,
            'sinopse': filme.sinopse,
            'generos': filme.generos,
            'popularidade': filme.popularidade,
            'media_votos': filme.media_votos,
            'qtd_votos': filme.qtd_votos,
            'poster_path': filme.poster_path,
            'favoritos': filme.tmdb_id in ids_favoritos
        } for filme in filmes_encontrados
    ]

    return jsonify(filmes_json)


# Rota para ADICIONAR um filme aos favoritos
@app.route('/favoritos', methods=['POST'])
@jwt_required()
def adicionar_favorito():
    id_usuario_atual = get_user_id()
    data = request.get_json()
    tmdb_id = data.get('tmdb_id')

    if not tmdb_id:
        return jsonify({"success": False,
                        "message": "tmdb_id do filme é obrigatório"}), 400

    filme = Filmes.query.filter_by(tmdb_id=tmdb_id).first()

    if not filme:
        return jsonify({"success": False, "message":
                        "Filme não encontrado no banco de dados"}), 404

    favorito_existente = Favoritos.query.filter_by(
        id_usuario=id_usuario_atual,
        id_filme=filme.tmdb_id
    ).first()

    if favorito_existente:
        return jsonify({"success": False,
                        "message": "Filme já está nos favoritos"}), 409

    novo_favorito = Favoritos(
        id_usuario=id_usuario_atual, id_filme=filme.tmdb_id)
    db.session.add(novo_favorito)
    db.session.commit()

    return jsonify({"success": True, "message":
                    "Filme adicionado aos favoritos!"}), 200


# Rota para listar favoritos
@app.route('/favoritos', methods=['GET'])
@jwt_required()
def listar_favoritos():
    id_usuario_atual = get_user_id()
    filmes_favoritos = db.session.query(Filmes).join(
        Favoritos, Filmes.tmdb_id == Favoritos.id_filme
    ).filter(Favoritos.id_usuario == id_usuario_atual).all()

    favoritos_json = [
        {
            'tmdb_id': filme.tmdb_id,
            'titulo': filme.titulo,
            'sinopse': filme.sinopse,
            'generos': filme.generos,
            'media_votos': filme.media_votos,
            'qtd_votos': filme.qtd_votos,
            'poster_path': filme.poster_path
        } for filme in filmes_favoritos
    ]

    return jsonify(favoritos_json)


# Rota para remover favoritos
@app.route('/favoritos/<int:tmdb_id>', methods=['DELETE'])
@jwt_required()
def remover_favorito(tmdb_id):
    id_usuario_atual = get_user_id()

    filme = Filmes.query.filter_by(tmdb_id=tmdb_id).first()
    if not filme:
        return jsonify({"success": False,
                        "message": "Filme não encontrado"}), 404

    favorito = Favoritos.query.filter_by(
        id_usuario=id_usuario_atual,
        id_filme=filme.tmdb_id
    ).first()

    if not favorito:
        return jsonify(
            {"success": False,
             "message": "Este filme não está na sua lista de favoritos"}), 404

    db.session.delete(favorito)
    db.session.commit()

    return jsonify({"success": True,
                    "message": "Filme removido dos favoritos com sucesso"})


@app.route('/recomendar/multiplos', methods=['POST'])
@jwt_required()
def recomendar_multiplos():
    """
    Recomendação baseada em filmes escolhidos pelo usuário
    Utiliza apenas NLP (modelo_recomendacao.pkl)
    """
    id_usuario_atual = get_user_id()
    try:
        data = request.get_json()
        lista_tmdb_ids = data.get('lista_tmdb_ids')
        incluir_avaliados = data.get('incluir_avaliados', False)

        if not lista_tmdb_ids:
            return jsonify(
                {"success": False,
                 "message": "Nenhum filme fornecido"}), 400

        if embeddings is None or indices_map is None:
            return jsonify({
                "success": False,
                "message": "Modelos de recomendação não carregados."}), 500

        indice_filmes = [
            indices_map[tmdb_id] for tmdb_id in lista_tmdb_ids
            if tmdb_id in indices_map
        ]

        if not indice_filmes:
            return jsonify({
                "success": False,
                "message": "Nenhum dos filmes foi encontrado no modelo"}), 404

        score_similaridade = defaultdict(float)

        for idx in indice_filmes:
            vetor_filme = embeddings[idx].reshape(1, -1)
            simi_cossenos = cosine_similarity(
                vetor_filme, embeddings).flatten()
            for sim_idx, score in enumerate(simi_cossenos):
                if sim_idx not in indice_filmes:
                    score_similaridade[sim_idx] += score

        alpha = 0.8  # similaridade
        beta = 0.2  # popularidade

        for sim_idx in list(score_similaridade.keys()):
            tmdb_id = tmdb_ids[sim_idx]
            meta = meta_por_id.get(tmdb_id, {"media_votos": 5})
            popularidade = meta["media_votos"] / 10
            score_similaridade[sim_idx] = (
                alpha * score_similaridade[sim_idx] + beta * popularidade
            )

        indices_ordenados = sorted(
            score_similaridade.items(),
            key=lambda item: item[1],
            reverse=True
        )

        idx_mais_relevantes = [idx for idx, score in indices_ordenados[:30]]

        if not idx_mais_relevantes:
            return jsonify(
             {"success": False,
              "message": "Não foi possível gerar recomendações"}), 404

        tmdb_ids_np = [tmdb_ids[idx] for idx in idx_mais_relevantes]
        tmdb_ids_recomendados = [int(id) for id in tmdb_ids_np]

        filmes_recomendados = Filmes.query.filter(
            Filmes.tmdb_id.in_(tmdb_ids_recomendados)).all()

        mapa_filmes = {filme.tmdb_id: filme for filme in filmes_recomendados}
        filmes_ordenados = [
            mapa_filmes[tmdb_id] for tmdb_id in tmdb_ids_recomendados
            if tmdb_id in mapa_filmes
        ]

        if not incluir_avaliados:
            av_usuario = db.session.query(Avaliacao.id_filme).filter_by(
                id_usuario=id_usuario_atual).all()

            ids_avaliados = {av.id_filme for av in av_usuario}

            filmes_ordenados = [
                f for f in filmes_ordenados
                if f.tmdb_id not in ids_avaliados
            ]

        filmes_finais = filmes_ordenados[:10]
        resultados_json = [
            {
                'tmdb_id': filme.tmdb_id,
                'titulo': filme.titulo,
                'sinopse': filme.sinopse,
                'generos': filme.generos,
                'media_votos': filme.media_votos,
                'qtd_votos': filme.qtd_votos,
                'poster_path': filme.poster_path
            } for filme in filmes_finais
        ]
        return jsonify(resultados_json)

    except Exception as e:
        app.logger.error("Erro na rota recomendar/multiplos: ", exc_info=True)
        return jsonify(
            {"success": False,
             "message": f"Erro interno do servidor: {str(e)}"}, 500
        )


# Rota para avaliar filmes
@app.route('/avaliar', methods=['POST'])
@jwt_required()
def avaliar_filme():
    id_usuario_atual = get_user_id()
    data = request.get_json()
    tmdb_id = data.get('tmdb_id')
    nota = data.get('nota')

    if not tmdb_id or nota is None:
        return jsonify({
            "success": False,
            "message": "tmdb_id e nota são obrigatórios"
        }), 400

    filme = Filmes.query.filter_by(tmdb_id=tmdb_id).first()

    if not filme:
        return jsonify({
            "success": False,
            "message": "Filme não encontrado no banco de dados"
        }), 404

    avaliacao = Avaliacao.query.filter_by(
        id_usuario=id_usuario_atual,
        id_filme=filme.tmdb_id
    ).first()

    try:
        if avaliacao:
            avaliacao.nota = nota
            avaliacao.data_avaliacao = datetime.utcnow()
            msg = "Avaliação atualizada com sucesso!"
        else:
            nova_avaliacao = Avaliacao(
                id_usuario=id_usuario_atual,
                id_filme=filme.tmdb_id,
                nota=nota,
                data_avaliacao=datetime.utcnow()
            )
            db.session.add(nova_avaliacao)
            msg = "Avaliação salva com sucesso!"

        db.session.commit()
        return jsonify({"success": True, "message": msg}), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Erro ao salvar avaliação: {e}")
        return jsonify({
            "success": False,
            "message": "Erro interno ao salvar avaliação."
        }), 500


# Listar favoritos
@app.route('/usuario/minhas-avaliacoes', methods=['GET'])
@jwt_required()
def get_minhas_avaliacoes():
    id_usuario_atual = get_user_id()
    resultados = db.session.query(Filmes, Avaliacao.nota).join(
        Avaliacao, Filmes.tmdb_id == Avaliacao.id_filme
    ).filter(
        Avaliacao.id_usuario == id_usuario_atual
    ).all()

    ids_favoritos = set()
    if id_usuario_atual:
        favoritos = Favoritos.query.filter_by(
            id_usuario=id_usuario_atual).all()
        ids_favoritos = {fav.id_filme for fav in favoritos}

    lista_avaliados = [
        {
            'tmdb_id': filme.tmdb_id,
            'titulo': filme.titulo,
            'poster_path': filme.poster_path,
            'generos': filme.generos,
            'media_votos': filme.media_votos,
            'qtd_votos': filme.qtd_votos,
            'sinopse': filme.sinopse,
            'nota_pessoal': nota,
            'favoritos': filme.tmdb_id in ids_favoritos
        }
        for filme, nota in resultados
    ]

    return jsonify(lista_avaliados), 200


@app.route('/recomendar/colaborativo', methods=['GET'])
@jwt_required()
def recomendar_colaborativo():
    """
    Recomendação colaborativa pura utilizando SVD
    uso de comutação para cold start com cluster e com dados(svd colaborativo)
    retorno de fallback caso não hajam interações
    utilização do modelo_colaborativo.pkl
    """
    def score_descoberta(item):
        nota = item['nota_svd']
        pop = item['popularidade'] if item['popularidade'] > 1 else 1
        penalidade = 0.1 * math.log10(pop)

        return nota - penalidade
    try:
        id_usuario_atual = get_user_id()

        qtd_avaliacoes = Avaliacao.query.filter_by(
            id_usuario=id_usuario_atual).count()
        qtd_favoritos = Favoritos.query.filter_by(
            id_usuario=id_usuario_atual).count()
        total_interacoes = qtd_avaliacoes + qtd_favoritos

        ids_recomendados = []
        origem_recomendacao = ""

        if total_interacoes > 0:
            calcular_vetor_usuario(id_usuario_atual,
                                   db.session, embeddings, indices_map)

        # cold start
        if total_interacoes < 6 and total_interacoes > 0:
            vizinhos = encontrar_vizinhos_cache(id_usuario_atual, k=30)
            if vizinhos:
                vizinhos_tuple = tuple(vizinhos)
                if len(vizinhos_tuple) == 1:
                    vizinhos_tuple = (vizinhos_tuple[0],)

                query = text("""
                    SELECT id_filme
                    FROM avaliacoes
                    WHERE id_usuario IN :vizinhos
                    AND nota >= 4
                    AND id_filme NOT IN (
                    SELECT id_filme FROM avaliacoes WHERE id_usuario = :meuid
                    )
                    GROUP BY id_filme
                    HAVING COUNT(id_usuario) > 1
                    ORDER BY COUNT(id_usuario) DESC, AVG(nota) DESC
                    LIMIT 10
                """)

                res = db.session.execute(
                    query, {'vizinhos': vizinhos_tuple,
                            'meuid': id_usuario_atual}).fetchall()
                ids_recomendados = [row[0] for row in res]
                origem_recomendacao = "Comunidade Similar (Cluster)"

        # svd - matriz
        elif total_interacoes >= 6:
            if algo_svd:
                avaliacoes = Avaliacao.query.filter_by(
                    id_usuario=id_usuario_atual).all()
                favoritos = Favoritos.query.filter_by(
                    id_usuario=id_usuario_atual).all()

                ids_vistos = {a.id_filme for a in avaliacoes}
                ids_vistos.update({f.id_filme for f in favoritos})

                candidatos = Filmes.query.filter(
                    Filmes.qtd_votos > 20,
                    ~Filmes.tmdb_id.in_(ids_vistos)
                ).limit(1500).all()

                previsoes = []
                for filme in candidatos:
                    try:
                        pred = algo_svd.predict(
                            uid=id_usuario_atual, iid=filme.tmdb_id)

                        if not pred.details.get('was_impossible', False):
                            previsoes.append({
                                'id': filme.tmdb_id,
                                'nota_svd': pred.est,
                                'popularidade': filme.qtd_votos})
                    except Exception:
                        continue

                previsoes.sort(key=score_descoberta, reverse=True)
                ids_recomendados = [x['id'] for x in previsoes[:20]]
                origem_recomendacao = "Recomendação Pessoal (IA)"

        # fallback
        if not ids_recomendados:
            filmes_top = Filmes.query.filter(Filmes.qtd_votos > 100)\
                .order_by(Filmes.media_votos.desc()).limit(10).all()
            ids_recomendados = [f.tmdb_id for f in filmes_top]
            origem_recomendacao = "Populares (Geral)"

        filmes_db = Filmes.query.filter(
            Filmes.tmdb_id.in_(ids_recomendados)).all()
        mapa_filmes = {f.tmdb_id: f for f in filmes_db}

        # reordernar após o sql in
        filmes_ordenados = []
        for tmdb_id in ids_recomendados:
            if tmdb_id in mapa_filmes:
                filmes_ordenados.append(mapa_filmes[tmdb_id])

        # Diversificação simples (não mostrar 10 filmes iguais)
        filmes_finais = div_genero(filmes_ordenados, max_por_genero=3)
        filmes_finais = filmes_finais[:10]

        resultados = [{
            'tmdb_id': f.tmdb_id,
            'titulo': f.titulo,
            'poster_path': f.poster_path,
            'sinopse': f.sinopse,
            'generos': f.generos,
            'media_votos': f.media_votos,
            'qtd_votos': f.qtd_votos,
            'origem': origem_recomendacao
        } for f in filmes_finais]

        return jsonify(resultados)

    except Exception as e:
        app.logger.error(f"Erro Colaborativo: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erro interno"}), 500


@app.route('/recomendar/hibrido', methods=['GET'])
@jwt_required()
def recomendar_hibrido():
    """
    Recomendação híbrida combinando NLP e filtragem colaborativa(SVD)
    Ajusta os pesos baseado no histórico do usuário
    A partir de 10 interações; SVD tem peso maior, abaixo disso, o NLP tem
    """
    try:
        id_usuario_atual = get_user_id()
        avaliacoes = Avaliacao.query.filter_by(
            id_usuario=id_usuario_atual).all()
        favoritos = Favoritos.query.filter_by(
            id_usuario=id_usuario_atual).all()

        ids_vistos = {a.id_filme for a in avaliacoes}
        ids_vistos.update({f.id_filme for f in favoritos})
        total_interacoes = len(ids_vistos)

        if total_interacoes < 10:
            peso_nlp = 0.7
            peso_svd = 0.3
        else:
            peso_nlp = 0.3
            peso_svd = 0.7

        user_vector = calcular_vetor_usuario(
            id_usuario_atual, db.session, embeddings, indices_map)

        if user_vector is None:
            return jsonify({"success": False,
                            "message": "Sem histórico suficiente."}), 404

        # array para todos os filmes
        scores_nlp_todos = cosine_similarity(user_vector, embeddings)[0]

        candidatos_finais = []

        top_indices_nlp = scores_nlp_todos.argsort()[-1000:][::-1]

        # pontuacao hibrida
        for idx in top_indices_nlp:
            tmdb_id = tmdb_ids[idx]  # ids mapp na mesma ordem dos embeddings

            if tmdb_id in ids_vistos:
                continue

            score_nlp = scores_nlp_todos[idx]

            # nota svd normalizada
            score_svd = 0
            if algo_svd:
                try:
                    pred = algo_svd.predict(id_usuario_atual, tmdb_id)
                    raw_score = (pred.est - 1) / 4
                    score_svd = max(0.0, min(1.0, raw_score))
                except Exception:
                    score_svd = 0.5

            score_final = (score_nlp * peso_nlp) + (score_svd * peso_svd)
            candidatos_finais.append(
                (tmdb_id, score_final, score_nlp, score_svd))

        candidatos_finais.sort(key=lambda x: x[1], reverse=True)
        top_15 = candidatos_finais[:15]

        ids_recomendados = [x[0] for x in top_15]

        filmes_db = Filmes.query.filter(
            Filmes.tmdb_id.in_(ids_recomendados)).all()
        mapa_filmes = {f.tmdb_id: f for f in filmes_db}

        resultados = []
        for cand in top_15:
            tid, s_final, s_nlp, s_svd = cand
            if tid in mapa_filmes:
                f = mapa_filmes[tid]

                motivo = "Recomendação Equilibrada"
                if s_nlp > 0.8:
                    motivo = "Semelhante ao que você curte"
                if s_svd > 0.8:
                    motivo = "Alta probabilidade de gostar"

                resultados.append({
                    'tmdb_id': f.tmdb_id,
                    'titulo': f.titulo,
                    'poster_path': f.poster_path,
                    'sinopse': f.sinopse,
                    'generos': f.generos,
                    'media_votos': f.media_votos,
                    'qtd_votos': f.qtd_votos,
                    'score_final': round(s_final, 2),  # Debug
                    'motivo': motivo
                })

        return jsonify(resultados)

    except Exception as e:
        app.logger.error(f"Erro Híbrido: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erro interno"}), 500


# Rota para remover avaliação
@app.route('/avaliar/<int:tmdb_id>', methods=['DELETE'])
@jwt_required()
def remover_avaliacao(tmdb_id):
    id_usuario_atual = get_user_id()

    avaliacao = Avaliacao.query.filter_by(
        id_usuario=id_usuario_atual,
        id_filme=tmdb_id
    ).first()

    if not avaliacao:
        return jsonify({"message":
                        "Avaliação não encontrada."}), 404

    try:
        db.session.delete(avaliacao)
        db.session.commit()
        return jsonify({"success": True,
                        "message": "Avaliação removida."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False,
                        "message": str(e)}), 500


# Inicialização do bloco de código main()
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)
