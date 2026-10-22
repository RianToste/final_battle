"""
Serviço de combate.

COMO FUNCIONA UM COMBATE (por turnos, determinado pelas estatísticas):

  1. A personagem ataca primeiro; depois ataca o adversário; e assim
     sucessivamente até um dos dois ficar sem vida (ou passarem
     config.COMBAT_MAX_TURNS turnos -> empate).
  2. Em cada ataque:
       a) o defensor pode esquivar-se (probabilidade 'dodge_chance');
       b) dano base = ataque * 100 / (100 + defesa);
       c) o dano varia aleatoriamente +-20%;
       d) pode ser um golpe crítico (probabilidade 'crit_chance'), que
          causa 50% mais dano.
  3. O azar/sorte existe, mas quem tem melhores estatísticas ganha quase
     sempre. Por isso o jogo mostra uma ESTIMATIVA da probabilidade de
     vitória antes de lutar (estimate_win_chance).

O combate em si (simulate_combat) é uma função "pura": não mexe na base de
dados. Isso facilita os testes. Só fight() grava os resultados.
"""

import random
from dataclasses import dataclass, field
from typing import List

import config
from database import queries
from database.connection import transaction
from models.enemy import Enemy
from services import character_service, history, missions
from utils.exceptions import EnemyNotFoundError

# Valores possíveis do resultado (iguais aos do CHECK da tabela combats)
RESULT_WIN = "vitoria"
RESULT_LOSS = "derrota"
RESULT_DRAW = "empate"


@dataclass
class Fighter:
    """Um lutador (a personagem ou um adversário) com as estatísticas de combate."""

    name: str
    health: int
    attack: int
    defense: int
    dodge_chance: float
    crit_chance: float


@dataclass
class CombatOutcome:
    """Resultado de uma simulação de combate (ainda sem gravar nada)."""

    result: str
    turns: int
    damage_dealt: int            # dano causado pela personagem
    damage_taken: int            # dano sofrido pela personagem
    player_health_left: int
    rounds: List[str] = field(default_factory=list)   # relato turno a turno


@dataclass
class CombatReport:
    """Relatório final de um combate, já com as consequências aplicadas."""

    enemy_name: str
    result: str
    turns: int
    damage_dealt: int
    damage_taken: int
    xp_gained: int
    money_gained: int
    money_lost: int
    levels_gained: int
    new_level: int
    health_left: int
    rounds: List[str]
    completed_missions: List = field(default_factory=list)


# ------------------------------------------------------------
# Construção dos lutadores
# ------------------------------------------------------------

def build_player_fighter(character, attack_bonus=0, defense_bonus=0):
    """
    Converte uma Character num Fighter. Os bónus do equipamento somam-se
    ao ataque e à defesa. A agilidade dá probabilidade de esquivar e de
    acertar golpes críticos.
    """
    dodge = min(
        character.agility * config.COMBAT_DODGE_CHANCE_PER_AGILITY,
        config.COMBAT_MAX_DODGE_CHANCE,
    )
    crit = (config.COMBAT_BASE_CRIT_CHANCE
            + character.agility * config.COMBAT_CRIT_CHANCE_PER_AGILITY)
    return Fighter(
        name=character.name,
        health=character.health,
        attack=character.attack + attack_bonus,
        defense=character.defense + defense_bonus,
        dodge_chance=dodge,
        crit_chance=crit,
    )


def build_enemy_fighter(enemy):
    """Converte um Enemy num Fighter (as probabilidades vêm da BD)."""
    return Fighter(
        name=enemy.name,
        health=enemy.health,
        attack=enemy.attack,
        defense=enemy.defense,
        dodge_chance=enemy.dodge_chance,
        crit_chance=enemy.crit_chance,
    )


# ------------------------------------------------------------
# Lógica do combate (sem base de dados)
# ------------------------------------------------------------

