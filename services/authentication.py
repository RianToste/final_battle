"""
Autenticação e gestão de contas: registo, login, logout, alteração de
dados e verificação de permissões.
"""

import sqlite3

from database import queries
from database.connection import transaction
from models.user import User
from services import history
from utils.exceptions import (
    AuthenticationError,
    DuplicateUserError,
    PermissionDeniedError,
    UserBlockedError,
)
from utils.security import hash_password, verify_password
from utils.validators import validate_password, validate_username

import config


def register_user(username, password):
    """
    Cria uma conta de jogador nova e devolve o User criado.

    Levanta ValidationError (dados inválidos) ou DuplicateUserError
    (username já existe).
    """
    username = validate_username(username)
    password = validate_password(password)

    with transaction() as connection:
        if queries.get_user_credentials(connection, username) is not None:
            raise DuplicateUserError("Esse username já está a ser utilizado.")

        password_hash, password_salt = hash_password(password)
        try:
            user_id = queries.insert_user(
                connection, username, password_hash, password_salt, config.ROLE_PLAYER
            )
        except sqlite3.IntegrityError:
            # Segurança extra: se duas pessoas registarem o mesmo username
            # no mesmo instante, a restrição UNIQUE da BD apanha o duplicado.
            raise DuplicateUserError("Esse username já está a ser utilizado.")

        history.log_activity(
            connection, history.ACTION_REGISTER,
            f"Conta '{username}' criada.", user_id=user_id,
        )
        return User.from_row(queries.get_user_by_id(connection, user_id))


def login(username, password):
    """
    Verifica as credenciais e devolve o User autenticado.

    A mensagem de erro é a MESMA quer o username não exista, quer a
    password esteja errada: assim ninguém consegue descobrir que
    usernames existem.
    """
    with transaction() as connection:
        row = queries.get_user_credentials(connection, (username or "").strip())

        password_ok = row is not None and verify_password(
            password or "", row["password_hash"], row["password_salt"]
        )
        if not password_ok:
            raise AuthenticationError("Username ou password incorretos.")

        if row["status"] == config.STATUS_BLOCKED:
            raise UserBlockedError("Esta conta está bloqueada. Contacte um administrador.")

        history.log_activity(
            connection, history.ACTION_LOGIN,
            f"{row['username']} iniciou sessão.", user_id=row["id"],
        )
        return User.from_row(queries.get_user_by_id(connection, row["id"]))


def logout(user):
    """Regista o fim da sessão (a sessão em si vive no menu principal)."""
    with transaction() as connection:
        history.log_activity(
            connection, history.ACTION_LOGOUT,
            f"{user.username} terminou sessão.", user_id=user.id,
        )


def _check_current_password(connection, user, current_password):
    """Confirma a password atual (pedida antes de alterações sensíveis)."""
    row = queries.get_user_credentials_by_id(connection, user.id)
    if row is None or not verify_password(
        current_password or "", row["password_hash"], row["password_salt"]
    ):
        raise AuthenticationError("A password atual está incorreta.")


def change_password(user, current_password, new_password):
    """Altera a password (pede a atual para confirmar a identidade)."""
    new_password = validate_password(new_password)

    with transaction() as connection:
        _check_current_password(connection, user, current_password)
        password_hash, password_salt = hash_password(new_password)
        queries.update_password(connection, user.id, password_hash, password_salt)
        history.log_activity(
            connection, history.ACTION_ACCOUNT,
            f"{user.username} alterou a password.", user_id=user.id,
        )


def change_username(user, current_password, new_username):
    """
    Altera o username (pede a password atual). Atualiza também o objeto
    'user' recebido, para o resto da sessão já mostrar o nome novo.
    """
    new_username = validate_username(new_username)

    with transaction() as connection:
        _check_current_password(connection, user, current_password)

        existing = queries.get_user_credentials(connection, new_username)
        if existing is not None and existing["id"] != user.id:
            raise DuplicateUserError("Esse username já está a ser utilizado.")

        old_username = user.username
        try:
            queries.update_username(connection, user.id, new_username)
        except sqlite3.IntegrityError:
            raise DuplicateUserError("Esse username já está a ser utilizado.")

        history.log_activity(
            connection, history.ACTION_ACCOUNT,
            f"{old_username} alterou o username para {new_username}.", user_id=user.id,
        )

    user.username = new_username


def require_admin(connection, user):
    """
    Garante que 'user' é um administrador ativo; senão levanta
    PermissionDeniedError.

    O papel é lido DE NOVO da base de dados (e não do objeto 'user'), por
    isso um utilizador não consegue ganhar permissões só por alterar o
    objeto em memória, e um admin bloqueado perde logo o acesso.
    """
    if user is None:
        raise PermissionDeniedError("Tem de iniciar sessão.")

    row = queries.get_user_by_id(connection, user.id)
    if row is None or row["role"] != config.ROLE_ADMIN or row["status"] != config.STATUS_ACTIVE:
        raise PermissionDeniedError("Não tem permissão para esta operação.")
