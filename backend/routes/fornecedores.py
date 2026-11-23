# ============================================================
# routes/fornecedores.py - Rotas de fornecedores com filtro por empresa
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from config import conectar, fechar

fornecedores_bp = Blueprint("fornecedores", __name__)


# ============================================================
# ROTA: GET /api/fornecedores
# ============================================================
@fornecedores_bp.route("/", methods=["GET"])
@jwt_required()
def listar():
    claims       = get_jwt()
    id_empresa   = claims.get("id_empresa")
    acesso_todas = claims.get("acesso_todas", 0)

    conexao = conectar()
    cursor  = conexao.cursor(dictionary=True)

    if acesso_todas:
        cursor.execute("""
            SELECT f.*, e.nome AS empresa_nome
            FROM fornecedores f
            LEFT JOIN empresas e ON f.id_empresa = e.id
            ORDER BY e.nome ASC, f.nome ASC
        """)
    else:
        cursor.execute("""
            SELECT f.*, e.nome AS empresa_nome
            FROM fornecedores f
            LEFT JOIN empresas e ON f.id_empresa = e.id
            WHERE f.id_empresa = %s
            ORDER BY f.nome ASC
        """, (id_empresa,))

    fornecedores = cursor.fetchall()
    fechar(conexao, cursor)
    return jsonify(fornecedores), 200


# ============================================================
# ROTA: POST /api/fornecedores
# ============================================================
@fornecedores_bp.route("/", methods=["POST"])
@jwt_required()
def cadastrar():
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")

    if claims.get("perfil") != "admin":
        return jsonify({"erro": "Apenas administradores podem cadastrar fornecedores"}), 403

    dados = request.get_json()

    if not dados.get("nome"):
        return jsonify({"erro": "Nome do fornecedor é obrigatório"}), 400

    conexao = conectar()
    cursor  = conexao.cursor()

    try:
        cursor.execute("""
            INSERT INTO fornecedores (nome, cnpj, contato, telefone, email, id_empresa)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            dados.get("nome"),
            dados.get("cnpj"),
            dados.get("contato"),
            dados.get("telefone"),
            dados.get("email"),
            id_empresa # sempre a empresa do token, nunca a escolhida pelo cliente
        ))
        conexao.commit()
        novo_id = cursor.lastrowid
        fechar(conexao, cursor)
        return jsonify({
            "mensagem": "Fornecedor cadastrado com sucesso!",
            "id": novo_id
        }), 201

    except Exception as e:
        conexao.rollback()
        fechar(conexao, cursor)
        return jsonify({"erro": str(e)}), 400


# ============================================================
# ROTA: PUT /api/fornecedores/<id>
# ============================================================
@fornecedores_bp.route("/<int:id>", methods=["PUT"])
@jwt_required()
def atualizar(id):
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")

    if claims.get("perfil") != "admin":
        return jsonify({"erro": "Apenas administradores podem editar fornecedores"}), 403

    dados   = request.get_json()
    conexao = conectar()
    cursor  = conexao.cursor()

    try:
        cursor.execute("""
            UPDATE fornecedores SET
                nome = %s, cnpj = %s, contato = %s,
                telefone = %s, email = %s, ativo = %s
            WHERE id = %s AND id_empresa = %s
        """, (
            dados.get("nome"),
            dados.get("cnpj"),
            dados.get("contato"),
            dados.get("telefone"),
            dados.get("email"),
            dados.get("ativo", 1),
            id,
            id_empresa
        ))
        conexao.commit()
        fechar(conexao, cursor)
        return jsonify({"mensagem": "Fornecedor atualizado com sucesso!"}), 200

    except Exception as e:
        conexao.rollback()
        fechar(conexao, cursor)
        return jsonify({"erro": str(e)}), 400


# ============================================================
# ROTA: DELETE /api/fornecedores/<id>
# ============================================================
@fornecedores_bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
def deletar(id):
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")

    if claims.get("perfil") != "admin":
        return jsonify({"erro": "Apenas administradores podem deletar fornecedores"}), 403

    conexao = conectar()
    cursor  = conexao.cursor()

    try:
        cursor.execute("""
            DELETE FROM fornecedores WHERE id = %s AND id_empresa = %s
        """, (id, id_empresa))
        conexao.commit()
        fechar(conexao, cursor)
        return jsonify({"mensagem": "Fornecedor removido com sucesso!"}), 200

    except Exception as e:
        conexao.rollback()
        fechar(conexao, cursor)
        return jsonify({"erro": str(e)}), 400