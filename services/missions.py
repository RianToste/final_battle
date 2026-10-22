"""
Serviço de missões: listar, aceitar, abandonar e atualizar o progresso.

Como funciona o progresso:
  - O jogador ACEITA uma missão (gasta energia) e ela fica "em curso".
  - Quando faz algo relevante (vencer um combate, comprar um objeto, subir
    de nível), os outros serviços avisam este módulo através das funções
    register_victory / register_items_bought / register_level.
  - Quando o progresso atinge o objetivo, a missão é CONCLUÍDA e a
    recompensa (dinheiro + XP) é entregue automaticamente.
"""

from dataclasses import dataclass

import config
from database import queries
from database.connection import transaction
from models.mission import Mission
from services import character_service, history
from utils.exceptions import MissionError


@dataclass
class CompletedMission:
    """Resumo de uma missão que acabou de ser concluída (para mostrar ao jogador)."""

    name: str
    reward_money: int
    reward_xp: int
    levels_gained: int


# ------------------------------------------------------------
# Consultas
# ------------------------------------------------------------

def list_missions(character_id):
    """Todas as missões com o estado/progresso desta personagem."""
    with transaction() as connection:
        rows = queries.list_missions_for_character(connection, character_id)
    return [Mission.from_row(row) for row in rows]


# ------------------------------------------------------------
# Aceitar e abandonar
# ------------------------------------------------------------

def accept_mission(character_id, mission_id):
    """
    Aceita uma missão. Regras:
      - a missão tem de existir;
      - não pode estar já em curso nem concluída (uma falhada pode ser repetida);
      - o nível da personagem tem de chegar ao mínimo exigido;
      - gasta config.ENERGY_COST_MISSION de energia.

    Devolve (missão, lista de CompletedMission). A lista só tem elementos
    se a missão já estiver cumprida no momento (ex.: "atingir o nível 3"
    quando já se é nível 5).
    """
    with transaction() as connection:
        character = character_service.load_character(connection, character_id)
        row = queries.get_mission_for_character(connection, character_id, mission_id)
        if row is None:
            raise MissionError("Missão inexistente.")
        mission = Mission.from_row(row)

        if mission.status == config.MISSION_IN_PROGRESS:
            raise MissionError("Já aceitou esta missão.")
        if mission.status == config.MISSION_COMPLETED:
            raise MissionError("Já concluiu esta missão.")
        if character.level < mission.min_level:
            raise MissionError(
                f"Precisa de nível {mission.min_level} para esta missão "
                f"(o seu nível é {character.level})."
            )

        character.spend_energy(config.ENERGY_COST_MISSION)
        queries.save_character(connection, character)
        queries.start_mission(connection, character_id, mission_id)

        history.log_activity(
            connection, history.ACTION_MISSION,
            f"{character.name} aceitou a missão '{mission.name}'.",
            user_id=character.user_id, character_id=character_id,
        )

        # Se o objetivo é "atingir o nível X" e já o cumpre, conclui logo
        completed = register_level(connection, character_id)

    return mission, completed


def abandon_mission(character_id, mission_id):
    """
    Abandona uma missão em curso: passa a 'falhada'.
    Pode ser aceite outra vez mais tarde (o progresso recomeça do zero).
    """
    with transaction() as connection:
        character = character_service.load_character(connection, character_id)
        row = queries.get_mission_for_character(connection, character_id, mission_id)
        if row is None:
            raise MissionError("Missão inexistente.")
        mission = Mission.from_row(row)

        if mission.status != config.MISSION_IN_PROGRESS:
            raise MissionError("Só pode abandonar missões que estejam em curso.")

        queries.finish_mission(
            connection, character_id, mission_id,
            config.MISSION_FAILED, mission.progress,
        )
        history.log_activity(
            connection, history.ACTION_MISSION,
            f"{character.name} abandonou a missão '{mission.name}'.",
            user_id=character.user_id, character_id=character_id,
        )
    return mission


# ------------------------------------------------------------
# Atualização do progresso (chamadas pelos outros serviços)
# Todas recebem a 'connection' da transação em curso.
# ------------------------------------------------------------

def register_victory(connection, character_id, enemy_id):
    """Chamar depois de uma vitória em combate. Devolve missões concluídas."""
    completed = _register_progress(
        connection, character_id, "defeat_enemies", 1, enemy_id=enemy_id
    )
    completed += _register_progress(connection, character_id, "win_combats", 1)
    return completed


def register_items_bought(connection, character_id, quantity):
    """Chamar depois de uma compra. Devolve missões concluídas."""
    return _register_progress(connection, character_id, "buy_items", quantity)


def register_level(connection, character_id):
    """
    Chamar quando o nível pode ter mudado. Nas missões "reach_level" o
    progresso é o próprio nível (não se soma). Devolve missões concluídas.
    """
    character = character_service.load_character(connection, character_id)
    return _register_progress(
        connection, character_id, "reach_level", character.level, absolute=True
    )


def _register_progress(connection, character_id, objective_type, amount,
                       enemy_id=None, absolute=False):
    """
    Atualiza o progresso de todas as missões em curso do tipo indicado.

    - amount:   quanto somar (ou o valor total, se absolute=True)
    - enemy_id: só conta para missões cujo alvo seja este adversário
    Devolve a lista de CompletedMission que ficaram cumpridas.
    """
    completed = []
    active_rows = queries.list_active_missions(connection, character_id, objective_type)

    for row in active_rows:
        mission = Mission.from_row(row)

        # "Derrotar X vezes o adversário Y": ignora vitórias contra outros
        if objective_type == "defeat_enemies" and mission.objective_target_id != enemy_id:
            continue

        new_progress = amount if absolute else mission.progress + amount
        new_progress = min(new_progress, mission.objective_amount)

        if new_progress >= mission.objective_amount:
            completed += _complete_mission(connection, character_id, mission)
        elif new_progress != mission.progress:
            queries.set_mission_progress(connection, character_id, mission.id, new_progress)

    return completed


def _complete_mission(connection, character_id, mission):
    """
    Conclui a missão e entrega a recompensa. Devolve uma lista com a
    missão concluída e quaisquer outras que a subida de nível tenha
    desbloqueado.
    """
    queries.finish_mission(
        connection, character_id, mission.id,
        config.MISSION_COMPLETED, mission.objective_amount,
    )

    character = character_service.load_character(connection, character_id)
    character.add_money(mission.reward_money)
    levels_gained = character_service.award_experience(connection, character, mission.reward_xp)
    queries.save_character(connection, character)

    history.log_activity(
        connection, history.ACTION_MISSION,
        f"{character.name} concluiu a missão '{mission.name}' "
        f"(+{mission.reward_money} €, +{mission.reward_xp} XP).",
        user_id=character.user_id, character_id=character_id,
    )

    result = [CompletedMission(mission.name, mission.reward_money,
                               mission.reward_xp, levels_gained)]

    # A recompensa pode ter feito subir de nível -> talvez complete outra missão
    if levels_gained > 0:
        result += register_level(connection, character_id)
    return result
