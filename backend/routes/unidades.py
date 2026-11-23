# ============================================================
# routes/unidades.py - Rotas de unidades com filtro por empresa
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from config import conectar, fechar

unidades_bp = Blueprint("unidades", __name__)


def recalcular_quantidade(cursor, id_equipamento):
    """
    Recalcula equipamentos.quantidade a partir da contagem de unidades
    disponíveis. Chamada sempre que o status de uma unidade muda, pra
    manter o contador do equipamento consistente com as unidades reais.
    """
    cursor.execute("""
        UPDATE equipamentos
        SET quantidade = (
            SELECT COUNT(*) FROM unidades
            WHERE id_equipamento = %s AND status = 'disponivel'
        )
        WHERE id = %s
    """, (id_equipamento, id_equipamento))


# ============================================================
# ROTA: GET /api/unidades
# ============================================================
@unidades_bp.route("/", methods=["GET"])
@jwt_required()
def listar():
    claims       = get_jwt()
    id_empresa   = claims.get("id_empresa")
    id_equipamento = request.args.get("id_equipamento")

    conexao = conectar()
    cursor  = conexao.cursor(dictionary=True)

    # Igual equipamentos.py: mesmo o Super Admin (acesso_todas) só vê a
    # empresa atualmente selecionada no topo — trocar de empresa é o
    # mecanismo de navegar entre elas, não uma visão global misturada.
    if id_equipamento:
        cursor.execute("""
            SELECT u.*, e.nome AS equipamento_nome, emp.nome AS empresa_nome
            FROM unidades u
            LEFT JOIN equipamentos e ON u.id_equipamento = e.id
            LEFT JOIN empresas emp ON u.id_empresa = emp.id
            WHERE u.id_equipamento = %s AND u.id_empresa = %s
            ORDER BY u.codigo_barras ASC
        """, (id_equipamento, id_empresa))
    else:
        cursor.execute("""
            SELECT u.*, e.nome AS equipamento_nome, emp.nome AS empresa_nome
            FROM unidades u
            LEFT JOIN equipamentos e ON u.id_equipamento = e.id
            LEFT JOIN empresas emp ON u.id_empresa = emp.id
            WHERE u.id_empresa = %s
            ORDER BY e.nome ASC, u.codigo_barras ASC
        """, (id_empresa,))

    unidades = cursor.fetchall()
    fechar(conexao, cursor)
    return jsonify(unidades), 200


