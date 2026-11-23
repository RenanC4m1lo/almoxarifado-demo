# ============================================================
# routes/usuarios.py - Rotas de usuários com suporte a empresas
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
import bcrypt
from config import conectar, fechar

usuarios_bp = Blueprint("usuarios", __name__)


# ============================================================
# ROTA: GET /api/usuarios
# ============================================================
@usuarios_bp.route("/", methods=["GET"])
@jwt_required()
def listar():
    claims       = get_jwt()
    id_empresa   = claims.get("id_empresa")
    acesso_todas = claims.get("acesso_todas", 0)

    if claims.get("perfil") != "admin":
        return jsonify({"erro": "Apenas administradores podem listar usuários"}), 403

    conexao = conectar()
    cursor  = conexao.cursor(dictionary=True)

    if acesso_todas:
        cursor.execute("""
            SELECT u.id, u.nome, u.email, u.perfil, u.ativo,
                   u.acesso_todas, u.criado_em,
                   e.nome AS empresa_nome, u.id_empresa
            FROM usuarios u
            LEFT JOIN empresas e ON u.id_empresa = e.id
            ORDER BY e.nome ASC, u.nome ASC
        """)
    else:
        cursor.execute("""
            SELECT u.id, u.nome, u.email, u.perfil, u.ativo,
                   u.acesso_todas, u.criado_em,
                   e.nome AS empresa_nome, u.id_empresa
            FROM usuarios u
            LEFT JOIN empresas e ON u.id_empresa = e.id
            WHERE u.id_empresa = %s
            ORDER BY u.nome ASC
        """, (id_empresa,))

    usuarios = cursor.fetchall()
    fechar(conexao, cursor)
    return jsonify(usuarios), 200


# ============================================================
# ROTA: PUT /api/usuarios/<id>
# ============================================================
@usuarios_bp.route("/<int:id>", methods=["PUT"])
@jwt_required()
def atualizar(id):
    claims       = get_jwt()
    id_empresa   = claims.get("id_empresa")
    acesso_todas = claims.get("acesso_todas", 0)

    if claims.get("perfil") != "admin":
        return jsonify({"erro": "Apenas administradores podem editar usuários"}), 403

    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return jsonify({"erro": "Corpo da requisição inválido"}), 400

    conexao = conectar()
    cursor  = conexao.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM usuarios WHERE id = %s", (id,))
        usuario_alvo = cursor.fetchone()

        if not usuario_alvo:
            fechar(conexao, cursor)
            return jsonify({"erro": "Usuário não encontrado"}), 404

        # Admin comum só edita usuários da própria empresa
        if not acesso_todas and usuario_alvo["id_empresa"] != id_empresa:
            fechar(conexao, cursor)
            return jsonify({"erro": "Sem permissão para editar esse usuário"}), 403

        if dados.get("senha"):
            senha_hash = bcrypt.hashpw(
                dados["senha"].encode("utf-8"),
                bcrypt.gensalt()
            ).decode("utf-8")
        else:
            senha_hash = usuario_alvo["senha"]

        # Só um Super Admin pode mudar a empresa do usuário ou conceder acesso_todas
        if acesso_todas:
            nova_empresa      = dados.get("id_empresa", usuario_alvo["id_empresa"])
            novo_acesso_todas = 1 if dados.get("acesso_todas") else 0
        else:
            nova_empresa      = usuario_alvo["id_empresa"]
            novo_acesso_todas = usuario_alvo["acesso_todas"]

        cursor2 = conexao.cursor()
        cursor2.execute("""
            UPDATE usuarios SET
                nome = %s, email = %s, senha = %s,
                perfil = %s, ativo = %s,
                id_empresa = %s, acesso_todas = %s
            WHERE id = %s
        """, (
            dados.get("nome", usuario_alvo["nome"]),
            dados.get("email", usuario_alvo["email"]),
            senha_hash,
            dados.get("perfil", usuario_alvo["perfil"]),
            dados.get("ativo", usuario_alvo["ativo"]),
            nova_empresa,
            novo_acesso_todas,
            id
        ))
        conexao.commit()
        fechar(conexao, cursor2)
        return jsonify({"mensagem": "Usuário atualizado com sucesso!"}), 200

    except Exception as e:
        conexao.rollback()
        fechar(conexao, cursor)
        return jsonify({"erro": str(e)}), 400


# ============================================================
# ROTA: DELETE /api/usuarios/<id>
# ============================================================
@usuarios_bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
def deletar(id):
    claims       = get_jwt()
    id_empresa   = claims.get("id_empresa")
    acesso_todas = claims.get("acesso_todas", 0)

    if claims.get("perfil") != "admin":
        return jsonify({"erro": "Apenas administradores podem deletar usuários"}), 403

    conexao = conectar()
    cursor  = conexao.cursor()

    try:
        if acesso_todas:
            cursor.execute("DELETE FROM usuarios WHERE id = %s", (id,))
        else:
            cursor.execute(
                "DELETE FROM usuarios WHERE id = %s AND id_empresa = %s",
                (id, id_empresa)
            )

        if cursor.rowcount == 0:
            fechar(conexao, cursor)
            return jsonify({"erro": "Usuário não encontrado"}), 404

        conexao.commit()
        fechar(conexao, cursor)
        return jsonify({"mensagem": "Usuário removido com sucesso!"}), 200

    except Exception as e:
        conexao.rollback()
        fechar(conexao, cursor)
        return jsonify({"erro": str(e)}), 400