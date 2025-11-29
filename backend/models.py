from database import db
from datetime import datetime


class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    pw_hash = db.Column(db.String(255), nullable=False)
    generos_fav = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f'<Usuario {self.username}>'


class Filmes(db.Model):
    __tablename__ = 'filmes'
    id = db.Column(db.Integer, primary_key=True)
    tmdb_id = db.Column(db.Integer, unique=True, nullable=False)
    titulo = db.Column(db.String(200), nullable=False)
    sinopse = db.Column(db.Text, nullable=False)
    data_lancamento = db.Column(db.Date, nullable=True)
    popularidade = db.Column(db.Float, nullable=True)
    media_votos = db.Column(db.Float, nullable=True)
    qtd_votos = db.Column(db.Integer, nullable=True)
    poster_path = db.Column(db.String(255), nullable=True)
    generos = db.Column(db.String(255), nullable=True)
    elenco = db.Column(db.Text, nullable=True)
    diretor = db.Column(db.String(255), nullable=True)
    keywords = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Filme {self.titulo}>'


class Favoritos(db.Model):
    __tablename__ = 'favoritos'
    id = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id'),
                           nullable=False)
    id_filme = db.Column(db.Integer, db.ForeignKey('filmes.tmdb_id'),
                         nullable=False)

    __table_args__ = (db.UniqueConstraint('id_usuario', 'id_filme',
                                          name='uq_usuario_filme'),)

    def __repr__(self):
        return f'<Favorito usuario_id={self.id_usuario} filme_id={self.id_filme}>'


class Avaliacao(db.Model):
    __tablename__ = 'avaliacoes'
    id = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id'),
                           nullable=False)
    id_filme = db.Column(db.Integer, db.ForeignKey('filmes.tmdb_id'),
                         nullable=False)
    nota = db.Column(db.Integer, nullable=False)
    data_avaliacao = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('id_usuario', 'id_filme',
                                          name='uq_usuario_avaliacao'),)

    def __repr__(self):
        return f'<Avaliacao usuario={self.id_usuario} Filme={self.id_filme} Nota={self.nota}>'
