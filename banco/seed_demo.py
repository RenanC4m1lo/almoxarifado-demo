# -*- coding: utf-8 -*-
"""
Popula o banco da versao de demonstracao com dados simulados.
Roda uma unica vez, logo apos aplicar o schema.sql num banco vazio.

Uso: python seed_demo.py
(precisa de DATABASE_URL configurada - ou DB_HOST/DB_USER/DB_PASSWORD/DB_NAME/DB_PORT)
"""
import sys
import os
import random
import bcrypt
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from config import conectar  # noqa: E402

random.seed(42)


def hash_senha(senha):
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


SENHA_DEMO = "demo123"

EMPRESAS = [
    (1, "Matriz", "Cidade A"),
    (2, "Filial", "Cidade B"),
]

USUARIOS = [
    ("Super Admin",      "superadmin@demo.com",       "admin",     1, 1),
    ("Admin Matriz",     "admin.matriz@demo.com",      "admin",     1, 0),
    ("Admin Filial",     "admin.filial@demo.com",      "admin",     2, 0),
    ("Operador Matriz",  "operador.matriz@demo.com",   "operador",  1, 0),
    ("Operador Filial",  "operador.filial@demo.com",   "operador",  2, 0),
    ("Visitante Matriz", "visitante.matriz@demo.com",  "visitante", 1, 0),
    ("Visitante Filial", "visitante.filial@demo.com",  "visitante", 2, 0),
]

FORNECEDORES_NOMES = [
    ("Fibratec Distribuidora", "11.222.333/0001-44", "Carlos Mendes", "(11) 4002-8922", "contato@fibratec.com.br"),
    ("Conecta Equipamentos",   "22.333.444/0001-55", "Patrícia Lima",  "(15) 3222-1144", "vendas@conectaequip.com.br"),
    ("NetSupply Telecom",      "33.444.555/0001-66", "Roberto Alves",  "(15) 3233-5566", "comercial@netsupply.com.br"),
]

CATEGORIAS_EQUIPAMENTOS = {
    "ONU":              ["ONU Fiberhome AN5506", "ONU Huawei HG8245", "ONU ZTE F660", "ONU Nokia G-140W", "ONU Intelbras ONU110"],
    "Roteador":         ["Roteador TP-Link Archer C6", "Roteador Intelbras Action RF 1200", "Roteador Mikrotik hAP ac2"],
    "Switch":           ["Switch 8 portas Gigabit", "Switch 16 portas PoE", "Switch 24 portas Gerenciável"],
    "Cabo de Rede":     ["Cabo Drop Óptico 1FO", "Cabo UTP Cat6 (caixa 305m)", "Cabo Flat Drop 2FO"],
    "Conector":         ["Conector Óptico SC/APC", "Conector RJ45 Cat6", "Splitter Óptico 1x8"],
    "Ferramenta":       ["Fusionadora de Fibra", "Alicate de Crimpar", "Power Meter Óptico", "Lançadeira de Fibra"],
    "EPI":              ["Cinto de Segurança", "Capacete com Jugular", "Luva Isolante"],
}

NOMES_TECNICOS = [
    "Jonas Pereira", "Marcos Vinícius", "Felipe Souza", "André Luiz", "Diego Fernandes",
    "Lucas Martins", "Rafael Costa", "Bruno Oliveira", "Thiago Ramos", "Gustavo Henrique",
]

RESPONSAVEIS_MOV = NOMES_TECNICOS

STATUS_UNIDADE_PESOS = [("disponivel", 65), ("em_uso", 25), ("manutencao", 7), ("inativo", 3)]


def status_aleatorio():
    r = random.uniform(0, 100)
    acumulado = 0
    for status, peso in STATUS_UNIDADE_PESOS:
        acumulado += peso
        if r <= acumulado:
            return status
    return "disponivel"


