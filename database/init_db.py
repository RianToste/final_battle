"""
Cria a base de dados: executa o schema (tabelas), o seed (dados iniciais)
e cria a conta de administrador.

Pode ser executado várias vezes sem problemas:
  - o schema usa "CREATE TABLE IF NOT EXISTS";
  - o seed (itens, adversários e missões de exemplo) só corre na PRIMEIRA
    criação da base de dados. Assim, se o administrador apagar um objeto,
    ele não "ressuscita" no arranque seguinte.
"""

import os

import config
from database.connection import get_connection
from utils.exceptions import ConfigurationError
from utils.security import hash_password

# Pasta onde estão os ficheiros .sql (a mesma deste ficheiro Python)
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _run_sql_file(connection, filename):
    """Lê um ficheiro .sql da pasta database/ e executa-o por inteiro."""
    path = os.path.join(_BASE_DIR, filename)
    with open(path, encoding="utf-8") as sql_file:
        connection.executescript(sql_file.read())


def _database_is_new(connection):
    """
    Devolve True se a base de dados ainda não tem tabelas.
    O SQLite guarda a lista de tabelas numa tabela especial: sqlite_master.
    """
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'users'"
    ).fetchone()
    return row is None


def _create_admin_if_missing(connection):
    """
    Cria o administrador (credenciais vindas do config/.env) se ainda
    não existir.
    """
    existing = connection.execute(
        "SELECT id FROM users WHERE username = ?",
        (config.ADMIN_USERNAME,),
    ).fetchone()

    if existing is not None:
        return

    # Sem password definida não criamos a conta (seria um risco de segurança).
    if not config.ADMIN_PASSWORD:
        raise ConfigurationError(
            "Falta a password do administrador. Copie o ficheiro .env.example "
            "para .env e defina ADMIN_PASSWORD."
        )

    password_hash, password_salt = hash_password(config.ADMIN_PASSWORD)
    connection.execute(
        "INSERT INTO users (username, password_hash, password_salt, role) "
        "VALUES (?, ?, ?, ?)",
        (config.ADMIN_USERNAME, password_hash, password_salt, config.ROLE_ADMIN),
    )


def init_database(db_path=None):
    """
    Prepara a base de dados completa.

    - db_path: caminho da BD (os testes passam uma BD temporária).
    """
    connection = get_connection(db_path)
    try:
        is_new = _database_is_new(connection)

        _run_sql_file(connection, "schema.sql")       # 1. tabelas
        if is_new:
            _run_sql_file(connection, "seed.sql")     # 2. dados iniciais
        _create_admin_if_missing(connection)          # 3. conta admin
        connection.commit()
    finally:
        connection.close()
