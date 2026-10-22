"""
Histórico de atividade: regista e consulta as ações relevantes do jogo.

Exemplo de uma entrada:
    21/09/2026 10:35 — João comprou Poção de Vida
"""

from database import queries
from database.connection import transaction

# Códigos curtos que identificam o tipo de cada ação registada
ACTION_REGISTER = "REGISTO"
ACTION_LOGIN = "LOGIN"
ACTION_LOGOUT = "LOGOUT"
ACTION_ACCOUNT = "CONTA"
ACTION_CHARACTER = "PERSONAGEM"
ACTION_LEVEL_UP = "NIVEL"
ACTION_BUY = "COMPRA"
ACTION_SELL = "VENDA"
ACTION_USE_ITEM = "USO"
ACTION_COMBAT = "COMBATE"
ACTION_MISSION = "MISSAO"
ACTION_REST = "DESCANSO"
ACTION_ADMIN = "ADMIN"


def log_activity(connection, action, description, user_id=None, character_id=None):
    """
    Regista uma ação. Recebe a 'connection' de quem a chama para que o
    registo faça parte da MESMA transação: se a ação falhar e for
    desfeita, o registo também é desfeito.
    """
    queries.insert_log(connection, action, description, user_id, character_id)


def get_user_history(user_id, limit):
    """Devolve as últimas 'limit' ações de um utilizador (mais recentes primeiro)."""
    with transaction() as connection:
        rows = queries.list_logs_for_user(connection, user_id, limit)
    return [dict(row) for row in rows]