def seed():
    conexao = conectar()
    cursor = conexao.cursor()

    print("Limpando tabelas...")
    cursor.execute(
        """TRUNCATE TABLE alertas, movimentacoes, unidades, usuarios,
           tecnicos, equipamentos, fornecedores, empresas
           RESTART IDENTITY CASCADE"""
    )

    print("Empresas...")
    for id_empresa, nome, cidade in EMPRESAS:
        cursor.execute(
            "INSERT INTO empresas (id, nome, cidade, ativo) VALUES (%s, %s, %s, 1)",
            (id_empresa, nome, cidade)
        )

    print("Usuários de demonstração...")
    for nome, email, perfil, id_empresa, acesso_todas in USUARIOS:
        cursor.execute(
            """INSERT INTO usuarios (nome, email, senha, perfil, id_empresa, acesso_todas, ativo)
               VALUES (%s, %s, %s, %s, %s, %s, 1)""",
            (nome, email, hash_senha(SENHA_DEMO), perfil, id_empresa, acesso_todas)
        )

    ids_fornecedores = {1: [], 2: []}
    print("Fornecedores...")
    for id_empresa in (1, 2):
        for nome, cnpj, contato, telefone, email in FORNECEDORES_NOMES:
            cnpj_empresa = cnpj.replace("0001", f"000{id_empresa}")
            cursor.execute(
                """INSERT INTO fornecedores (nome, cnpj, contato, telefone, email, ativo, id_empresa)
                   VALUES (%s, %s, %s, %s, %s, 1, %s)""",
                (nome, cnpj_empresa, contato, telefone, email, id_empresa)
            )
            ids_fornecedores[id_empresa].append(cursor.lastrowid)

    print("Técnicos...")
    ids_tecnicos = {1: [], 2: []}
    for id_empresa in (1, 2):
        qtd = random.randint(5, 7)
        for nome in random.sample(NOMES_TECNICOS, qtd):
            telefone = f"(15) 9{random.randint(6000,9999)}-{random.randint(1000,9999)}"
            cursor.execute(
                "INSERT INTO tecnicos (nome, telefone, ativo, id_empresa) VALUES (%s, %s, 1, %s)",
                (nome, telefone, id_empresa)
            )
            ids_tecnicos[id_empresa].append(cursor.lastrowid)

    print("Equipamentos e unidades...")
    ids_equipamentos = {1: [], 2: []}
    SERIALIZADOS = {"ONU", "Roteador", "Switch"}

    for id_empresa in (1, 2):
        for categoria, nomes in CATEGORIAS_EQUIPAMENTOS.items():
            for nome in nomes:
                serializado = categoria in SERIALIZADOS
                qtd_inicial = 0 if serializado else random.randint(10, 80)
                qtd_minima = random.randint(3, 10)
                fornecedor = random.choice(ids_fornecedores[id_empresa])
                codigo_barras = f"EMP{id_empresa}{random.randint(100000,999999)}"

                cursor.execute(
                    """INSERT INTO equipamentos
                       (nome, descricao, codigo_barras, quantidade, quantidade_minima,
                        status, categoria, localizacao, id_fornecedor, id_empresa)
                       VALUES (%s, %s, %s, %s, %s, 'disponivel', %s, %s, %s, %s)""",
                    (nome, f"{nome} - uso em instalações e manutenções de rede",
                     codigo_barras, qtd_inicial, qtd_minima, categoria,
                     f"Almoxarifado {EMPRESAS[id_empresa-1][2]}", fornecedor, id_empresa)
                )
                id_eq = cursor.lastrowid
                ids_equipamentos[id_empresa].append((id_eq, nome, categoria, serializado))

                if serializado:
                    qtd_unidades = random.randint(12, 30)
                    disponiveis = 0
                    for i in range(qtd_unidades):
                        status = status_aleatorio()
                        if status == "disponivel":
                            disponiveis += 1
                        barra_unidade = f"{codigo_barras}-{i+1:03d}"
                        serie = f"SN{random.randint(10**9, 10**10-1)}"
                        cursor.execute(
                            """INSERT INTO unidades
                               (id_equipamento, id_empresa, codigo_barras, numero_serie, status)
                               VALUES (%s, %s, %s, %s, %s)""",
                            (id_eq, id_empresa, barra_unidade, serie, status)
                        )
                    cursor.execute(
                        "UPDATE equipamentos SET quantidade = %s WHERE id = %s",
                        (disponiveis, id_eq)
                    )

    print("Movimentações (últimos 10 dias)...")
    HOJE = datetime.now()
    for id_empresa in (1, 2):
        equipamentos_qtd = [e for e in ids_equipamentos[id_empresa] if not e[3]]
        for dia_offset in range(10, -1, -1):
            data_mov = HOJE - timedelta(days=dia_offset, hours=random.randint(0, 8))
            qtd_mov_dia = random.randint(2, 6)
            for _ in range(qtd_mov_dia):
                id_eq, nome_eq, categoria, _ = random.choice(equipamentos_qtd)
                tipo = random.choices(["saida", "devolucao", "manutencao"], weights=[55, 35, 10])[0]
                quantidade = random.randint(1, 5)
                responsavel = random.choice(RESPONSAVEIS_MOV)
                condicao = "boa" if tipo == "devolucao" else None

                cursor.execute(
                    """INSERT INTO movimentacoes
                       (tipo, quantidade, observacao, condicao, responsavel,
                        id_equipamento, id_empresa, criado_em)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (tipo, quantidade, f"Movimentação simulada - {nome_eq}", condicao,
                     responsavel, id_eq, id_empresa, data_mov)
                )

    print("Alertas de estoque baixo...")
    for id_empresa in (1, 2):
        cursor.execute(
            """SELECT id, nome, quantidade, quantidade_minima FROM equipamentos
               WHERE id_empresa = %s AND quantidade <= quantidade_minima""",
            (id_empresa,)
        )
        for id_eq, nome_eq, qtd, qtd_min in cursor.fetchall():
            tipo_alerta = "sem_estoque" if qtd == 0 else "estoque_baixo"
            cursor.execute(
                """INSERT INTO alertas (mensagem, tipo, id_equipamento, id_empresa)
                   VALUES (%s, %s, %s, %s)""",
                (f"Estoque baixo: {nome_eq} tem apenas {qtd} unidade(s)", tipo_alerta, id_eq, id_empresa)
            )

    conexao.commit()
    cursor.close()
    conexao.close()
    print("\nConcluído! Dados simulados prontos.")
    print(f"Senha de todas as contas de demonstração: {SENHA_DEMO}")
    for _, email, perfil, id_empresa, acesso_todas in USUARIOS:
        print(f"  - {email}  ({'Super Admin' if acesso_todas else perfil})")


if __name__ == "__main__":
    seed()
