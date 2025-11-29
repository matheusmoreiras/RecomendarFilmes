# RotaCine - Recomendação de filmes

Recomendações de filmes personalizadas com aprendizado de máquina.

### Funcionalidades:

* **Autenticação de usuário**
* **Cadastro de novos usuários**
* **Segurança de senhas**
* **Recuperação de senhas**
* **Busca de filmes**
* **Sistema de favoritos**
* **Sistema de avaliações**
* **Recomendação baseada em conteúdo (NLP)**
* **Recomendação colaborativa (SVD)**
* **Recomendação híbrida (NLP + SVD)**


### Tecnologias:

**Backend**
* Python 3.11, Flask, SQLAlchemy e PostgreSQL

**Frontend**
* Python 3.11, Streamlit e CSS

### Como executar o projeto?

Siga os passos abaixo para configurar e executar localmente.

**Pré-requisitos:**
* Git
* Docker Desktop instalado e em execução

Python e PostgreSQL não são necessários.
(Caso deseje treinar os modelos por sí, python 3.11 é necessário.)

## Configuração do Backend e Docker

**1. Clone o repositório**
```
$ git clone https://github.com/matheusmoreiras/RecomendarFilmes
```

**2. Configure o .env**

```
# no Windows (CMD ou PowerShell) navegue até a pasta do clone:
$ cd RecomendarFilmes
$ copy .env.example .env

# No macOS/Linux ou Git Bash:
$ cp .env.example .env
```
Abra o arquivo .env em um editor de código. Os valores padrão do banco de dados já devem funcionar. Se quiser testar a redefinição de senha, preencha as variáveis de email.

_Para ativar e verificar senhas de app: https://support.google.com/accounts/answer/185833?hl=pt-br_

## Execute a aplicação

**Terminal 1 - Docker**
```
# No terminal, navegue até a pasta RecomendarFilmes, com Docker Desktop aberto
# "--build" necessário apenas na primeira execução
$ docker-compose up --build

# Para outras execuções:
$ docker-compose up
```
_Após iniciar, use a URL: http://localhost:8501 no seu navegador_

## Modelo de Recomendaçao (ML)

A aplicação utiliza dois modelos pré-treinados (`.pkl`) para gerar as recomendações:
1. **SVD (Collaborative Filtering):** Para descobertas baseadas em padrões de usuários.
2. **Transformer NLP (Content-Based):** Para similaridade de conteúdo (sinopse, gêneros, etc).

O repositório já inclui esses arquivos treinados com o dataset do **MovieLens**, garantindo que a aplicação funcione imediatamente sem necessidade de retreino.

### Como treinar (opcional)
Caso deseje atualizar os modelos ou testar com seus próprios dados:
```
$ cd ml_scripts
# Windows
$ python -m venv venv
$ "venv\scripts\activate"
$ pip install -r requirements.txt
```
Por fim, execute os notebooks .ipynb (Jupyter) para gerar novos arquivos (`.pkl`), e cole esses arquivos em ``\backend``.

## Aviso importante sobre dados locais
Os modelos incluídos no repositório foram treinados apenas com dados públicos (MovieLens) para evitar conflitos de IDs. Se treinar o modelo com os notebooks .ipynb, ele aprenderá de acordo com gostos do banco de dados LOCAL, se houver alguma alteração no seu banco de dados, ou compartilhar, os IDS do novo BD herdarão os gostos de **SEUS** IDS antigos. Gerando recomendações incorretas, mantenha o treino híbrido (movielens + local) apenas para SEU uso pessoal.


### Endpoints da API

Rotas protegidas requerem um Token JWT no cabeçalho de autorização. Rotas do Flask;
```
Endpoint	        Método	     Descrição	

/login	                    POST	   Autentica um usuário
/cadastro	                POST	   Cadastra um novo usuário
/reset_senha                POST       Solicita a redefinição de senha
/redefinir	                POST	   Redefine a senha (com token válido)
/filmes/pesquisar           GET	       Busca filmes no banco de dados
/favoritos                  GET	       Adiciona um filme à lista de favoritos do usuário.
/favoritos/<tmdb_id>        DELETE     Remove um filme da lista de favoritos do usuário.
/recomendar/multiplos       POST       Recomendação baseada em conteúdo
/avaliar                    POST       Manipula avaliações
/usuario/minhas-avaliacoes  GET        Lista avaliações
/avaliar/<int:tmdb_id>      DELETE     Remove uma avaliação
/recomendar/colaborativo    GET        Recomendação com filtragem colaborativa
/recomendar/hibrido         GET        Recomendação híbrida (conteúdo + colaborativa)
```