# ============================================================
# ROTA: GET /api/unidades/todas-empresas
# Junta unidades de todas as empresas - mesma exceção usada em
# movimentacoes.py e equipamentos.py, só pro card combinado do
# Dashboard (Super Admin).
# ============================================================
@unidades_bp.route("/todas-empresas", methods=["GET"])
@jwt_required()
def listar_todas_empresas():
    claims = get_jwt()

    if not claims.get("acesso_todas"):
        return jsonify({"erro": "Sem permissão"}), 403

    conexao = conectar()
    cursor  = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT u.*, e.nome AS equipamento_nome, e.categoria, emp.nome AS empresa_nome
        FROM unidades u
        LEFT JOIN equipamentos e ON u.id_equipamento = e.id
        LEFT JOIN empresas emp ON u.id_empresa = emp.id
    """)

    unidades = cursor.fetchall()
    fechar(conexao, cursor)
    return jsonify(unidades), 200


# ============================================================
# ROTA: GET /api/unidades/barras/<codigo>
# ============================================================
@unidades_bp.route("/barras/<codigo>", methods=["GET"])
@jwt_required()
def buscar_por_barras(codigo):
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")

    conexao = conectar()
    cursor  = conexao.cursor(dictionary=True)

    # Mesmo pro Super Admin, a busca so encontra unidades da empresa
    # atualmente selecionada — evita registrar saida/devolucao na
    # empresa errada por engano.
    cursor.execute("""
        SELECT u.*, e.nome AS equipamento_nome,
               e.categoria, e.localizacao, emp.nome AS empresa_nome
        FROM unidades u
        LEFT JOIN equipamentos e ON u.id_equipamento = e.id
        LEFT JOIN empresas emp ON u.id_empresa = emp.id
        WHERE u.codigo_barras = %s AND u.id_empresa = %s
    """, (codigo, id_empresa))

    unidade = cursor.fetchone()
    fechar(conexao, cursor)

    if not unidade:
        return jsonify({"erro": "Unidade não encontrada"}), 404

    return jsonify(unidade), 200


# ============================================================
# ROTA: GET /api/unidades/buscar?q=trecho
# Busca unidades por qualquer trecho do código de barras (ex: só os
# últimos dígitos), pra quando não se sabe o código completo.
# ============================================================
@unidades_bp.route("/buscar", methods=["GET"])
@jwt_required()
def buscar_parcial():
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")
    termo      = (request.args.get("q") or "").strip()

    if not termo:
        return jsonify([]), 200

    conexao = conectar()
    cursor  = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT u.*, e.nome AS equipamento_nome,
               e.categoria, e.localizacao, emp.nome AS empresa_nome
        FROM unidades u
        LEFT JOIN equipamentos e ON u.id_equipamento = e.id
        LEFT JOIN empresas emp ON u.id_empresa = emp.id
        WHERE u.id_empresa = %s AND u.codigo_barras LIKE %s
        ORDER BY u.codigo_barras ASC
        LIMIT 20
    """, (id_empresa, f"%{termo}%"))

    unidades = cursor.fetchall()
    fechar(conexao, cursor)
    return jsonify(unidades), 200


# ============================================================
# ROTA: POST /api/unidades
# ============================================================
@unidades_bp.route("/", methods=["POST"])
@jwt_required()
def cadastrar():
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")

    if claims.get("perfil") == "visitante":
        return jsonify({"erro": "Sem permissão"}), 403

    dados = request.get_json()

    if not dados.get("id_equipamento") or not dados.get("codigo_barras"):
        return jsonify({"erro": "Equipamento e código de barras são obrigatórios"}), 400

    conexao = conectar()
    cursor  = conexao.cursor()

    try:
        cursor.execute("""
            INSERT INTO unidades
            (id_equipamento, codigo_barras, numero_serie, status, observacao, id_empresa)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            dados.get("id_equipamento"),
            dados.get("codigo_barras"),
            dados.get("numero_serie"),
            dados.get("status", "disponivel"),
            dados.get("observacao"),
            id_empresa
        ))

        novo_id = cursor.lastrowid

        recalcular_quantidade(cursor, dados.get("id_equipamento"))

        conexao.commit()
        fechar(conexao, cursor)
        return jsonify({
            "mensagem": "Unidade cadastrada com sucesso!",
            "id": novo_id
        }), 201

    except Exception as e:
        conexao.rollback()
        fechar(conexao, cursor)
        return jsonify({"erro": str(e)}), 400


# ============================================================
# ROTA: POST /api/unidades/saida
# ============================================================
@unidades_bp.route("/saida", methods=["POST"])
@jwt_required()
def registrar_saida():
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")

    if claims.get("perfil") == "visitante":
        return jsonify({"erro": "Sem permissão"}), 403

    dados       = request.get_json()
    codigo      = dados.get("codigo_barras")
    responsavel = dados.get("responsavel")

    if not codigo or not responsavel:
        return jsonify({"erro": "Código de barras e responsável são obrigatórios"}), 400

    conexao = conectar()
    cursor  = conexao.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT u.*, e.nome AS equipamento_nome,
                   e.quantidade_minima, e.nome
            FROM unidades u
            LEFT JOIN equipamentos e ON u.id_equipamento = e.id
            WHERE u.codigo_barras = %s AND u.id_empresa = %s
        """, (codigo, id_empresa))
        unidade = cursor.fetchone()

        if not unidade:
            return jsonify({"erro": "Unidade não encontrada com esse código"}), 404

        if unidade["status"] != "disponivel":
            return jsonify({
                "erro": f"Unidade não disponível. Status: {unidade['status']}"
            }), 400

        id_usuario = get_jwt_identity()
        cursor2    = conexao.cursor()

        cursor2.execute("""
            UPDATE unidades SET status = 'em_uso', responsavel_atual = %s
            WHERE id = %s
        """, (responsavel, unidade["id"]))

        cursor2.execute("""
            INSERT INTO movimentacoes
            (tipo, quantidade, responsavel, observacao, id_equipamento, id_usuario, id_empresa)
            VALUES ('saida', 1, %s, %s, %s, %s, %s)
        """, (
            responsavel,
            f"Unidade: {codigo}" + (f" | {dados.get('observacao')}"
                if dados.get("observacao") else ""),
            unidade["id_equipamento"],
            id_usuario,
            id_empresa
        ))

        recalcular_quantidade(cursor2, unidade["id_equipamento"])

        cursor2.execute("""
            SELECT quantidade, quantidade_minima, nome FROM equipamentos WHERE id = %s
        """, (unidade["id_equipamento"],))
        eq = cursor2.fetchone()

        if eq and eq[0] <= eq[1]:
            tipo_alerta = "sem_estoque" if eq[0] == 0 else "estoque_baixo"
            cursor2.execute("""
                INSERT INTO alertas (mensagem, tipo, id_equipamento, id_empresa)
                VALUES (%s, %s, %s, %s)
            """, (
                f"Estoque baixo: {eq[2]} tem apenas {eq[0]} unidade(s)",
                tipo_alerta,
                unidade["id_equipamento"],
                id_empresa
            ))

        conexao.commit()
        fechar(conexao, cursor2)
        return jsonify({
            "mensagem": f"Saída da unidade {codigo} registrada!",
            "equipamento": unidade["equipamento_nome"]
        }), 201

    except Exception as e:
        conexao.rollback()
        fechar(conexao, cursor)
        return jsonify({"erro": str(e)}), 400


