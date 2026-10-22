"""
Serviço de administração.

TODAS as funções públicas deste módulo começam por verificar se quem as
chama é um administrador (require_admin). Assim, mesmo que a interface
tivesse um erro, um jogador normal nunca conseguiria executar estas
operações.
"""

import sqlite3
from dataclasses import dataclass
from typing import Optional, Sequence

import config
from database import queries
from database.connection import transaction
from services import history
from services.authentication import require_admin
from utils.exceptions import (
    EnemyNotFoundError,
    InvalidOperationError,
    ItemNotFoundError,
    MissionError,
    PermissionDeniedError,
    UserNotFoundError,
    ValidationError,
)
from utils.validators import (
    validate_choice,
    validate_float_range,
    validate_int_range,
    validate_text,
)


# ============================================================
# DESCRIÇÃO DOS CAMPOS EDITÁVEIS
#
# Em vez de escrever um formulário diferente para cada coisa, descrevemos
# cada campo (nome, tipo de valor, limites) e o mesmo código serve para
# validar e para a interface perguntar. A interface importa estas listas.
# ============================================================

@dataclass
class FieldSpec:
    column: str                          # nome da coluna na BD
    label: str                           # nome mostrado ao administrador
    kind: str                            # "text", "int", "float" ou "choice"
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    choices: Optional[Sequence[str]] = None


ITEM_FIELDS = [
    FieldSpec("name", "Nome", "text"),
    FieldSpec("description", "Descrição", "text"),
    FieldSpec("type", "Tipo", "choice", choices=config.ITEM_TYPES),
    FieldSpec("price", "Preço", "int", minimum=0),
    FieldSpec("stock", "Quantidade em stock", "int", minimum=0),
    FieldSpec("effect_type", "Tipo de efeito", "choice", choices=config.ITEM_EFFECT_TYPES),
    FieldSpec("effect_value", "Valor do efeito", "int", minimum=0),
]

ENEMY_FIELDS = [
    FieldSpec("name", "Nome", "text"),
    FieldSpec("level", "Nível", "int", minimum=1),
    FieldSpec("health", "Vida", "int", minimum=1),
    FieldSpec("attack", "Ataque", "int", minimum=0),
    FieldSpec("defense", "Defesa", "int", minimum=0),
    FieldSpec("reward_money", "Recompensa em dinheiro", "int", minimum=0),
    FieldSpec("reward_xp", "Recompensa em XP", "int", minimum=0),
    FieldSpec("dodge_chance", "Probabilidade de esquiva (0 a 1)", "float", minimum=0, maximum=1),
    FieldSpec("crit_chance", "Probabilidade de crítico (0 a 1)", "float", minimum=0, maximum=1),
]

# Campos de uma missão que se escolhem ao CRIAR
MISSION_FIELDS = [
    FieldSpec("name", "Nome", "text"),
    FieldSpec("description", "Descrição", "text"),
    FieldSpec("difficulty", "Dificuldade (1 a 5)", "int", minimum=1, maximum=5),
    FieldSpec("min_level", "Nível mínimo", "int", minimum=1),
    FieldSpec("reward_money", "Recompensa em dinheiro", "int", minimum=0),
    FieldSpec("reward_xp", "Recompensa em XP", "int", minimum=0),
    FieldSpec("objective_amount", "Quantidade do objetivo", "int", minimum=1),
]
OBJECTIVE_TYPE_FIELD = FieldSpec(
    "objective_type", "Tipo de objetivo", "choice", choices=config.OBJECTIVE_TYPES
)


def validate_field(spec, raw_value):
    """
    Valida e converte um valor de acordo com a descrição do campo.
    Devolve o valor convertido (texto, int ou float) ou levanta ValidationError.
    """
    if spec.kind == "text":
        return validate_text(raw_value, spec.label)
    if spec.kind == "int":
        return validate_int_range(raw_value, spec.label, spec.minimum, spec.maximum)
    if spec.kind == "float":
        return validate_float_range(raw_value, spec.label, spec.minimum, spec.maximum)
    if spec.kind == "choice":
        return validate_choice(raw_value, spec.choices, spec.label)
    raise ValueError(f"Tipo de campo desconhecido: {spec.kind}")


def _validate_all(fields, data):
    """Valida um dicionário completo {coluna: valor} (criação)."""
    clean = {}
    for spec in fields:
        if spec.column not in data:
            raise ValidationError(f"Falta o campo: {spec.label}.")
        clean[spec.column] = validate_field(spec, data[spec.column])
    return clean


