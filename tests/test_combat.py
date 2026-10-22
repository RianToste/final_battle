"""
Testes do combate.

Usamos random.Random(<número>) para o "acaso" ser sempre o mesmo e os
testes serem repetíveis. Para garantir vitórias/derrotas, alteramos as
estatísticas da personagem diretamente na BD.
"""

import random
import unittest

import config
from services import combat, history
from services.combat import Fighter
from tests.base import GameTestCase
from utils.exceptions import EnemyNotFoundError, InsufficientEnergyError


def fighter(name="F", health=100, attack=10, defense=0, dodge=0.0, crit=0.0):
    return Fighter(name, health, attack, defense, dodge, crit)


class SimulationTest(unittest.TestCase):
    """Lógica pura do combate (sem base de dados)."""

    def test_stronger_fighter_wins(self):
        outcome = combat.simulate_combat(
            fighter("Forte", health=1000, attack=200), fighter("Fraco", health=30, attack=1),
            random.Random(1),
        )
        self.assertEqual(outcome.result, combat.RESULT_WIN)
        self.assertEqual(outcome.damage_taken, 0 if outcome.turns == 1 else outcome.damage_taken)
        self.assertGreater(outcome.damage_dealt, 0)

    def test_weaker_fighter_loses(self):
        outcome = combat.simulate_combat(
            fighter("Fraco", health=5, attack=1), fighter("Forte", health=1000, attack=200),
            random.Random(1),
        )
        self.assertEqual(outcome.result, combat.RESULT_LOSS)
        self.assertEqual(outcome.player_health_left, 0)

    def test_draw_when_nobody_dies_in_time(self):
        outcome = combat.simulate_combat(
            fighter(health=10 ** 6), fighter(health=10 ** 6), random.Random(1)
        )
        self.assertEqual(outcome.result, combat.RESULT_DRAW)
        self.assertEqual(outcome.turns, config.COMBAT_MAX_TURNS)

    def test_same_seed_gives_same_result(self):
        first = combat.simulate_combat(fighter(), fighter(), random.Random(7))
        second = combat.simulate_combat(fighter(), fighter(), random.Random(7))
        self.assertEqual(first, second)

    def test_defense_reduces_damage_but_never_to_zero(self):
        weak_hit = combat._attack(fighter(attack=1), fighter(defense=10 ** 6), random.Random(1))
        self.assertGreaterEqual(weak_hit[0], config.COMBAT_MIN_DAMAGE)

        # Mais defesa => menos dano (sem variação aleatória nem crítico: média de muitos ataques)
        rng = random.Random(3)
        low_defense = sum(combat._attack(fighter(attack=50), fighter(defense=0), rng)[0] for _ in range(200))
        high_defense = sum(combat._attack(fighter(attack=50), fighter(defense=100), rng)[0] for _ in range(200))
        self.assertLess(high_defense, low_defense)

    def test_dodge_chance_one_means_no_damage(self):
        damage, dodged, crit = combat._attack(fighter(), fighter(dodge=1.0), random.Random(1))
        self.assertEqual((damage, dodged), (0, True))

    def test_crit_chance_one_always_crits(self):
        _, _, crit = combat._attack(fighter(crit=1.0), fighter(), random.Random(1))
        self.assertTrue(crit)

    def test_win_estimate_is_coherent_with_strength(self):
        rng = random.Random(5)
        easy = combat.estimate_win_chance(fighter(health=500, attack=100), fighter(health=20, attack=1), 100, rng)
        hopeless = combat.estimate_win_chance(fighter(health=10, attack=1), fighter(health=999, attack=999), 100, rng)
        self.assertEqual(easy, 1.0)
        self.assertEqual(hopeless, 0.0)

    def test_record_rounds_flag(self):
        with_rounds = combat.simulate_combat(fighter(), fighter(), random.Random(1))
        without = combat.simulate_combat(fighter(), fighter(), random.Random(1), record_rounds=False)
        self.assertTrue(with_rounds.rounds)
        self.assertEqual(without.rounds, [])
        self.assertEqual(with_rounds.result, without.result)   # mesmo resultado


