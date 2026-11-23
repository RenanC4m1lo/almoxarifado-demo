# ============================================================
# routes/movimentacoes.py - Rotas de movimentações com filtro por empresa
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from datetime import datetime
from config import conectar, fechar
from routes.unidades import recalcular_quantidade

movimentacoes_bp = Blueprint("movimentacoes", __name__)


# ============================================================
# ROTA: GET /api/movimentacoes
# ============================================================
@movimentacoes_bp.route("/", methods=["GET"])
@jwt_required()
def listar():
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")

    conexao = conectar()
    cursor  = conexao.cursor(dictionary=True)

    # Mesmo para o Super Admin (acesso_todas), a lista reflete só a empresa
    # atualmente selecionada no topo — trocar de empresa é o mecanismo pra
    # ver os dados de cada uma, não uma visão global misturada (a tabela
    # nem mostra de qual empresa é cada linha).
    cursor.execute("""
        SELECT m.*, e.nome AS equipamento_nome,
               u.nome AS usuario_nome,
               emp.nome AS empresa_nome
        FROM movimentacoes m
        LEFT JOIN equipamentos e ON m.id_equipamento = e.id
        LEFT JOIN usuarios u ON m.id_usuario = u.id
        LEFT JOIN empresas emp ON m.id_empresa = emp.id
        WHERE m.id_empresa = %s
        ORDER BY m.criado_em DESC
    """, (id_empresa,))

    movimentacoes = cursor.fetchall()
    fechar(conexao, cursor)
    return jsonify(movimentacoes), 200