# ============================================================
# ROTA: POST /api/unidades/devolucao
# ============================================================
@unidades_bp.route("/devolucao", methods=["POST"])
@jwt_required()
def registrar_devolucao():
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")

    if claims.get("perfil") == "visitante":
        return jsonify({"erro": "Sem permissão"}), 403

    dados       = request.get_json()
    codigo      = dados.get("codigo_barras")
    responsavel = dados.get("responsavel")
    condicao    = dados.get("condicao", "boa")  # "boa", "manutencao" ou "inutilizavel"
    if not codigo or not responsavel:
        return jsonify({"erro": "Código de barras e responsável são obrigatórios"}), 400

    if condicao not in ("boa", "manutencao", "inutilizavel"):
        return jsonify({"erro": "Condição de devolução inválida"}), 400

    conexao = conectar()
    cursor  = conexao.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT u.*, e.nome AS equipamento_nome
            FROM unidades u
            LEFT JOIN equipamentos e ON u.id_equipamento = e.id
            WHERE u.codigo_barras = %s AND u.id_empresa = %s
        """, (codigo, id_empresa))
        unidade = cursor.fetchone()

        if not unidade:
            return jsonify({"erro": "Unidade não encontrada"}), 404

        id_usuario = get_jwt_identity()
        cursor2    = conexao.cursor()

        status_por_condicao = {
            "boa": "disponivel",
            "manutencao": "manutencao",
            "inutilizavel": "inativo"
        }
        novo_status = status_por_condicao[condicao]

        cursor2.execute("""
            UPDATE unidades SET status = %s, responsavel_atual = NULL
            WHERE id = %s
        """, (novo_status, unidade["id"],))

        anotacao_condicao = {
            "manutencao": " (EM MANUTENÇÃO)",
            "inutilizavel": " (INUTILIZÁVEL/PERDIDO)"
        }.get(condicao, "")

        cursor2.execute("""
            INSERT INTO movimentacoes
            (tipo, quantidade, responsavel, observacao, condicao,
             data_devolucao_real, id_equipamento, id_usuario, id_empresa)
            VALUES ('devolucao', 1, %s, %s, %s, NOW(), %s, %s, %s)
        """, (
            responsavel,
             f"Devolução: {codigo}"
            + anotacao_condicao
            + (f" | {dados.get('observacao')}" if dados.get("observacao") else ""),
            condicao,
            unidade["id_equipamento"],
            id_usuario,
            id_empresa
        ))

        recalcular_quantidade(cursor2, unidade["id_equipamento"])

        conexao.commit()
        fechar(conexao, cursor2)
        return jsonify({
            "mensagem": f"Devolução da unidade {codigo} registrada!",
            "equipamento": unidade["equipamento_nome"]
        }), 201

    except Exception as e:
        conexao.rollback()
        fechar(conexao, cursor)
        return jsonify({"erro": str(e)}), 400


# ============================================================
# ROTA: DELETE /api/unidades/<id>
# ============================================================
@unidades_bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
def deletar(id):
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")

    if claims.get("perfil") != "admin":
        return jsonify({"erro": "Apenas administradores podem deletar unidades"}), 403

    conexao = conectar()
    cursor  = conexao.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT id_equipamento FROM unidades
            WHERE id = %s AND id_empresa = %s
        """, (id, id_empresa))
        unidade = cursor.fetchone()

        if not unidade:
            return jsonify({"erro": "Unidade não encontrada"}), 404

        cursor2 = conexao.cursor()
        cursor2.execute("DELETE FROM unidades WHERE id = %s", (id,))

        recalcular_quantidade(cursor2, unidade["id_equipamento"])

        conexao.commit()
        fechar(conexao, cursor2)
        return jsonify({"mensagem": "Unidade removida com sucesso!"}), 200

    except Exception as e:
        conexao.rollback()
        fechar(conexao, cursor)
        return jsonify({"erro": str(e)}), 400


