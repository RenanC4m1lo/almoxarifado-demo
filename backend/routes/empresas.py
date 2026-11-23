# ============================================================
# routes/empresas.py - Rotas de empresas
# Gerencia as empresas do sistema (multi-filial)
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from config import conectar, fechar

empresas_bp = Blueprint("empresas", __name__)


# ============================================================
# ROTA: GET /api/empresas
# Lista todas as empresas
# ============================================================
@empresas_bp.route("/", methods=["GET"])
@jwt_required()
def listar():
    claims       = get_jwt()
    acesso_todas = claims.get("acesso_todas", 0)
    id_empresa   = claims.get("id_empresa")

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    if acesso_todas:
        cursor.execute("SELECT * FROM empresas WHERE ativo = 1 ORDER BY nome ASC")
    else:
        cursor.execute("SELECT * FROM empresas WHERE id = %s AND ativo = 1", (id_empresa,))

    empresas = cursor.fetchall()
    fechar(conexao, cursor)
    return jsonify(empresas), 200


# ============================================================
# ROTA: GET /api/empresas/minhas
# Retorna as empresas que o usuário logado pode acessar
# ============================================================
@empresas_bp.route("/minhas", methods=["GET"])
@jwt_required()
def minhas_empresas():
    claims = get_jwt()
    acesso_todas = claims.get("acesso_todas", 0)
    id_empresa   = claims.get("id_empresa")

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    if acesso_todas:
        # Super admin vê todas as empresas
        cursor.execute("SELECT * FROM empresas WHERE ativo = 1 ORDER BY nome ASC")
    else:
        # Usuário comum vê só a sua empresa
        cursor.execute("SELECT * FROM empresas WHERE id = %s", (id_empresa,))

    empresas = cursor.fetchall()
    fechar(conexao, cursor)
    return jsonify(empresas), 200