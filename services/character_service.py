"""
Serviço da personagem: criar, consultar, evolução, descanso e experiência.
"""

import sqlite3

import config
from database import queries
from database.connection import transaction
from models.character import Character
from services import history
from utils.exceptions import CharacterNotFoundError, ValidationError
from utils.validators import validate_character_class, validate_character_name


def create_character(user, name, class_name):
    """
    Cria a personagem do jogador (cada jogador só pode ter uma).
    Os valores iniciais dependem da classe escolhida (ver config.py).
    Devolve a Character criada.
    """
    name = validate_character_name(name)
    class_name = validate_character_class(class_name)
    stats = config.CHARACTER_CLASSES[class_name]

    with transaction() as connection:
        if queries.get_character_by_user_id(connection, user.id) is not None:
            raise ValidationError("Já tem uma personagem criada.")

        try:
            character_id = queries.insert_character(
                connection, user.id, name, class_name, stats
            )
        except sqlite3.IntegrityError:
            # A coluna 'name' é UNIQUE: o nome já pertence a outra personagem
            raise ValidationError("Já existe uma personagem com esse nome.")

        history.log_activity(
            connection, history.ACTION_CHARACTER,
            f"{name} ({class_name}) foi criado(a).",
            user_id=user.id, character_id=character_id,
        )
        return Character.from_row(queries.get_character_by_id(connection, character_id))


def find_character(user_id):
    """Devolve a Character do utilizador ou None se ainda não tiver."""
    with transaction() as connection:
        row = queries.get_character_by_user_id(connection, user_id)
    return Character.from_row(row) if row else None


def get_character(user):
    """Como find_character, mas levanta CharacterNotFoundError se não existir."""
    character = find_character(user.id)
    if character is None:
        raise CharacterNotFoundError("Ainda não criou uma personagem.")
    return character


def load_character(connection, character_id):
    """
    Carrega uma Character DENTRO de uma transação já aberta.
    Usado pelos outros serviços (loja, combate, missões).
    """
    row = queries.get_character_by_id(connection, character_id)
    if row is None:
        raise CharacterNotFoundError("Personagem não encontrada.")
    return Character.from_row(row)


def award_experience(connection, character, amount):
    """
    Dá XP à personagem (em memória) e regista cada subida de nível no
    histórico. Devolve o nº de níveis ganhos.

    ATENÇÃO: não grava a personagem! Quem chama deve fazer
    queries.save_character(connection, character) a seguir.
    """
    levels_gained = character.gain_experience(amount)
    if levels_gained > 0:
        history.log_activity(
            connection, history.ACTION_LEVEL_UP,
            f"{character.name} subiu para o nível {character.level}!",
            user_id=character.user_id, character_id=character.id,
        )
    return levels_gained


def get_equipment_bonuses(character_id):
    """Devolve (bónus de ataque, bónus de defesa) do equipamento no inventário."""
    with transaction() as connection:
        return queries.get_equipment_bonuses(connection, character_id)


def rest(character_id):
    """
    Descansar: recupera a vida e a energia ao máximo.
    Custa até config.REST_COST (se tiver menos dinheiro, paga só o que tem,
    para o jogador nunca ficar bloqueado). Devolve o custo pago.
    """
    with transaction() as connection:
        character = load_character(connection, character_id)

        if character.health >= character.max_health and character.energy >= config.MAX_ENERGY:
            raise ValidationError("Já está com a vida e a energia no máximo.")

        cost = min(config.REST_COST, character.money)
        character.spend_money(cost)
        character.health = character.max_health
        character.energy = config.MAX_ENERGY
        queries.save_character(connection, character)

        history.log_activity(
            connection, history.ACTION_REST,
            f"{character.name} descansou (custo: {cost} €).",
            user_id=character.user_id, character_id=character.id,
        )
    return cost


def get_evolution(character_id):
    """
    Reúne os dados para o jogador consultar a evolução da personagem:
      - 'level_ups':  histórico de subidas de nível;
      - 'combats':    resumo dos combates por resultado (nº, XP, dinheiro);
      - 'missions_completed': nº de missões concluídas.
    """
    with transaction() as connection:
        level_ups = queries.list_logs_by_action(
            connection, character_id, history.ACTION_LEVEL_UP, 50
        )
        combats = queries.get_combat_summary(connection, character_id)
        missions_completed = queries.count_completed_missions(connection, character_id)

    return {
        "level_ups": [dict(row) for row in level_ups],
        "combats": [dict(row) for row in combats],
        "missions_completed": missions_completed,
    }