def _validate_changes(fields, changes):
    """Valida só os campos que se querem alterar (edição)."""
    if not changes:
        raise ValidationError("Não indicou nenhuma alteração.")
    specs = {spec.column: spec for spec in fields}
    clean = {}
    for column, raw_value in changes.items():
        if column not in specs:
            raise ValidationError(f"O campo '{column}' não pode ser editado.")
        clean[column] = validate_field(specs[column], raw_value)
    return clean


def _log_admin(connection, admin_user, description):
    """Regista uma ação de administração no histórico."""
    history.log_activity(
        connection, history.ACTION_ADMIN,
        f"[Admin {admin_user.username}] {description}", user_id=admin_user.id,
    )


# ============================================================
# UTILIZADORES
# ============================================================

def list_users(admin_user):
    """Lista todos os utilizadores (com a personagem, se existir)."""
    with transaction() as connection:
        require_admin(connection, admin_user)
        return [dict(row) for row in queries.list_users_with_characters(connection)]


def set_user_blocked(admin_user, user_id, blocked):
    """
    Bloqueia (blocked=True) ou desbloqueia (blocked=False) um utilizador.
    Não se pode bloquear a própria conta nem outros administradores.
    """
    with transaction() as connection:
        require_admin(connection, admin_user)

        target = queries.get_user_by_id(connection, user_id)
        if target is None:
            raise UserNotFoundError("Esse utilizador não existe.")
        if target["id"] == admin_user.id:
            raise InvalidOperationError("Não pode bloquear a sua própria conta.")
        if target["role"] == config.ROLE_ADMIN:
            raise PermissionDeniedError("Não é possível bloquear outro administrador.")

        status = config.STATUS_BLOCKED if blocked else config.STATUS_ACTIVE
        queries.update_user_status(connection, user_id, status)
        action = "bloqueou" if blocked else "desbloqueou"
        _log_admin(connection, admin_user, f"{action} o utilizador {target['username']}.")


# ============================================================
# OBJETOS
# ============================================================

def create_item(admin_user, data):
    """Cria um objeto. 'data' é um dicionário {coluna: valor}. Devolve o id."""
    clean = _validate_all(ITEM_FIELDS, data)
    with transaction() as connection:
        require_admin(connection, admin_user)
        try:
            item_id = queries.insert_item(connection, clean)
        except sqlite3.IntegrityError:
            raise ValidationError("Já existe um objeto com esse nome.")
        _log_admin(connection, admin_user, f"criou o objeto '{clean['name']}'.")
    return item_id


def update_item(admin_user, item_id, changes):
    """Edita campos de um objeto. 'changes' é {coluna: novo valor}."""
    clean = _validate_changes(ITEM_FIELDS, changes)
    with transaction() as connection:
        require_admin(connection, admin_user)
        item = queries.get_item_by_id(connection, item_id)
        if item is None:
            raise ItemNotFoundError("Esse objeto não existe.")
        try:
            queries.update_item(connection, item_id, clean)
        except sqlite3.IntegrityError:
            raise ValidationError("Já existe um objeto com esse nome.")
        _log_admin(connection, admin_user, f"editou o objeto '{item['name']}'.")


def delete_item(admin_user, item_id):
    """
    Remove um objeto. Se já foi comprado por alguém (aparece em inventários
    ou transações) não pode ser apagado, para não corromper o histórico;
    nesse caso o admin deve pôr o stock a 0.
    """
    with transaction() as connection:
        require_admin(connection, admin_user)
        item = queries.get_item_by_id(connection, item_id)
        if item is None:
            raise ItemNotFoundError("Esse objeto não existe.")
        if queries.item_is_referenced(connection, item_id):
            raise InvalidOperationError(
                "Este objeto já foi comprado e não pode ser removido. "
                "Coloque o stock a 0 para deixar de estar disponível."
            )
        queries.delete_item(connection, item_id)
        _log_admin(connection, admin_user, f"removeu o objeto '{item['name']}'.")


# ============================================================
# ADVERSÁRIOS
# ============================================================

def create_enemy(admin_user, data):
    """Cria um adversário. Devolve o id."""
    clean = _validate_all(ENEMY_FIELDS, data)
    with transaction() as connection:
        require_admin(connection, admin_user)
        try:
            enemy_id = queries.insert_enemy(connection, clean)
        except sqlite3.IntegrityError:
            raise ValidationError("Já existe um adversário com esse nome.")
        _log_admin(connection, admin_user, f"criou o adversário '{clean['name']}'.")
    return enemy_id


