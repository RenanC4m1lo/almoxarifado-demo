# ============================================================
# routes/auth.py - Rotas de autenticação
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt, get_jwt_identity
import bcrypt
from config import conectar, fechar

auth_bp = Blueprint("auth", __name__)


# ============================================================
# ROTA: POST /api/auth/login
# ============================================================
@auth_bp.route("/login", methods=["POST"])
def login():
    dados = request.get_json()

    if not dados or not dados.get("email") or not dados.get("senha"):
        return jsonify({"erro": "Email e senha são obrigatórios"}), 400

    email = dados.get("email")
    senha = dados.get("senha")
    # id_empresa_selecionada = empresa que o usuário escolheu na tela de seleção
    id_empresa_selecionada = dados.get("id_empresa")

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT u.*, e.nome AS empresa_nome
        FROM usuarios u
        LEFT JOIN empresas e ON u.id_empresa = e.id
        WHERE u.email = %s AND u.ativo = 1
    """, (email,))
    usuario = cursor.fetchone()
    fechar(conexao, cursor)

    if not usuario:
        return jsonify({"erro": "Usuário não encontrado"}), 404

    senha_correta = bcrypt.checkpw(
        senha.encode("utf-8"),
        usuario["senha"].encode("utf-8")
    )

    if not senha_correta:
        return jsonify({"erro": "Senha incorreta"}), 401

    # Se o usuário tem acesso a todas as empresas e não selecionou ainda
    # retorna a lista de empresas para ele escolher
    if usuario["acesso_todas"] and not id_empresa_selecionada:
        return jsonify({
            "selecionar_empresa": True,
            "mensagem": "Selecione a empresa que deseja acessar",
            "usuario_temp": {
                "email": usuario["email"],
                "nome": usuario["nome"]
            }
        }), 200

    # Define qual empresa o usuário vai acessar
    empresa_acesso = id_empresa_selecionada or usuario["id_empresa"]

    # Busca o nome da empresa selecionada
    conexao2 = conectar()
    cursor2 = conexao2.cursor(dictionary=True)
    cursor2.execute("SELECT * FROM empresas WHERE id = %s", (empresa_acesso,))
    empresa = cursor2.fetchone()
    fechar(conexao2, cursor2)

    # Gera o token com informações da empresa
    token = create_access_token(
        identity=str(usuario["id"]),
        additional_claims={
            "nome":         usuario["nome"],
            "perfil":       usuario["perfil"],
            "id_empresa":   empresa_acesso,
            "empresa_nome": empresa["nome"] if empresa else "",
            "acesso_todas": usuario["acesso_todas"]
        }
    )

    return jsonify({
        "token": token,
        "usuario": {
            "id":           usuario["id"],
            "nome":         usuario["nome"],
            "email":        usuario["email"],
            "perfil":       usuario["perfil"],
            "id_empresa":   empresa_acesso,
            "empresa_nome": empresa["nome"] if empresa else "",
            "acesso_todas": usuario["acesso_todas"]
        }
    }), 200


# ============================================================
# ROTA: POST /api/auth/registrar
# ============================================================
@auth_bp.route("/registrar", methods=["POST"])
@jwt_required()
def registrar():
    claims = get_jwt()

    if claims.get("perfil") != "admin":
        return jsonify({"erro": "Apenas administradores podem cadastrar usuários"}), 403

    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return jsonify({"erro": "Corpo da requisição inválido"}), 400

    if not dados.get("nome") or not dados.get("email") or not dados.get("senha"):
        return jsonify({"erro": "Nome, email e senha são obrigatórios"}), 400

    perfil = dados.get("perfil", "visitante")
    if perfil not in ("admin", "operador", "visitante"):
        return jsonify({"erro": "Perfil inválido"}), 400

    # Só um Super Admin (acesso_todas) pode escolher livremente a empresa do
    # novo usuário ou torná-lo Super Admin também; um admin comum só cria
    # usuários dentro da própria empresa e nunca com acesso_todas.
    if claims.get("acesso_todas"):
        id_empresa    = dados.get("id_empresa", claims.get("id_empresa"))
        acesso_todas  = 1 if dados.get("acesso_todas") else 0
    else:
        id_empresa    = claims.get("id_empresa")
        acesso_todas  = 0

    senha_hash = bcrypt.hashpw(
        dados["senha"].encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute("""
            INSERT INTO usuarios (nome, email, senha, perfil, id_empresa, acesso_todas)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            dados["nome"],
            dados["email"],
            senha_hash,
            perfil,
            id_empresa,
            acesso_todas
        ))
        conexao.commit()
        fechar(conexao, cursor)
        return jsonify({"mensagem": "Usuário criado com sucesso!"}), 201

    except Exception as e:
        conexao.rollback()
        fechar(conexao, cursor)
        return jsonify({"erro": str(e)}), 400

    # ============================================================
# ROTA: POST /api/auth/trocar-empresa
# Permite que o Super Admin troque de empresa sem logout
# ============================================================

@auth_bp.route("/trocar-empresa", methods=["POST"])
@jwt_required()
def trocar_empresa():
    claims = get_jwt()

    # Só Super Admin (acesso_todas = 1) pode trocar de empresa
    if not claims.get("acesso_todas"):
        return jsonify({"erro": "Você não tem permissão para trocar de empresa"}), 403

    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return jsonify({"erro": "Corpo da requisição inválido"}), 400

    nova_empresa_id = dados.get("id_empresa")

    if not nova_empresa_id:
        return jsonify({"erro": "id_empresa é obrigatório"}), 400

    # Valida se a empresa existe
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)
    cursor.execute("SELECT * FROM empresas WHERE id = %s", (nova_empresa_id,))
    empresa = cursor.fetchone()
    fechar(conexao, cursor)

    if not empresa:
        return jsonify({"erro": "Empresa não encontrada"}), 404

    # Pega o id do usuário logado (vem do token atual)
    id_usuario = get_jwt_identity()

    # Gera um novo token, com os mesmos dados do usuário mas empresa nova
    novo_token = create_access_token(
        identity=id_usuario,
        additional_claims={
            "nome":         claims.get("nome"),
            "perfil":       claims.get("perfil"),
            "id_empresa":   empresa["id"],
            "empresa_nome": empresa["nome"],
            "acesso_todas": claims.get("acesso_todas")
        }
    )

    return jsonify({
        "token": novo_token,
        "usuario": {
            "id":           id_usuario,
            "nome":         claims.get("nome"),
            "perfil":       claims.get("perfil"),
            "id_empresa":   empresa["id"],
            "empresa_nome": empresa["nome"],
            "acesso_todas": claims.get("acesso_todas")
        }
    }), 200