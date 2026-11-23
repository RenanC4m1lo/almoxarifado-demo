# ============================================================
# routes/alertas.py - Rotas de alertas com filtro por empresa
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from config import conectar, fechar

alertas_bp = Blueprint("alertas", __name__)


# ============================================================
# ROTA: GET /api/alertas
# ============================================================
@alertas_bp.route("/", methods=["GET"])
@jwt_required()
def listar():
    claims = get_jwt()
    id_empresa = claims.get("id_empresa")

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    # Verifica se existe equipamento com estoque baixo que ainda não tem
    # alerta ativo (ex: já estava baixo antes, sem nenhuma mudança recente)
    cursor.execute("""
        SELECT e.id, e.nome, e.quantidade, e.quantidade_minima
        FROM equipamentos e
        WHERE e.id_empresa = %s
          AND e.quantidade <= e.quantidade_minima
          AND NOT EXISTS (
              SELECT 1 FROM alertas a
              WHERE a.id_equipamento = e.id AND a.lido = 0
          )
    """, (id_empresa,))
    pendentes = cursor.fetchall()

    for eq in pendentes:
        tipo_alerta = "sem_estoque" if eq["quantidade"] == 0 else "estoque_baixo"
        cursor.execute("""
            INSERT INTO alertas (mensagem, tipo, id_equipamento, id_empresa)
            VALUES (%s, %s, %s, %s)
        """, (
            f"Estoque baixo: {eq['nome']} tem apenas {eq['quantidade']} unidade(s)",
            tipo_alerta,
            eq["id"],
            id_empresa
        ))

    if pendentes:
        conexao.commit()

    cursor.execute("""
        SELECT a.*, e.nome AS equipamento_nome,
               e.quantidade, emp.nome AS empresa_nome
        FROM alertas a
        LEFT JOIN equipamentos e ON a.id_equipamento = e.id
        LEFT JOIN empresas emp ON a.id_empresa = emp.id
        WHERE a.id_empresa = %s AND a.lido = 0
        ORDER BY a.criado_em DESC
    """, (id_empresa,))

    alertas = cursor.fetchall()
    fechar(conexao, cursor)
    return jsonify(alertas), 200

# ============================================================
# ROTA: GET /api/alertas/nao-lidos
# ============================================================
@alertas_bp.route("/nao-lidos", methods=["GET"])
@jwt_required()
def contar_nao_lidos():
    claims       = get_jwt()
    id_empresa   = claims.get("id_empresa")

    conexao = conectar()
    cursor  = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT COUNT(*) AS total FROM alertas
        WHERE lido = 0 AND id_empresa = %s
    """, (id_empresa,))

    resultado = cursor.fetchone()
    fechar(conexao, cursor)
    return jsonify({"total": resultado["total"]}), 200


# ============================================================
# ROTA: PUT /api/alertas/<id>/marcar-lido
# ============================================================
@alertas_bp.route("/<int:id>/marcar-lido", methods=["PUT"])
@jwt_required()
def marcar_lido(id):
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")

    conexao = conectar()
    cursor  = conexao.cursor()

    try:
        cursor.execute(
            "UPDATE alertas SET lido = 1 WHERE id = %s AND id_empresa = %s",
            (id, id_empresa)
        )

        if cursor.rowcount == 0:
            fechar(conexao, cursor)
            return jsonify({"erro": "Alerta não encontrado"}), 404

        conexao.commit()
        fechar(conexao, cursor)
        return jsonify({"mensagem": "Alerta marcado como lido!"}), 200

    except Exception as e:
        conexao.rollback()
        fechar(conexao, cursor)
        return jsonify({"erro": str(e)}), 400


# ============================================================
# ROTA: PUT /api/alertas/marcar-todos-lidos
# ============================================================
@alertas_bp.route("/marcar-todos-lidos", methods=["PUT"])
@jwt_required()
def marcar_todos_lidos():
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")

    conexao = conectar()
    cursor  = conexao.cursor()

    try:
        cursor.execute("""
            UPDATE alertas SET lido = 1
            WHERE lido = 0 AND id_empresa = %s
        """, (id_empresa,))

        conexao.commit()
        fechar(conexao, cursor)
        return jsonify({"mensagem": "Todos os alertas marcados como lidos!"}), 200

    except Exception as e:
        conexao.rollback()
        fechar(conexao, cursor)
        return jsonify({"erro": str(e)}), 400


# ============================================================
# ROTA: DELETE /api/alertas/<id>
# ============================================================
@alertas_bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
def deletar(id):
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")

    if claims.get("perfil") != "admin":
        return jsonify({"erro": "Apenas administradores podem deletar alertas"}), 403

    conexao = conectar()
    cursor  = conexao.cursor()

    try:
        cursor.execute(
            "DELETE FROM alertas WHERE id = %s AND id_empresa = %s",
            (id, id_empresa)
        )

        if cursor.rowcount == 0:
            fechar(conexao, cursor)
            return jsonify({"erro": "Alerta não encontrado"}), 404

        conexao.commit()
        fechar(conexao, cursor)
        return jsonify({"mensagem": "Alerta removido com sucesso!"}), 200

    except Exception as e:
        conexao.rollback()
        fechar(conexao, cursor)
        return jsonify({"erro": str(e)}), 400