def _attack(attacker, defender, rng):
    """
    Resolve UM ataque. Devolve (dano, esquivou, critico).
    'rng' é o gerador de números aleatórios (random.Random).
    """
    # a) o defensor esquiva-se?
    if rng.random() < defender.dodge_chance:
        return 0, True, False

    # b) dano base: a defesa reduz o dano em percentagem, nunca o anula
    base_damage = attacker.attack * config.COMBAT_DEFENSE_SCALE / (
        config.COMBAT_DEFENSE_SCALE + defender.defense
    )

    # c) variação aleatória (+-20%)
    variation = rng.uniform(
        1 - config.COMBAT_DAMAGE_VARIATION, 1 + config.COMBAT_DAMAGE_VARIATION
    )
    damage = base_damage * variation

    # d) golpe crítico
    is_crit = rng.random() < attacker.crit_chance
    if is_crit:
        damage *= config.COMBAT_CRIT_MULTIPLIER

    return max(config.COMBAT_MIN_DAMAGE, round(damage)), False, is_crit


def _describe_attack(turn, attacker, defender, damage, dodged, crit):
    """Frase que conta o que aconteceu num ataque (para o relato)."""
    if dodged:
        return f"Turno {turn}: {attacker.name} ataca, mas {defender.name} esquiva-se!"
    extra = " GOLPE CRÍTICO!" if crit else ""
    return f"Turno {turn}: {attacker.name} causa {damage} de dano a {defender.name}.{extra}"


def simulate_combat(player, enemy, rng=None, record_rounds=True):
    """
    Simula um combate completo entre dois Fighter e devolve um CombatOutcome.
    Não altera os objetos recebidos nem a base de dados.

    - rng: gerador aleatório. Nos testes passa-se random.Random(1) para o
      resultado ser sempre o mesmo.
    - record_rounds: se False não constrói o relato (mais rápido; usado nas
      estimativas, que simulam centenas de combates).
    """
    rng = rng or random.Random()
    player_health = player.health
    enemy_health = enemy.health
    damage_dealt = 0
    damage_taken = 0
    rounds = []
    result = RESULT_DRAW
    turn = 0

    for turn in range(1, config.COMBAT_MAX_TURNS + 1):
        # --- ataque da personagem ---
        damage, dodged, crit = _attack(player, enemy, rng)
        enemy_health -= damage
        damage_dealt += damage
        if record_rounds:
            rounds.append(_describe_attack(turn, player, enemy, damage, dodged, crit))
        if enemy_health <= 0:
            result = RESULT_WIN
            break

        # --- ataque do adversário ---
        damage, dodged, crit = _attack(enemy, player, rng)
        player_health -= damage
        damage_taken += damage
        if record_rounds:
            rounds.append(_describe_attack(turn, enemy, player, damage, dodged, crit))
        if player_health <= 0:
            result = RESULT_LOSS
            break

    return CombatOutcome(
        result=result,
        turns=turn,
        damage_dealt=damage_dealt,
        damage_taken=damage_taken,
        player_health_left=max(0, player_health),
        rounds=rounds,
    )


def estimate_win_chance(player, enemy, simulations=None, rng=None):
    """
    Estima a probabilidade (0 a 1) de a personagem vencer, simulando muitos
    combates. Serve para o jogador decidir se vale a pena arriscar.
    """
    simulations = simulations or config.COMBAT_WIN_ESTIMATE_SIMULATIONS
    rng = rng or random.Random()
    wins = sum(
        1 for _ in range(simulations)
        if simulate_combat(player, enemy, rng, record_rounds=False).result == RESULT_WIN
    )
    return wins / simulations


# ------------------------------------------------------------
# Operações com base de dados
# ------------------------------------------------------------

def list_enemies_with_odds(character_id):
    """
    Lista os adversários, cada um com a probabilidade estimada de vitória
    da personagem (tendo em conta a vida atual e o equipamento).
    Devolve uma lista de tuplos (Enemy, probabilidade).
    """
    with transaction() as connection:
        character = character_service.load_character(connection, character_id)
        attack_bonus, defense_bonus = queries.get_equipment_bonuses(connection, character_id)
        enemy_rows = queries.list_enemies(connection)

    player = build_player_fighter(character, attack_bonus, defense_bonus)
    result = []
    for row in enemy_rows:
        enemy = Enemy.from_row(row)
        result.append((enemy, estimate_win_chance(player, build_enemy_fighter(enemy))))
    return result


