from flask import Flask, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
    JWTManager,
    decode_token
)
from jwt.exceptions import ExpiredSignatureError, DecodeError
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
import os
from flask_migrate import Migrate
from email.mime.text import MIMEText
from datetime import timedelta
from dotenv import load_dotenv
from database import db
from models import Usuario, Filmes, Favoritos
from pathlib import Path
from collections import defaultdict
from sklearn.metrics.pairwise import cosine_similarity
import joblib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
model_embedding = os.path.join(BASE_DIR, 'modelo_recomendacao.pkl')
model = joblib.load(model_embedding)
embeddings = model['embeddings']
tmdb_ids = model['tmdb_ids']
indices_map = {tmdb_id: i for i, tmdb_id in enumerate(tmdb_ids)}
meta_por_id = {m["tmdb_id"]: m for m in model["metadata"]}

env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Iniciando o Flask
app = Flask(__name__)

# Conectando com o banco de dados
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv("SECRET_KEY")
db.init_app(app)

migrate = Migrate(app, db)

# Config jwt
app.config['JWT_SECRET_KEY'] = os.getenv("JWT_KEY")
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=2)
jwt = JWTManager(app)


# Rota de login
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
                        "message": "usuario ou senha incorreta"}), 401


# Rota de status da API.
@app.route('/status')
def status():
    return jsonify({'status': "API FUNCIONANDO"})


# Rota de cadastro de usuário
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
        generos_fav=generos_str

    )

    db.session.add(novo_usuario)
    db.session.commit()

    print(f"novo usuario {user} cadastrado com sucesso")
    return jsonify({
        "success": True,
        "message": f"usuario {user} cadastrado com sucesso!"}), 200


# Rota para o reset da senha
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


# Rota para redefinir a senha
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


# Rota para pesquisa de filmes
@app.route('/filmes/pesquisar', methods=['GET'])
@jwt_required(optional=True)
def pesquisar_filme():
    termo_pesquisa = request.args.get('q')  # URL/?q=talfilme

    if not termo_pesquisa:
        return jsonify({
            "success": False,
            "message": "Termo de pesquisa não fornecido"}), 400

    id_usuario_logado = get_jwt_identity()

    termo_like = f"%{termo_pesquisa}%"
    filmes_encontrados = Filmes.query.filter(
        Filmes.titulo.ilike(termo_like)
        ).order_by(
            Filmes.qtd_votos.desc()
        ).limit(20).all()

    if not filmes_encontrados:
        return jsonify([])

    ids_favoritos = set()
    if id_usuario_logado:
        favoritos = Favoritos.query.filter_by(
            id_usuario=id_usuario_logado).all()
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
            'favoritos': filme.id in ids_favoritos
        } for filme in filmes_encontrados
    ]

    return jsonify(filmes_json)


# Rota para ADICIONAR um filme aos favoritos
@app.route('/favoritos', methods=['POST'])
@jwt_required()
def adicionar_favorito():
    id_usuario_atual = get_jwt_identity()
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
        id_filme=filme.id
    ).first()

    if favorito_existente:
        return jsonify({"success": False,
                        "message": "Filme já está nos favoritos"}), 409

    novo_favorito = Favoritos(id_usuario=id_usuario_atual, id_filme=filme.id)
    db.session.add(novo_favorito)
    db.session.commit()

    return jsonify({"success": True, "message":
                    "Filme adicionado aos favoritos!"}), 200


# Rota para listar favoritos
@app.route('/favoritos', methods=['GET'])
@jwt_required()
def listar_favoritos():
    id_usuario_atual = get_jwt_identity()
    filmes_favoritos = db.session.query(Filmes).join(
        Favoritos, Filmes.id == Favoritos.id_filme
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
    id_usuario_atual = get_jwt_identity()

    filme = Filmes.query.filter_by(tmdb_id=tmdb_id).first()
    if not filme:
        return jsonify({"success": False,
                        "message": "Filme não encontrado"}), 404

    favorito = Favoritos.query.filter_by(
        id_usuario=id_usuario_atual,
        id_filme=filme.id
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
    try:
        data = request.get_json()
        lista_tmdb_ids = data.get('lista_tmdb_ids')

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

        alpha = 0.75  # similaridade
        beta = 0.25  # popularidade

        for sim_idx in list(score_similaridade.keys()):
            tmdb_id = tmdb_ids[sim_idx]
            meta = meta_por_id.get(tmdb_id, {"media_votos": 5})
            popularidade = meta["media_votos"] / 10  # normaliza 0–1
            score_similaridade[sim_idx] = (
                alpha * score_similaridade[sim_idx] + beta * popularidade
            )

        indices_ordenados = sorted(
            score_similaridade.items(),
            key=lambda item: item[1],
            reverse=True
        )

        idx_mais_relevantes = [idx for idx, score in indices_ordenados[:10]]

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

        resultados_json = [
            {
                'tmdb_id': filme.tmdb_id,
                'titulo': filme.titulo,
                'sinopse': filme.sinopse,
                'generos': filme.generos,
                'media_votos': filme.media_votos,
                'qtd_votos': filme.qtd_votos,
                'poster_path': filme.poster_path
            } for filme in filmes_ordenados
        ]
        return jsonify(resultados_json)

    except Exception as e:
        app.logger.error("Erro na rota recomendar/multiplos: ", exc_info=True)
        return jsonify(
            {"success": False,
             "message": f"Erro interno do servidor: {str(e)}"}, 500
        )


# Inicialização do bloco de código main()
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)
