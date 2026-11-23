# ============================================================
# routes/relatorios.py - Rotas de relatórios em PDF
# Gera relatórios do estoque usando a biblioteca ReportLab
# ============================================================

from flask import Blueprint, make_response, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from reportlab.lib.pagesizes import A4          # tamanho da página A4
from reportlab.lib import colors                # cores para o PDF
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet  # estilos de texto
from reportlab.lib.units import cm              # unidade de medida em centímetros
from reportlab.lib.utils import ImageReader     # para descobrir o tamanho das imagens dos gráficos
import io                                       # para criar o PDF em memória
import base64                                   # para decodificar as imagens dos gráficos (enviadas pelo navegador)
from datetime import datetime                   # para colocar a data no relatório
from xml.sax.saxutils import escape             # escapa texto antes de colocar num Paragraph (ReportLab lê como XML)
from config import conectar, fechar

relatorios_bp = Blueprint("relatorios", __name__)


# ============================================================
# ROTA: GET /api/relatorios/estoque
# Gera um PDF com todos os equipamentos do estoque
# ============================================================
@relatorios_bp.route("/estoque", methods=["GET"])
@jwt_required()
def relatorio_estoque():
    claims = get_jwt()
    id_empresa = claims.get("id_empresa")

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    # Busca só os equipamentos da empresa do usuário logado
    cursor.execute("""
        SELECT e.nome, e.categoria, e.quantidade,
               e.quantidade_minima, e.status, e.localizacao,
               f.nome AS fornecedor
        FROM equipamentos e
        LEFT JOIN fornecedores f ON e.id_fornecedor = f.id
        WHERE e.id_empresa = %s
        ORDER BY e.categoria, e.nome
    """, (id_empresa,))
    equipamentos = cursor.fetchall()
    fechar(conexao, cursor)

    # Cria o PDF em memória (sem salvar no disco)
    buffer = io.BytesIO()

    # Configura o documento PDF
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,            # tamanho A4
        rightMargin=2*cm,       # margem direita
        leftMargin=2*cm,        # margem esquerda
        topMargin=2*cm,         # margem superior
        bottomMargin=2*cm       # margem inferior
    )

    # Lista de elementos que vão aparecer no PDF
    elementos = []
    estilos = getSampleStyleSheet()

    # Título do relatório
    titulo = Paragraph(
        "<b>Relatório de Estoque - Sistema Almoxarifado</b>",
        estilos["Title"]
    )
    elementos.append(titulo)

    # Data de geração do relatório
    data_geracao = Paragraph(
        f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
        estilos["Normal"]
    )
    elementos.append(data_geracao)

    # Espaço entre o título e a tabela
    elementos.append(Spacer(1, 0.5*cm))

    # Cabeçalho da tabela
    cabecalho = ["Nome", "Categoria", "Qtd", "Qtd Mín", "Status", "Localização", "Fornecedor"]

    # Dados da tabela: começa com o cabeçalho
    dados_tabela = [cabecalho]

    # Adiciona cada equipamento como uma linha da tabela
    for eq in equipamentos:
        dados_tabela.append([
            eq["nome"] or "",
            eq["categoria"] or "",
            str(eq["quantidade"]),
            str(eq["quantidade_minima"]),
            eq["status"] or "",
            eq["localizacao"] or "",
            eq["fornecedor"] or ""
        ])

    # Cria a tabela com os dados
    tabela = Table(dados_tabela, repeatRows=1)
    # repeatRows=1 = repete o cabeçalho em todas as páginas

    # Estilo visual da tabela
    tabela.setStyle(TableStyle([
        # Cabeçalho: fundo azul escuro, texto branco e negrito
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),

        # Linhas alternadas: branco e azul claro
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#e8f0fe")]),

        # Borda em todas as células
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),

        # Padding interno das células
        ("PADDING", (0, 0), (-1, -1), 6),

        # Alinhamento do texto nas células
        ("ALIGN", (2, 1), (3, -1), "CENTER"),  # centraliza quantidade
        ("FONTSIZE", (0, 1), (-1, -1), 8),     # tamanho da fonte nas linhas
    ]))

    elementos.append(tabela)

    # Gera o PDF com todos os elementos
    doc.build(elementos)

    # Pega o conteúdo do PDF gerado em memória
    pdf = buffer.getvalue()
    buffer.close()

    # Cria a resposta HTTP com o PDF
    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    # Content-Disposition: força o download do arquivo
    response.headers["Content-Disposition"] = "attachment; filename=relatorio_estoque.pdf"

    return response


