# ============================================================
# bootstrap_demo.py - Inicialização automática da demonstração
#
# No primeiro boot (banco vazio), cria as tabelas e popula com
# dados simulados. Em qualquer boot seguinte (ex: o app "acordando"
# depois de dormir no plano grátis do Render), a tabela já existe
# e esta função não faz nada - nunca apaga dados em uso.
# ============================================================
import os
import sys

import psycopg2


def _banco_ja_existe():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return True  # sem config de banco, não tenta mexer em nada

    conexao = psycopg2.connect(database_url)
    cursor = conexao.cursor()
    try:
        cursor.execute("SELECT 1 FROM empresas LIMIT 1")
        existe = True
    except psycopg2.errors.UndefinedTable:
        existe = False
    cursor.close()
    conexao.close()
    return existe


def inicializar_se_necessario():
    try:
        if _banco_ja_existe():
            return
    except Exception as e:
        print(f"[bootstrap_demo] Não foi possível checar o banco: {e}", file=sys.stderr)
        return

    print("[bootstrap_demo] Banco vazio detectado - criando tabelas e dados simulados...")

    raiz_projeto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    caminho_schema = os.path.join(raiz_projeto, "banco", "schema.sql")

    database_url = os.getenv("DATABASE_URL")
    conexao = psycopg2.connect(database_url)
    cursor = conexao.cursor()
    with open(caminho_schema, encoding="utf-8") as f:
        cursor.execute(f.read())
    conexao.commit()
    cursor.close()
    conexao.close()
    print("[bootstrap_demo] Tabelas criadas.")

    sys.path.insert(0, os.path.join(raiz_projeto, "banco"))
    import seed_demo
    seed_demo.seed()
    print("[bootstrap_demo] Dados simulados prontos.")