def update_enemy(admin_user, enemy_id, changes):
    """Edita campos de um adversário."""
    clean = _validate_changes(ENEMY_FIELDS, changes)
    with transaction() as connection:
        require_admin(connection, admin_user)
        enemy = queries.get_enemy_by_id(connection, enemy_id)
        if enemy is None:
            raise EnemyNotFoundError("Esse adversário não existe.")
        try:
            queries.update_enemy(connection, enemy_id, clean)
        except sqlite3.IntegrityError:
            raise ValidationError("Já existe um adversário com esse nome.")
        _log_admin(connection, admin_user, f"editou o adversário '{enemy['name']}'.")


# ============================================================
# MISSÕES
# ============================================================

def create_mission(admin_user, data, objective_type, target_enemy_id=None):
    """
    Cria uma missão.
      - data: campos de MISSION_FIELDS;
      - objective_type: um de config.OBJECTIVE_TYPES;
      - target_enemy_id: obrigatório se o tipo for "defeat_enemies".
    Devolve o id da missão.
    """
    clean = _validate_all(MISSION_FIELDS, data)
    clean["objective_type"] = validate_field(OBJECTIVE_TYPE_FIELD, objective_type)

    with transaction() as connection:
        require_admin(connection, admin_user)

        if clean["objective_type"] == "defeat_enemies":
            if target_enemy_id is None or queries.get_enemy_by_id(connection, target_enemy_id) is None:
                raise MissionError("Escolha um adversário válido como alvo da missão.")
            clean["objective_target_id"] = target_enemy_id
        else:
            clean["objective_target_id"] = None

        try:
            mission_id = queries.insert_mission(connection, clean)
        except sqlite3.IntegrityError:
            raise ValidationError("Já existe uma missão com esse nome.")
        _log_admin(connection, admin_user, f"criou a missão '{clean['name']}'.")
    return mission_id


def update_mission(admin_user, mission_id, changes):
    """
    Edita campos de uma missão (os de MISSION_FIELDS). O tipo de objetivo e
    o alvo não se alteram, para não invalidar o progresso dos jogadores.
    """
    clean = _validate_changes(MISSION_FIELDS, changes)
    with transaction() as connection:
        require_admin(connection, admin_user)
        mission = queries.get_mission_by_id(connection, mission_id)
        if mission is None:
            raise MissionError("Essa missão não existe.")
        try:
            queries.update_mission(connection, mission_id, clean)
        except sqlite3.IntegrityError:
            raise ValidationError("Já existe uma missão com esse nome.")
        _log_admin(connection, admin_user, f"editou a missão '{mission['name']}'.")


# ============================================================
# CONSULTAS: partidas (combates), estatísticas e logs
# ============================================================

def list_combats(admin_user, limit=30):
    """Últimos combates (partidas) de todos os jogadores."""
    with transaction() as connection:
        require_admin(connection, admin_user)
        return [dict(row) for row in queries.list_combats(connection, limit)]


def get_system_statistics(admin_user):
    """Reúne estatísticas gerais do sistema num dicionário."""
    with transaction() as connection:
        require_admin(connection, admin_user)
        characters = queries.get_character_statistics(connection)
        return {
            "users_by_status": [dict(r) for r in queries.count_users_by_status(connection)],
            "characters": dict(characters),
            "combats_by_result": [dict(r) for r in queries.count_combats_by_result(connection)],
            "best_selling_items": [dict(r) for r in queries.get_best_selling_items(connection, 5)],
            "missions_completed": [dict(r) for r in queries.get_missions_completed_count(connection)],
        }


def list_logs(admin_user, limit=50):
    """Últimos registos de atividade de todo o sistema."""
    with transaction() as connection:
        require_admin(connection, admin_user)
        return [dict(row) for row in queries.list_all_logs(connection, limit)]


# ============================================================
# CATÁLOGOS (para o administrador escolher o que editar)
# ============================================================

def list_items(admin_user):
    """Todos os objetos (linhas em bruto) para a administração."""
    with transaction() as connection:
        require_admin(connection, admin_user)
        return [dict(row) for row in queries.list_items(connection)]


def list_enemies(admin_user):
    """Todos os adversários para a administração."""
    with transaction() as connection:
        require_admin(connection, admin_user)
        return [dict(row) for row in queries.list_enemies(connection)]


def list_missions(admin_user):
    """Todas as missões do catálogo para a administração."""
    with transaction() as connection:
        require_admin(connection, admin_user)
        return [dict(row) for row in queries.list_missions(connection)]