# ============================================================
# ROTA: GET /api/relatorios/movimentacoes
# Gera um PDF com o histórico de movimentações
# ============================================================
@relatorios_bp.route("/movimentacoes", methods=["GET"])
@jwt_required()
def relatorio_movimentacoes():
    claims = get_jwt()
    id_empresa = claims.get("id_empresa")

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT m.tipo, m.quantidade, m.responsavel,
               m.observacao, m.criado_em,
               e.nome AS equipamento
        FROM movimentacoes m
        LEFT JOIN equipamentos e ON m.id_equipamento = e.id
        WHERE m.id_empresa = %s
        ORDER BY m.criado_em DESC
        LIMIT 100
    """, (id_empresa,))
    # LIMIT 100 = máximo de 100 registros no relatório
    movimentacoes = cursor.fetchall()
    fechar(conexao, cursor)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                           rightMargin=2*cm, leftMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)
    elementos = []
    estilos = getSampleStyleSheet()

    titulo = Paragraph("<b>Relatório de Movimentações</b>", estilos["Title"])
    elementos.append(titulo)

    data_geracao = Paragraph(
        f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
        estilos["Normal"]
    )
    elementos.append(data_geracao)
    elementos.append(Spacer(1, 0.5*cm))

    cabecalho = ["Tipo", "Equipamento", "Quantidade", "Responsável", "Data"]
    dados_tabela = [cabecalho]

    for mov in movimentacoes:
        # Formata a data para exibição
        data = mov["criado_em"].strftime("%d/%m/%Y %H:%M") if mov["criado_em"] else ""
        dados_tabela.append([
            mov["tipo"].upper(),
            mov["equipamento"] or "",
            str(mov["quantidade"]),
            mov["responsavel"] or "",
            data
        ])

    tabela = Table(dados_tabela, repeatRows=1)
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#e8f0fe")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
    ]))

    elementos.append(tabela)
    doc.build(elementos)

    pdf = buffer.getvalue()
    buffer.close()

    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "attachment; filename=relatorio_movimentacoes.pdf"

    return response

# ============================================================
# ROTA: GET /api/relatorios/tecnicos
# Gera um PDF com os materiais usados por técnico no mês
# Parâmetros opcionais: ?mes=8&ano=2026&responsavel=Nome
# ============================================================
@relatorios_bp.route("/tecnicos", methods=["GET"])
@jwt_required()
def relatorio_tecnicos():
    claims = get_jwt()
    id_empresa = claims.get("id_empresa")

    mes = request.args.get("mes", type=int) or datetime.now().month
    ano = request.args.get("ano", type=int) or datetime.now().year
    responsavel = request.args.get("responsavel")  # opcional, vazio = todos
    if responsavel:
        responsavel = responsavel.strip()

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    # TRIM no responsavel evita que "DIEGO" e "DIEGO " (espaço a mais
    # digitado/lido por engano) virem dois técnicos diferentes no relatório.
    if responsavel:
        cursor.execute("""
            SELECT TRIM(m.responsavel) AS responsavel, e.nome AS equipamento, SUM(m.quantidade) AS total
            FROM movimentacoes m
            LEFT JOIN equipamentos e ON m.id_equipamento = e.id
            WHERE m.id_empresa = %s AND m.tipo = 'saida'
              AND EXTRACT(MONTH FROM m.criado_em) = %s AND EXTRACT(YEAR FROM m.criado_em) = %s
              AND TRIM(m.responsavel) = %s
            GROUP BY TRIM(m.responsavel), e.nome
            ORDER BY e.nome
        """, (id_empresa, mes, ano, responsavel))
    else:
        cursor.execute("""
            SELECT TRIM(m.responsavel) AS responsavel, e.nome AS equipamento, SUM(m.quantidade) AS total
            FROM movimentacoes m
            LEFT JOIN equipamentos e ON m.id_equipamento = e.id
            WHERE m.id_empresa = %s AND m.tipo = 'saida'
              AND EXTRACT(MONTH FROM m.criado_em) = %s AND EXTRACT(YEAR FROM m.criado_em) = %s
            GROUP BY TRIM(m.responsavel), e.nome
            ORDER BY TRIM(m.responsavel), e.nome
        """, (id_empresa, mes, ano))

    linhas = cursor.fetchall()
    fechar(conexao, cursor)

    # Agrupa os resultados por técnico
    tecnicos = {}
    for l in linhas:
        nome_tec = l["responsavel"] or "Não informado"
        tecnicos.setdefault(nome_tec, []).append(l)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                           rightMargin=2*cm, leftMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)
    elementos = []
    estilos = getSampleStyleSheet()

    meses_nomes = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                   "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

    titulo_texto = "Relatório de Materiais por Técnico"
    if responsavel:
        titulo_texto += f" — {responsavel}"

    elementos.append(Paragraph(f"<b>{titulo_texto}</b>", estilos["Title"]))
    elementos.append(Paragraph(f"Referente a: {meses_nomes[mes]} de {ano}", estilos["Normal"]))
    elementos.append(Paragraph(
        f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
        estilos["Normal"]
    ))
    elementos.append(Spacer(1, 0.5*cm))

    if not tecnicos:
        elementos.append(Paragraph("Nenhuma saída registrada nesse período.", estilos["Normal"]))
    else:
        for nome_tec in sorted(tecnicos.keys()):
            elementos.append(Paragraph(f"<b>👤 {nome_tec}</b>", estilos["Heading2"]))

            cabecalho = ["Material", "Quantidade Total"]
            dados_tabela = [cabecalho]
            total_geral = 0
            for item in tecnicos[nome_tec]:
                dados_tabela.append([item["equipamento"] or "-", str(item["total"])])
                total_geral += item["total"]

            tabela = Table(dados_tabela, repeatRows=1, colWidths=[10*cm, 4*cm])
            tabela.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#e8f0fe")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("ALIGN", (1, 1), (1, -1), "CENTER"),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
            ]))
            elementos.append(tabela)
            elementos.append(Paragraph(
                f"<b>Total de itens retirados: {total_geral}</b>", estilos["Normal"]
            ))
            elementos.append(Spacer(1, 0.7*cm))

    doc.build(elementos)
    pdf = buffer.getvalue()
    buffer.close()

    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    nome_arquivo = f"tecnico_{responsavel}" if responsavel else "todos_tecnicos"
    response.headers["Content-Disposition"] = f"attachment; filename=relatorio_{nome_arquivo}_{mes}_{ano}.pdf"

    return response


# ============================================================
# ROTA: POST /api/relatorios/dashboard
# Gera um PDF com os gráficos do Dashboard.
# Os gráficos são desenhados no navegador (Chart.js) e chegam aqui
# já como imagens PNG em base64 — essa rota só monta o PDF com elas.
# ============================================================
@relatorios_bp.route("/dashboard", methods=["POST"])
@jwt_required()
def relatorio_dashboard():
    claims = get_jwt()
    dados  = request.get_json() or {}

    graficos            = dados.get("graficos", {})
    resumo              = dados.get("resumo", {})
    filtro_equipamento  = dados.get("filtro_equipamento")

    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
        elementos = []
        estilos = getSampleStyleSheet()

        elementos.append(Paragraph("<b>Relatório do Dashboard - Sistema Almoxarifado</b>", estilos["Title"]))
        elementos.append(Paragraph(f"Empresa: {escape(claims.get('empresa_nome', ''))}", estilos["Normal"]))
        if filtro_equipamento:
            elementos.append(Paragraph(f"Filtro aplicado: {escape(filtro_equipamento)}", estilos["Normal"]))
        elementos.append(Paragraph(
            f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
            estilos["Normal"]
        ))
        elementos.append(Spacer(1, 0.5*cm))

        # Resumo dos totais mostrados nos cards do Dashboard
        if resumo:
            dados_resumo = [
                ["Total de Equipamentos", "Disponíveis", "Em Uso", "Em Manutenção", "Perdidos"],
                [
                    str(resumo.get("total_equipamentos", "-")),
                    str(resumo.get("disponiveis", "-")),
                    str(resumo.get("em_uso", "-")),
                    str(resumo.get("manutencao", "-")),
                    str(resumo.get("perdidos", "-")),
                ]
            ]
            tabela_resumo = Table(dados_resumo, colWidths=[3.4*cm]*5)
            tabela_resumo.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("PADDING", (0, 0), (-1, -1), 8),
            ]))
            elementos.append(tabela_resumo)
            elementos.append(Spacer(1, 0.7*cm))

        # Cada gráfico chega como PNG em base64; a ordem aqui define a ordem no PDF
        titulos_graficos = [
            ("status",         "Status dos Equipamentos"),
            ("movimentacoes",  "Movimentações (7 dias)"),
            ("categorias",     "Equipamentos por Categoria"),
        ]

        largura_util = A4[0] - 4*cm  # descontando as margens esquerda/direita

        for chave, titulo in titulos_graficos:
            imagem_base64 = graficos.get(chave)
            if not imagem_base64:
                continue

            if "," in imagem_base64:
                imagem_base64 = imagem_base64.split(",", 1)[1]

            imagem_bytes = base64.b64decode(imagem_base64)

            # Descobre a proporção da imagem pra não distorcer o gráfico no PDF
            leitor = ImageReader(io.BytesIO(imagem_bytes))
            largura_original, altura_original = leitor.getSize()
            if not largura_original:
                continue
            altura_proporcional = largura_util * (altura_original / largura_original)

            elementos.append(Paragraph(f"<b>{titulo}</b>", estilos["Heading2"]))
            elementos.append(Image(io.BytesIO(imagem_bytes), width=largura_util, height=altura_proporcional))
            elementos.append(Spacer(1, 0.6*cm))

        doc.build(elementos)
        pdf = buffer.getvalue()
        buffer.close()

        response = make_response(pdf)
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = "attachment; filename=relatorio_dashboard.pdf"

        return response

    except Exception as e:
        return jsonify({"erro": f"Erro ao gerar o PDF do dashboard: {e}"}), 400