# ============================================================
# ROTA: GET /api/movimentacoes/todas-empresas
# Única rota que junta dados de mais de uma empresa - usada só pelo
# card "combinado" do Dashboard, visível apenas pra quem tem
# acesso_todas (Super Admin). Todo o resto do sistema continua
# estritamente isolado por empresa, mesmo pra Super Admin.
# ============================================================
@movimentacoes_bp.route("/todas-empresas", methods=["GET"])
@jwt_required()
def listar_todas_empresas():
    claims = get_jwt()

    if not claims.get("acesso_todas"):
        return jsonify({"erro": "Sem permissão"}), 403

    conexao = conectar()
    cursor  = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT m.*, e.nome AS equipamento_nome, emp.nome AS empresa_nome
        FROM movimentacoes m
        LEFT JOIN equipamentos e ON m.id_equipamento = e.id
        LEFT JOIN empresas emp ON m.id_empresa = emp.id
        ORDER BY m.criado_em DESC
    """)

    movimentacoes = cursor.fetchall()
    fechar(conexao, cursor)
    return jsonify(movimentacoes), 200


# ============================================================
# ROTA: POST /api/movimentacoes/saida
# ============================================================
@movimentacoes_bp.route("/saida", methods=["POST"])
@jwt_required()
def registrar_saida():
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")

    if claims.get("perfil") == "visitante":
        return jsonify({"erro": "Sem permissão para registrar saídas"}), 403

    dados = request.get_json()

    if not dados.get("id_equipamento") or not dados.get("responsavel"):
        return jsonify({"erro": "Equipamento e responsável são obrigatórios"}), 400

    quantidade = dados.get("quantidade", 1)

    conexao = conectar()
    cursor  = conexao.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT * FROM equipamentos
            WHERE id = %s AND id_empresa = %s
        """, (dados.get("id_equipamento"), id_empresa))
        equipamento = cursor.fetchone()

        if not equipamento:
            return jsonify({"erro": "Equipamento não encontrado"}), 404

        if equipamento["quantidade"] < quantidade:
            return jsonify({
                "erro": f"Estoque insuficiente. Disponível: {equipamento['quantidade']}"
            }), 400

        id_usuario    = get_jwt_identity()
        nova_quantidade = equipamento["quantidade"] - quantidade

        cursor2 = conexao.cursor()
        cursor2.execute("""
            INSERT INTO movimentacoes
            (tipo, quantidade, observacao, responsavel,
             data_devolucao_prevista, id_equipamento, id_usuario, id_empresa)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            "saida", quantidade,
            dados.get("observacao"),
            dados.get("responsavel"),
            dados.get("data_devolucao_prevista"),
            dados.get("id_equipamento"),
            id_usuario,
            id_empresa
        ))

        cursor2.execute("""
            UPDATE equipamentos SET quantidade = %s WHERE id = %s
        """, (nova_quantidade, dados.get("id_equipamento")))

        # Remove alertas antigos não lidos desse equipamento antes de reavaliar
        cursor2.execute("""
            DELETE FROM alertas
            WHERE id_equipamento = %s AND lido = 0
        """, (dados.get("id_equipamento"),))

        if nova_quantidade <= equipamento["quantidade_minima"]:
            tipo_alerta = "sem_estoque" if nova_quantidade == 0 else "estoque_baixo"
            cursor2.execute("""
                INSERT INTO alertas (mensagem, tipo, id_equipamento, id_empresa)
                VALUES (%s, %s, %s, %s)
            """, (
                f"Estoque baixo: {equipamento['nome']} tem apenas {nova_quantidade} unidade(s)",
                tipo_alerta,
                dados.get("id_equipamento"),
                id_empresa
            ))

        conexao.commit()
        fechar(conexao, cursor2)
        return jsonify({"mensagem": "Saída registrada com sucesso!"}), 201

    except Exception as e:
        conexao.rollback()
        fechar(conexao, cursor)
        return jsonify({"erro": str(e)}), 400


# ============================================================
# ROTA: POST /api/movimentacoes/devolucao
# ============================================================
@movimentacoes_bp.route("/devolucao", methods=["POST"])
@jwt_required()
def registrar_devolucao():
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")

    if claims.get("perfil") == "visitante":
        return jsonify({"erro": "Sem permissão para registrar devoluções"}), 403

    dados = request.get_json()

    if not dados.get("id_equipamento") or not dados.get("responsavel"):
        return jsonify({"erro": "Equipamento e responsável são obrigatórios"}), 400

    quantidade = dados.get("quantidade", 1)

    conexao = conectar()
    cursor  = conexao.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT * FROM equipamentos
            WHERE id = %s AND id_empresa = %s
        """, (dados.get("id_equipamento"), id_empresa))
        equipamento = cursor.fetchone()

        if not equipamento:
            return jsonify({"erro": "Equipamento não encontrado"}), 404

        id_usuario    = get_jwt_identity()
        nova_quantidade = equipamento["quantidade"] + quantidade

        cursor2 = conexao.cursor()
        cursor2.execute("""
            INSERT INTO movimentacoes
            (tipo, quantidade, observacao, responsavel,
             data_devolucao_real, id_equipamento, id_usuario, id_empresa)
            VALUES (%s, %s, %s, %s, NOW(), %s, %s, %s)
        """, (
            "devolucao", quantidade,
            dados.get("observacao"),
            dados.get("responsavel"),
            dados.get("id_equipamento"),
            id_usuario,
            id_empresa
        ))

        cursor2.execute("""
            UPDATE equipamentos SET quantidade = %s WHERE id = %s
        """, (nova_quantidade, dados.get("id_equipamento")))

        # Se o estoque voltou ao normal com a devolução, remove alertas pendentes
        if nova_quantidade > equipamento["quantidade_minima"]:
            cursor2.execute("""
                DELETE FROM alertas
                WHERE id_equipamento = %s AND lido = 0
            """, (dados.get("id_equipamento"),))

        conexao.commit()
        fechar(conexao, cursor2)
        return jsonify({"mensagem": "Devolução registrada com sucesso!"}), 201

    except Exception as e:
        conexao.rollback()
        fechar(conexao, cursor)
        return jsonify({"erro": str(e)}), 400