# ============================================================
# ROTA: PUT /api/unidades/<id>/status
# Corrige manualmente o status de uma unidade específica
# ============================================================
@unidades_bp.route("/<int:id>/status", methods=["PUT"])
@jwt_required()
def alterar_status(id):
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")

    if claims.get("perfil") != "admin":
        return jsonify({"erro": "Apenas administradores podem corrigir o status"}), 403

    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return jsonify({"erro": "Corpo da requisição inválido"}), 400

    novo_status = dados.get("status")
    responsavel_informado = (dados.get("responsavel") or "").strip()

    if novo_status not in ("disponivel", "em_uso", "manutencao", "inativo"):
        return jsonify({"erro": "Status inválido"}), 400

    if novo_status == "em_uso" and not responsavel_informado:
        return jsonify({"erro": "Informe o responsável ao marcar como Em Uso"}), 400

    conexao = conectar()
    cursor  = conexao.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT * FROM unidades WHERE id = %s AND id_empresa = %s
        """, (id, id_empresa))
        unidade = cursor.fetchone()

        if not unidade:
            fechar(conexao, cursor)
            return jsonify({"erro": "Unidade não encontrada"}), 404

        cursor2 = conexao.cursor()

        # Só mantém "responsável atual" se o novo status for em_uso
        responsavel = responsavel_informado if novo_status == "em_uso" else None

        cursor2.execute("""
            UPDATE unidades SET status = %s, responsavel_atual = %s
            WHERE id = %s
        """, (novo_status, responsavel, id))

        recalcular_quantidade(cursor2, unidade["id_equipamento"])

        conexao.commit()
        fechar(conexao, cursor2)

        return jsonify({"mensagem": "Status corrigido com sucesso!"}), 200

    except Exception as e:
        conexao.rollback()
        fechar(conexao, cursor)
        return jsonify({"erro": str(e)}), 400
