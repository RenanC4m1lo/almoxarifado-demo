# ============================================================
# routes/equipamentos.py - Rotas de equipamentos com filtro por empresa
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from config import conectar, fechar
from routes.unidades import recalcular_quantidade

equipamentos_bp = Blueprint("equipamentos", __name__)


# ============================================================
# ROTA: GET /api/equipamentos
# ============================================================
@equipamentos_bp.route("/", methods=["GET"])
@jwt_required()
def listar():
    claims      = get_jwt()
    id_empresa  = claims.get("id_empresa")
    acesso_todas= claims.get("acesso_todas", 0)

    conexao = conectar()
    cursor  = conexao.cursor(dictionary=True)

    if acesso_todas:
        cursor.execute("""
            SELECT e.*, f.nome AS fornecedor_nome, emp.nome AS empresa_nome
            FROM equipamentos e
            LEFT JOIN fornecedores f ON e.id_fornecedor = f.id
            LEFT JOIN empresas emp ON e.id_empresa = emp.id
            WHERE e.id_empresa = %s
            ORDER BY e.nome ASC
        """, (id_empresa,))
    else:
        cursor.execute("""
            SELECT e.*, f.nome AS fornecedor_nome, emp.nome AS empresa_nome
            FROM equipamentos e
            LEFT JOIN fornecedores f ON e.id_fornecedor = f.id
            LEFT JOIN empresas emp ON e.id_empresa = emp.id
            WHERE e.id_empresa = %s
            ORDER BY e.nome ASC
        """, (id_empresa,))

    equipamentos = cursor.fetchall()
    fechar(conexao, cursor)
    return jsonify(equipamentos), 200


# ============================================================
# ROTA: GET /api/equipamentos/todas-empresas
# Junta equipamentos de todas as empresas - usada só pelo card
# "combinado" do Dashboard (Super Admin), pra mostrar quanto cada
# empresa tem de cada categoria. Mesma exceção já usada em
# movimentacoes.py: todo o resto do sistema continua isolado por
# empresa, mesmo pra quem tem acesso_todas.
# ============================================================
@equipamentos_bp.route("/todas-empresas", methods=["GET"])
@jwt_required()
def listar_todas_empresas():
    claims = get_jwt()

    if not claims.get("acesso_todas"):
        return jsonify({"erro": "Sem permissão"}), 403

    conexao = conectar()
    cursor  = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT e.*, emp.nome AS empresa_nome
        FROM equipamentos e
        LEFT JOIN empresas emp ON e.id_empresa = emp.id
        ORDER BY e.nome ASC
    """)

    equipamentos = cursor.fetchall()
    fechar(conexao, cursor)
    return jsonify(equipamentos), 200


# ============================================================
# ROTA: GET /api/equipamentos/<id>
# ============================================================
@equipamentos_bp.route("/<int:id>", methods=["GET"])
@jwt_required()
def buscar(id):
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")
    acesso_todas = claims.get("acesso_todas", 0)

    conexao = conectar()
    cursor  = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT e.*, f.nome AS fornecedor_nome
        FROM equipamentos e
        LEFT JOIN fornecedores f ON e.id_fornecedor = f.id
        WHERE e.id = %s
    """, (id,))
    equipamento = cursor.fetchone()
    fechar(conexao, cursor)

    if not equipamento:
        return jsonify({"erro": "Equipamento não encontrado"}), 404

    # Verifica se o usuário tem acesso a esse equipamento
    if not acesso_todas and equipamento["id_empresa"] != id_empresa:
        return jsonify({"erro": "Sem permissão para acessar esse equipamento"}), 403

    return jsonify(equipamento), 200