# ============================================================
# ROTA: GET /api/movimentacoes/resumo-mes?mes=X&ano=Y
# Conta as devoluções do mês por condição (boa/manutenção/perdido),
# usado no card "Resumo do Mês" do Dashboard.
# ============================================================
@movimentacoes_bp.route("/resumo-mes", methods=["GET"])
@jwt_required()
def resumo_mes():
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")

    mes = request.args.get("mes", type=int) or datetime.now().month
    ano = request.args.get("ano", type=int) or datetime.now().year

    conexao = conectar()
    cursor  = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT condicao, COUNT(*) AS total
        FROM movimentacoes
        WHERE id_empresa = %s AND tipo = 'devolucao'
          AND condicao IS NOT NULL
          AND EXTRACT(MONTH FROM criado_em) = %s AND EXTRACT(YEAR FROM criado_em) = %s
        GROUP BY condicao
    """, (id_empresa, mes, ano))

    contagens = {"boa": 0, "manutencao": 0, "inutilizavel": 0}
    for linha in cursor.fetchall():
        contagens[linha["condicao"]] = linha["total"]

    fechar(conexao, cursor)
    return jsonify({
        "mes": mes,
        "ano": ano,
        "disponiveis": contagens["boa"],
        "manutencao":  contagens["manutencao"],
        "perdidos":    contagens["inutilizavel"]
    }), 200


# ============================================================
# ROTA: POST /api/movimentacoes/saida-lote
# Registra saída de vários itens de uma vez (equipamentos por
# quantidade e/ou unidades por código de barras), tudo numa
# transação só - se um item falhar, nada é gravado.
# ============================================================
@movimentacoes_bp.route("/saida-lote", methods=["POST"])
@jwt_required()
def saida_lote():
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")

    if claims.get("perfil") == "visitante":
        return jsonify({"erro": "Sem permissão para registrar saídas"}), 403

    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return jsonify({"erro": "Corpo da requisição inválido"}), 400

    responsavel = dados.get("responsavel")
    itens       = dados.get("itens")

    if not responsavel:
        return jsonify({"erro": "Responsável é obrigatório"}), 400
    if not itens or not isinstance(itens, list):
        return jsonify({"erro": "Selecione ao menos um equipamento"}), 400

    observacao_geral        = dados.get("observacao")
    data_devolucao_prevista = dados.get("data_devolucao_prevista")
    id_usuario = get_jwt_identity()

    conexao = conectar()
    cursor  = conexao.cursor(dictionary=True)

    try:
        for i, item in enumerate(itens, start=1):
            tipo = item.get("tipo")

            if tipo == "unidade":
                codigo = item.get("codigo_barras")
                cursor.execute("""
                    SELECT u.* FROM unidades u
                    WHERE u.codigo_barras = %s AND u.id_empresa = %s
                """, (codigo, id_empresa))
                unidade = cursor.fetchone()

                if not unidade:
                    raise ValueError(f"Item {i}: unidade com código '{codigo}' não encontrada")
                if unidade["status"] != "disponivel":
                    raise ValueError(
                        f"Item {i}: unidade '{codigo}' não está disponível (status: {unidade['status']})"
                    )

                cursor.execute("""
                    UPDATE unidades SET status = 'em_uso', responsavel_atual = %s
                    WHERE id = %s
                """, (responsavel, unidade["id"]))

                cursor.execute("""
                    INSERT INTO movimentacoes
                    (tipo, quantidade, responsavel, observacao,
                     data_devolucao_prevista, id_equipamento, id_usuario, id_empresa)
                    VALUES ('saida', 1, %s, %s, %s, %s, %s, %s)
                """, (
                    responsavel,
                    f"Unidade: {codigo}" + (f" | {observacao_geral}" if observacao_geral else ""),
                    data_devolucao_prevista,
                    unidade["id_equipamento"],
                    id_usuario,
                    id_empresa
                ))

                recalcular_quantidade(cursor, unidade["id_equipamento"])

                cursor.execute("""
                    SELECT quantidade, quantidade_minima, nome FROM equipamentos WHERE id = %s
                """, (unidade["id_equipamento"],))
                eq_atual = cursor.fetchone()
                if eq_atual and eq_atual["quantidade"] <= eq_atual["quantidade_minima"]:
                    tipo_alerta = "sem_estoque" if eq_atual["quantidade"] == 0 else "estoque_baixo"
                    cursor.execute("""
                        INSERT INTO alertas (mensagem, tipo, id_equipamento, id_empresa)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        f"Estoque baixo: {eq_atual['nome']} tem apenas {eq_atual['quantidade']} unidade(s)",
                        tipo_alerta, unidade["id_equipamento"], id_empresa
                    ))

            elif tipo == "equipamento":
                id_equipamento = item.get("id_equipamento")
                quantidade     = item.get("quantidade", 1)

                cursor.execute("""
                    SELECT * FROM equipamentos WHERE id = %s AND id_empresa = %s
                """, (id_equipamento, id_empresa))
                equipamento = cursor.fetchone()

                if not equipamento:
                    raise ValueError(f"Item {i}: equipamento não encontrado")
                if equipamento["quantidade"] < quantidade:
                    raise ValueError(
                        f"Item {i}: estoque insuficiente de '{equipamento['nome']}' "
                        f"(disponível: {equipamento['quantidade']})"
                    )

                nova_quantidade = equipamento["quantidade"] - quantidade
                cursor.execute("""
                    UPDATE equipamentos SET quantidade = %s WHERE id = %s
                """, (nova_quantidade, id_equipamento))

                cursor.execute("""
                    INSERT INTO movimentacoes
                    (tipo, quantidade, responsavel, observacao,
                     data_devolucao_prevista, id_equipamento, id_usuario, id_empresa)
                    VALUES ('saida', %s, %s, %s, %s, %s, %s, %s)
                """, (
                    quantidade, responsavel, observacao_geral,
                    data_devolucao_prevista, id_equipamento, id_usuario, id_empresa
                ))

                cursor.execute("""
                    DELETE FROM alertas WHERE id_equipamento = %s AND lido = 0
                """, (id_equipamento,))

                if nova_quantidade <= equipamento["quantidade_minima"]:
                    tipo_alerta = "sem_estoque" if nova_quantidade == 0 else "estoque_baixo"
                    cursor.execute("""
                        INSERT INTO alertas (mensagem, tipo, id_equipamento, id_empresa)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        f"Estoque baixo: {equipamento['nome']} tem apenas {nova_quantidade} unidade(s)",
                        tipo_alerta, id_equipamento, id_empresa
                    ))
            else:
                raise ValueError(f"Item {i}: tipo inválido")

        conexao.commit()
        fechar(conexao, cursor)
        return jsonify({
            "mensagem": f"Saída registrada com sucesso! {len(itens)} item(ns) processado(s)."
        }), 201

    except Exception as e:
        conexao.rollback()
        fechar(conexao, cursor)
        return jsonify({"erro": str(e)}), 400


# ============================================================
# ROTA: POST /api/movimentacoes/devolucao-lote
# Mesma ideia da saída em lote, só que pro fluxo de devolução -
# itens tipo "unidade" aceitam condição (boa/manutenção/inutilizável).
# ============================================================
@movimentacoes_bp.route("/devolucao-lote", methods=["POST"])
@jwt_required()
def devolucao_lote():
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")

    if claims.get("perfil") == "visitante":
        return jsonify({"erro": "Sem permissão para registrar devoluções"}), 403

    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return jsonify({"erro": "Corpo da requisição inválido"}), 400

    responsavel = dados.get("responsavel")
    itens       = dados.get("itens")

    if not responsavel:
        return jsonify({"erro": "Responsável é obrigatório"}), 400
    if not itens or not isinstance(itens, list):
        return jsonify({"erro": "Selecione ao menos um equipamento"}), 400

    observacao_geral = dados.get("observacao")
    id_usuario = get_jwt_identity()

    conexao = conectar()
    cursor  = conexao.cursor(dictionary=True)

    status_por_condicao = {
        "boa": "disponivel",
        "manutencao": "manutencao",
        "inutilizavel": "inativo"
    }
    anotacao_condicao = {
        "manutencao": " (EM MANUTENÇÃO)",
        "inutilizavel": " (INUTILIZÁVEL/PERDIDO)"
    }

    try:
        for i, item in enumerate(itens, start=1):
            tipo = item.get("tipo")

            if tipo == "unidade":
                codigo   = item.get("codigo_barras")
                condicao = item.get("condicao", "boa")

                if condicao not in status_por_condicao:
                    raise ValueError(f"Item {i}: condição de devolução inválida")

                cursor.execute("""
                    SELECT u.* FROM unidades u
                    WHERE u.codigo_barras = %s AND u.id_empresa = %s
                """, (codigo, id_empresa))
                unidade = cursor.fetchone()

                if not unidade:
                    raise ValueError(f"Item {i}: unidade com código '{codigo}' não encontrada")

                cursor.execute("""
                    UPDATE unidades SET status = %s, responsavel_atual = NULL
                    WHERE id = %s
                """, (status_por_condicao[condicao], unidade["id"]))

                cursor.execute("""
                    INSERT INTO movimentacoes
                    (tipo, quantidade, responsavel, observacao, condicao,
                     data_devolucao_real, id_equipamento, id_usuario, id_empresa)
                    VALUES ('devolucao', 1, %s, %s, %s, NOW(), %s, %s, %s)
                """, (
                    responsavel,
                    f"Devolução: {codigo}" + anotacao_condicao.get(condicao, "")
                    + (f" | {observacao_geral}" if observacao_geral else ""),
                    condicao,
                    unidade["id_equipamento"],
                    id_usuario,
                    id_empresa
                ))

                recalcular_quantidade(cursor, unidade["id_equipamento"])

            elif tipo == "equipamento":
                id_equipamento = item.get("id_equipamento")
                quantidade     = item.get("quantidade", 1)

                cursor.execute("""
                    SELECT * FROM equipamentos WHERE id = %s AND id_empresa = %s
                """, (id_equipamento, id_empresa))
                equipamento = cursor.fetchone()

                if not equipamento:
                    raise ValueError(f"Item {i}: equipamento não encontrado")

                nova_quantidade = equipamento["quantidade"] + quantidade
                cursor.execute("""
                    UPDATE equipamentos SET quantidade = %s WHERE id = %s
                """, (nova_quantidade, id_equipamento))

                cursor.execute("""
                    INSERT INTO movimentacoes
                    (tipo, quantidade, responsavel, observacao,
                     data_devolucao_real, id_equipamento, id_usuario, id_empresa)
                    VALUES ('devolucao', %s, %s, %s, NOW(), %s, %s, %s)
                """, (
                    quantidade, responsavel, observacao_geral,
                    id_equipamento, id_usuario, id_empresa
                ))

                if nova_quantidade > equipamento["quantidade_minima"]:
                    cursor.execute("""
                        DELETE FROM alertas WHERE id_equipamento = %s AND lido = 0
                    """, (id_equipamento,))
            else:
                raise ValueError(f"Item {i}: tipo inválido")

        conexao.commit()
        fechar(conexao, cursor)
        return jsonify({
            "mensagem": f"Devolução registrada com sucesso! {len(itens)} item(ns) processado(s)."
        }), 201

    except Exception as e:
        conexao.rollback()
        fechar(conexao, cursor)
        return jsonify({"erro": str(e)}), 400