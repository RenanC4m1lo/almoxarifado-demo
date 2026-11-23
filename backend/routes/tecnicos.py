# ============================================================
# routes/tecnicos.py - Rotas de técnicos de campo com filtro por empresa
#
# Usado principalmente como lista de escolha no campo "Responsável"
# das telas de Movimentações e Unidades, pra evitar nome digitado
# de forma inconsistente (ex: "DIEGO" vs "DIEGO " com espaço a mais).
#
# Mesmo pras contas Super Admin (acesso_todas), a lista sempre reflete
# só a empresa selecionada no momento - igual equipamentos.py - já
# que o técnico é escolhido no contexto de uma saída/devolução dessa
# empresa, não faz sentido misturar técnicos de outra.
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from config import conectar, fechar

tecnicos_bp = Blueprint("tecnicos", __name__)


# ============================================================
# ROTA: GET /api/tecnicos
# ============================================================
@tecnicos_bp.route("/", methods=["GET"])
@jwt_required()
def listar():
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")

    if claims.get("perfil") == "visitante":
        return jsonify({"erro": "Sem permissão"}), 403

    conexao = conectar()
    cursor  = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM tecnicos
        WHERE id_empresa = %s
        ORDER BY nome ASC
    """, (id_empresa,))

    tecnicos = cursor.fetchall()
    fechar(conexao, cursor)
    return jsonify(tecnicos), 200


# ============================================================
# ROTA: POST /api/tecnicos
# ============================================================
@tecnicos_bp.route("/", methods=["POST"])
@jwt_required()
def cadastrar():
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")

    if claims.get("perfil") != "admin":
        return jsonify({"erro": "Apenas administradores podem cadastrar técnicos"}), 403

    dados = request.get_json()

    if not dados.get("nome"):
        return jsonify({"erro": "Nome do técnico é obrigatório"}), 400

    conexao = conectar()
    cursor  = conexao.cursor()

    try:
        cursor.execute("""
            INSERT INTO tecnicos (nome, telefone, id_empresa)
            VALUES (%s, %s, %s)
        """, (
            dados.get("nome"),
            dados.get("telefone"),
            id_empresa # sempre a empresa do token, nunca a escolhida pelo cliente
        ))
        conexao.commit()
        novo_id = cursor.lastrowid
        fechar(conexao, cursor)
        return jsonify({
            "mensagem": "Técnico cadastrado com sucesso!",
            "id": novo_id
        }), 201

    except Exception as e:
        conexao.rollback()
        fechar(conexao, cursor)
        return jsonify({"erro": str(e)}), 400


# ============================================================
# ROTA: PUT /api/tecnicos/<id>
# ============================================================
@tecnicos_bp.route("/<int:id>", methods=["PUT"])
@jwt_required()
def atualizar(id):
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")

    if claims.get("perfil") != "admin":
        return jsonify({"erro": "Apenas administradores podem editar técnicos"}), 403

    dados   = request.get_json()
    conexao = conectar()
    cursor  = conexao.cursor()

    try:
        cursor.execute("""
            UPDATE tecnicos SET nome = %s, telefone = %s, ativo = %s
            WHERE id = %s AND id_empresa = %s
        """, (
            dados.get("nome"),
            dados.get("telefone"),
            dados.get("ativo", 1),
            id,
            id_empresa
        ))

        if cursor.rowcount == 0:
            fechar(conexao, cursor)
            return jsonify({"erro": "Técnico não encontrado"}), 404

        conexao.commit()
        fechar(conexao, cursor)
        return jsonify({"mensagem": "Técnico atualizado com sucesso!"}), 200

    except Exception as e:
        conexao.rollback()
        fechar(conexao, cursor)
        return jsonify({"erro": str(e)}), 400


# ============================================================
# ROTA: DELETE /api/tecnicos/<id>
# ============================================================
@tecnicos_bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
def deletar(id):
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")

    if claims.get("perfil") != "admin":
        return jsonify({"erro": "Apenas administradores podem deletar técnicos"}), 403

    conexao = conectar()
    cursor  = conexao.cursor()

    try:
        cursor.execute(
            "DELETE FROM tecnicos WHERE id = %s AND id_empresa = %s",
            (id, id_empresa)
        )

        if cursor.rowcount == 0:
            fechar(conexao, cursor)
            return jsonify({"erro": "Técnico não encontrado"}), 404

        conexao.commit()
        fechar(conexao, cursor)
        return jsonify({"mensagem": "Técnico removido com sucesso!"}), 200

    except Exception as e:
        conexao.rollback()
        fechar(conexao, cursor)
        return jsonify({"erro": str(e)}), 400