class FightTest(GameTestCase):
    def setUp(self):
        super().setUp()
        self.user, self.character = self.create_player()
        self.rat_id = self.id_of("enemies", "Rato Gigante")     # 15 €, 30 XP
        self.troll_id = self.id_of("enemies", "Troll")

    def test_victory_gives_rewards_and_updates_character(self):
        self.make_strong(self.character.id)
        report = combat.fight(self.character.id, self.rat_id, random.Random(1))

        self.assertEqual(report.result, combat.RESULT_WIN)
        self.assertEqual((report.xp_gained, report.money_gained), (30, 15))
        after = self.reload(self.character.id)
        self.assertEqual(after.wins, 1)
        self.assertEqual(after.experience, 30)
        self.assertEqual(after.money, config.STARTING_MONEY + 15)
        self.assertEqual(after.energy, config.STARTING_ENERGY - config.ENERGY_COST_COMBAT)

    def test_combat_is_saved_and_logged(self):
        self.make_strong(self.character.id)
        combat.fight(self.character.id, self.rat_id, random.Random(1))

        self.assertEqual(self.scalar("SELECT COUNT(*) FROM combats WHERE result = 'vitoria'"), 1)
        texts = [e["description"] for e in history.get_user_history(self.user.id, 20)]
        self.assertTrue(any("iniciou combate contra Rato Gigante" in t for t in texts))
        self.assertTrue(any("venceu o combate" in t for t in texts))
        self.assertTrue(any("recebeu 30 XP" in t for t in texts))

    def test_defeat_costs_money_and_leaves_low_health(self):
        self.set_character(self.character.id, attack=1, health=1, agility=0, money=1000)
        report = combat.fight(self.character.id, self.troll_id, random.Random(1))

        self.assertEqual(report.result, combat.RESULT_LOSS)
        expected_loss = int(1000 * config.COMBAT_DEFEAT_MONEY_PENALTY)
        self.assertEqual(report.money_lost, expected_loss)
        after = self.reload(self.character.id)
        self.assertEqual(after.money, 1000 - expected_loss)
        self.assertEqual(after.losses, 1)
        self.assertEqual(after.wins, 0)
        self.assertEqual(after.health, config.COMBAT_DEFEAT_HEALTH)
        self.assertEqual(after.experience, 0)

    def test_victory_can_level_up(self):
        self.make_strong(self.character.id)
        self.set_character(self.character.id, experience=90)
        report = combat.fight(self.character.id, self.rat_id, random.Random(1))   # +30 XP
        self.assertEqual(report.levels_gained, 1)
        after = self.reload(self.character.id)
        self.assertEqual((after.level, after.experience), (2, 20))

    def test_not_enough_energy_blocks_combat_and_changes_nothing(self):
        self.set_character(self.character.id, energy=config.ENERGY_COST_COMBAT - 1)
        with self.assertRaises(InsufficientEnergyError):
            combat.fight(self.character.id, self.rat_id)
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM combats"), 0)
        self.assertEqual(self.reload(self.character.id).energy, config.ENERGY_COST_COMBAT - 1)

    def test_unknown_enemy(self):
        with self.assertRaises(EnemyNotFoundError):
            combat.fight(self.character.id, 99999)

    def test_equipment_improves_chances(self):
        from services import shop
        self.set_character(self.character.id, money=5000)
        before = dict((e.name, p) for e, p in combat.list_enemies_with_odds(self.character.id))
        shop.buy_item(self.character.id, self.id_of("items", "Espada de Ferro"), 1)
        shop.buy_item(self.character.id, self.id_of("items", "Armadura de Couro"), 1)
        after = dict((e.name, p) for e, p in combat.list_enemies_with_odds(self.character.id))
        self.assertGreaterEqual(after["Bandido"], before["Bandido"])

    def test_list_enemies_with_odds_orders_by_difficulty(self):
        odds = combat.list_enemies_with_odds(self.character.id)
        chances = {enemy.name: chance for enemy, chance in odds}
        self.assertGreater(chances["Rato Gigante"], 0.9)
        self.assertEqual(chances["Troll"], 0.0)       # nível 1 não vence o Troll


if __name__ == "__main__":
    unittest.main()
