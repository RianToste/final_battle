"""
Serviço de ranking: classificação dos jogadores.
"""

import config
from database import queries
from database.connection import transaction
from utils.exceptions import ValidationError

# Critérios disponíveis (as chaves são as de queries.RANKING_ORDERS)
CRITERIA = {
    "nivel": "Nível (e experiência)",
    "dinheiro": "Dinheiro",
    "vitorias": "Vitórias em combate",
    "missoes": "Missões concluídas",
}


def get_ranking(criterion="nivel", limit=config.RANKING_TOP_N):
    """Devolve os melhores 'limit' jogadores (lista de dicionários com 'position')."""
    _check_criterion(criterion)
    with transaction() as connection:
        rows = queries.get_ranking(connection, criterion, limit)
    return [dict(row) for row in rows]


def get_my_position(character_id, criterion="nivel"):
    """Devolve a linha do ranking da personagem (com a posição) ou None."""
    _check_criterion(criterion)
    with transaction() as connection:
        row = queries.get_ranking_position(connection, criterion, character_id)
    return dict(row) if row else None


def _check_criterion(criterion):
    """Garante que o critério existe (evita SQL com valores inesperados)."""
    if criterion not in CRITERIA:
        raise ValidationError("Critério de ranking inválido.")