def fight(character_id, enemy_id, rng=None):
    """
    Faz a personagem lutar contra um adversário e grava as consequências:

      - gasta energia (levanta InsufficientEnergyError se não chegar);
      - vitória: ganha XP e dinheiro, +1 vitória, pode subir de nível;
      - derrota: perde uma percentagem do dinheiro e fica com pouca vida;
      - empate: não ganha nem perde nada (além da energia e da vida gasta);
      - regista o combate, o histórico e atualiza as missões.

    Tudo numa única transação: se algo falhar, nada é gravado.
    Devolve um CombatReport.
    """
    rng = rng or random.Random()

    with transaction() as connection:
        character = character_service.load_character(connection, character_id)

        enemy_row = queries.get_enemy_by_id(connection, enemy_id)
        if enemy_row is None:
            raise EnemyNotFoundError("Esse adversário não existe.")
        enemy = Enemy.from_row(enemy_row)

        character.spend_energy(config.ENERGY_COST_COMBAT)

        attack_bonus, defense_bonus = queries.get_equipment_bonuses(connection, character_id)
        outcome = simulate_combat(
            build_player_fighter(character, attack_bonus, defense_bonus),
            build_enemy_fighter(enemy),
            rng,
        )

        history.log_activity(
            connection, history.ACTION_COMBAT,
            f"{character.name} iniciou combate contra {enemy.name}.",
            user_id=character.user_id, character_id=character.id,
        )

        # --- Consequências do resultado ---
        xp_gained = money_gained = money_lost = 0

        if outcome.result == RESULT_WIN:
            xp_gained = enemy.reward_xp
            money_gained = enemy.reward_money
            character.wins += 1
            character.health = outcome.player_health_left
            character.add_money(money_gained)
            result_text = f"{character.name} venceu o combate contra {enemy.name}."
        elif outcome.result == RESULT_LOSS:
            money_lost = int(character.money * config.COMBAT_DEFEAT_MONEY_PENALTY)
            character.losses += 1
            character.health = config.COMBAT_DEFEAT_HEALTH
            character.money -= money_lost
            result_text = f"{character.name} perdeu o combate contra {enemy.name}."
        else:
            character.health = outcome.player_health_left
            result_text = f"{character.name} empatou o combate contra {enemy.name}."

        levels_gained = character_service.award_experience(connection, character, xp_gained)
        queries.save_character(connection, character)

        queries.insert_combat(
            connection, character.id, enemy.id, outcome.result, outcome.turns,
            outcome.damage_dealt, outcome.damage_taken, xp_gained, money_gained,
        )

        history.log_activity(connection, history.ACTION_COMBAT, result_text,
                             user_id=character.user_id, character_id=character.id)
        if xp_gained:
            history.log_activity(
                connection, history.ACTION_COMBAT,
                f"{character.name} recebeu {xp_gained} XP e {money_gained} €.",
                user_id=character.user_id, character_id=character.id,
            )
        if money_lost:
            history.log_activity(
                connection, history.ACTION_COMBAT,
                f"{character.name} perdeu {money_lost} € na derrota.",
                user_id=character.user_id, character_id=character.id,
            )

        # --- Missões (a personagem já está gravada) ---
        completed = []
        if outcome.result == RESULT_WIN:
            completed += missions.register_victory(connection, character.id, enemy.id)
        if levels_gained > 0:
            completed += missions.register_level(connection, character.id)

        # Recarrega a personagem: as recompensas das missões podem ter mudado o nível
        final = character_service.load_character(connection, character.id)

        return CombatReport(
            enemy_name=enemy.name, result=outcome.result, turns=outcome.turns,
            damage_dealt=outcome.damage_dealt, damage_taken=outcome.damage_taken,
            xp_gained=xp_gained, money_gained=money_gained, money_lost=money_lost,
            levels_gained=levels_gained, new_level=final.level,
            health_left=final.health, rounds=outcome.rounds,
            completed_missions=completed,
        )
