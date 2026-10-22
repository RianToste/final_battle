"""
Gere a ligação à base de dados SQLite.

Este módulo só abre/fecha ligações e controla transações.
NÃO contém regras de jogo nem consultas SQL.
"""

import sqlite3
from contextlib import contextmanager

import config


def get_connection(db_path=None):
    """
    Abre uma ligação à base de dados e devolve-a.

    - db_path: caminho da BD. Se não for indicado, usa o de config.py.
      (Os testes passam aqui uma BD temporária para não mexer na real.)
    """
    # Lemos config.DATABASE_PATH no momento da chamada (e não ao importar),
    # para que os testes consigam alterar o valor.
    path = db_path or config.DATABASE_PATH

    connection = sqlite3.connect(path)

    # Row permite aceder às colunas pelo nome: linha["username"]
    connection.row_factory = sqlite3.Row

    # O SQLite NÃO verifica chaves estrangeiras por defeito: ativamos aqui.
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


@contextmanager
def transaction(db_path=None):
    """
    Se tudo correr bem -> COMMIT (guarda tudo).
    Se der qualquer erro -> ROLLBACK (desfaz tudo) e o erro continua a subir.

    Numa compra, nunca se desconta o dinheiro sem entregar o item.
    """
    connection = get_connection(db_path)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()