# ============================================================
# ROTA: GET /api/equipamentos/barras/<codigo>
# ============================================================
@equipamentos_bp.route("/barras/<codigo>", methods=["GET"])
@jwt_required()
def buscar_por_barras(codigo):
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")

    conexao = conectar()
    cursor  = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT e.*, f.nome AS fornecedor_nome
        FROM equipamentos e
        LEFT JOIN fornecedores f ON e.id_fornecedor = f.id
        WHERE e.codigo_barras = %s AND e.id_empresa = %s
    """, (codigo, id_empresa))
    equipamento = cursor.fetchone()
    fechar(conexao, cursor)

    if not equipamento:
        return jsonify({"erro": "Equipamento não encontrado"}), 404

    return jsonify(equipamento), 200


# ============================================================
# ROTA: POST /api/equipamentos
# ============================================================
@equipamentos_bp.route("/", methods=["POST"])
@jwt_required()
def cadastrar():
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")

    if claims.get("perfil") == "visitante":
        return jsonify({"erro": "Sem permissão"}), 403

    dados = request.get_json()

    if not dados.get("nome"):
        return jsonify({"erro": "Nome do equipamento é obrigatório"}), 400

    conexao = conectar()
    cursor  = conexao.cursor()

    try:
        cursor.execute("""
            INSERT INTO equipamentos
            (nome, descricao, numero_patrimonio, codigo_barras, quantidade,
             quantidade_minima, status, categoria, localizacao, id_fornecedor,
             id_empresa)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            dados.get("nome"),
            dados.get("descricao"),
            dados.get("numero_patrimonio"),
            dados.get("codigo_barras"),
            dados.get("quantidade", 0),
            dados.get("quantidade_minima", 5),
            dados.get("status", "disponivel"),
            dados.get("categoria"),
            dados.get("localizacao"),
            dados.get("id_fornecedor"),
            id_empresa # sempre a empresa do token, nunca a escolhida pelo cliente
        ))
        conexao.commit()
        novo_id = cursor.lastrowid
        fechar(conexao, cursor)
        return jsonify({
            "mensagem": "Equipamento cadastrado com sucesso!",
            "id": novo_id
        }), 201

    except Exception as e:
        conexao.rollback()
        fechar(conexao, cursor)
        return jsonify({"erro": str(e)}), 400


# ============================================================
# ROTA: PUT /api/equipamentos/<id>
# ============================================================
@equipamentos_bp.route("/<int:id>", methods=["PUT"])
@jwt_required()
def atualizar(id):
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")

    if claims.get("perfil") == "visitante":
        return jsonify({"erro": "Sem permissão"}), 403

    dados   = request.get_json()
    conexao = conectar()
    cursor  = conexao.cursor()

    try:
        cursor.execute("""
            UPDATE equipamentos SET
                nome = %s, descricao = %s, numero_patrimonio = %s,
                codigo_barras = %s, quantidade = %s, quantidade_minima = %s,
                status = %s, categoria = %s, localizacao = %s, id_fornecedor = %s
            WHERE id = %s AND id_empresa = %s
        """, (
            dados.get("nome"),
            dados.get("descricao"),
            dados.get("numero_patrimonio"),
            dados.get("codigo_barras"),
            dados.get("quantidade"),
            dados.get("quantidade_minima"),
            dados.get("status"),
            dados.get("categoria"),
            dados.get("localizacao"),
            dados.get("id_fornecedor"),
            id,
            id_empresa
        ))

        if cursor.rowcount == 0:
            fechar(conexao, cursor)
            return jsonify({"erro": "Equipamento não encontrado"}), 404

        # Verifica se precisa gerar alerta após atualização manual
        nova_qtd = dados.get("quantidade")
        qtd_minima = dados.get("quantidade_minima")

        if nova_qtd is not None and qtd_minima is not None:
            # Remove alertas antigos não lidos desse equipamento,
            # já que a quantidade mudou e precisa ser reavaliada
            cursor.execute("""
                DELETE FROM alertas
                WHERE id_equipamento = %s AND lido = 0
            """, (id,))

            if int(nova_qtd) <= int(qtd_minima):
                tipo_alerta = "sem_estoque" if int(nova_qtd) == 0 else "estoque_baixo"
                cursor.execute("""
                    INSERT INTO alertas (mensagem, tipo, id_equipamento, id_empresa)
                    VALUES (%s, %s, %s, %s)
                """, (
                    f"Estoque baixo: {dados.get('nome')} tem apenas {nova_qtd} unidade(s)",
                    tipo_alerta,
                    id,
                    id_empresa
                ))
                
        conexao.commit()
        fechar(conexao, cursor)
        return jsonify({"mensagem": "Equipamento atualizado com sucesso!"}), 200

    except Exception as e:
        conexao.rollback()
        fechar(conexao, cursor)
        print(f"ERRO AO ATUALIZAR EQUIPAMENTO: {str(e)}")
        return jsonify({"erro": str(e)}), 400


