# ============================================================
# config.py - Configuração da conexão com o banco de dados
# Versão de demonstração: usa PostgreSQL (Render) em vez de
# MySQL. Esta camada de compatibilidade existe só pra não ter
# que reescrever cada rota que chama conexao.cursor(dictionary=True)
# e cursor.lastrowid (que não existem no driver do Postgres).
# ============================================================

import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()  # carrega as variáveis do arquivo .env


class _CursorCompat:
    """Cursor do psycopg2 com .lastrowid emulado via RETURNING id."""

    def __init__(self, cursor_real):
        self._cursor = cursor_real
        self.lastrowid = None

    def execute(self, query, params=None):
        query_ajustada = query
        query_sem_espaco = query.strip().upper()
        if query_sem_espaco.startswith("INSERT") and "RETURNING" not in query_sem_espaco:
            query_ajustada = query.rstrip().rstrip(";") + " RETURNING id"

        self._cursor.execute(query_ajustada, params)

        if query_ajustada is not query:
            linha = self._cursor.fetchone()
            if linha:
                self.lastrowid = linha["id"] if isinstance(linha, dict) else linha[0]

    def __getattr__(self, nome):
        return getattr(self._cursor, nome)

    def __iter__(self):
        return iter(self._cursor)


class _ConexaoCompat:
    """Conexão psycopg2 com a mesma interface usada nas rotas (estilo mysql.connector)."""

    def __init__(self, conexao_real):
        self._conexao = conexao_real

    def cursor(self, dictionary=False):
        if dictionary:
            cursor_real = self._conexao.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            cursor_real = self._conexao.cursor()
        return _CursorCompat(cursor_real)

    def commit(self):
        self._conexao.commit()

    def rollback(self):
        self._conexao.rollback()

    def close(self):
        self._conexao.close()


def conectar():
    """
    Função que cria e retorna uma conexão com o banco de dados.
    Sempre que precisarmos acessar o banco, chamamos essa função.
    """
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        conexao_real = psycopg2.connect(database_url)
    else:
        conexao_real = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            dbname=os.getenv("DB_NAME"),
            port=os.getenv("DB_PORT", "5432"),
        )
    return _ConexaoCompat(conexao_real)


def fechar(conexao, cursor):
    """
    Função que fecha a conexão com o banco após o uso.
    Importante para não deixar conexões abertas desnecessariamente.
    """
    cursor.close()
    conexao.close()