# ============================================================
# ROTA: DELETE /api/equipamentos/<id>
# ============================================================
@equipamentos_bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
def deletar(id):
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")

    if claims.get("perfil") != "admin":
        return jsonify({"erro": "Apenas administradores podem deletar"}), 403

    conexao = conectar()
    cursor  = conexao.cursor()

    try:
        cursor.execute("""
            DELETE FROM equipamentos WHERE id = %s AND id_empresa = %s
        """, (id, id_empresa))
        conexao.commit()
        fechar(conexao, cursor)
        return jsonify({"mensagem": "Equipamento removido com sucesso!"}), 200

    except Exception as e:
        conexao.rollback()
        fechar(conexao, cursor)
        return jsonify({"erro": str(e)}), 400


# ============================================================
# ROTA: PUT /api/equipamentos/manutencao-lote
# Marca vários equipamentos e/ou unidades específicas (código de
# barras) como "Em Manutenção" de uma vez - mesmo campo único (nome
# ou código de barras) usado em saída/devolução. Exige responsável e
# gera um registro de movimentação (tipo 'manutencao') por item, pra
# ficar rastreável no Histórico igual saída/devolução.
# ============================================================
@equipamentos_bp.route("/manutencao-lote", methods=["PUT"])
@jwt_required()
def manutencao_lote():
    claims     = get_jwt()
    id_empresa = claims.get("id_empresa")

    if claims.get("perfil") == "visitante":
        return jsonify({"erro": "Sem permissão"}), 403

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

    try:
        for i, item in enumerate(itens, start=1):
            tipo = item.get("tipo")

            if tipo == "unidade":
                codigo = item.get("codigo_barras")
                cursor.execute("""
                    SELECT * FROM unidades WHERE codigo_barras = %s AND id_empresa = %s
                """, (codigo, id_empresa))
                unidade = cursor.fetchone()

                if not unidade:
                    raise ValueError(f"Item {i}: unidade com código '{codigo}' não encontrada")

                cursor.execute("""
                    UPDATE unidades SET status = 'manutencao', responsavel_atual = NULL
                    WHERE id = %s
                """, (unidade["id"],))

                cursor.execute("""
                    INSERT INTO movimentacoes
                    (tipo, quantidade, responsavel, observacao, id_equipamento, id_usuario, id_empresa)
                    VALUES ('manutencao', 1, %s, %s, %s, %s, %s)
                """, (
                    responsavel,
                    f"Unidade: {codigo}" + (f" | {observacao_geral}" if observacao_geral else ""),
                    unidade["id_equipamento"], id_usuario, id_empresa
                ))

                recalcular_quantidade(cursor, unidade["id_equipamento"])

            elif tipo == "equipamento":
                id_equipamento = item.get("id_equipamento")
                cursor.execute("""
                    SELECT id, nome, quantidade FROM equipamentos
                    WHERE id = %s AND id_empresa = %s
                """, (id_equipamento, id_empresa))
                eq = cursor.fetchone()

                if not eq:
                    raise ValueError(f"Item {i}: equipamento não encontrado")

                cursor.execute("""
                    UPDATE equipamentos SET status = 'manutencao' WHERE id = %s
                """, (eq["id"],))

                cursor.execute("""
                    INSERT INTO movimentacoes
                    (tipo, quantidade, responsavel, observacao, id_equipamento, id_usuario, id_empresa)
                    VALUES ('manutencao', %s, %s, %s, %s, %s, %s)
                """, (
                    eq["quantidade"], responsavel, observacao_geral,
                    eq["id"], id_usuario, id_empresa
                ))
            else:
                raise ValueError(f"Item {i}: tipo inválido")

        conexao.commit()
        fechar(conexao, cursor)
        return jsonify({
            "mensagem": f"{len(itens)} item(ns) marcado(s) como Em Manutenção!"
        }), 200

    except Exception as e:
        conexao.rollback()
        fechar(conexao, cursor)
        return jsonify({"erro": str(e)}), 400