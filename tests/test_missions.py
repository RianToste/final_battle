"""Testes das missões: aceitar, progresso, conclusão e recompensas."""

import random
import unittest

import config
from services import combat, missions, shop
from tests.base import GameTestCase
from utils.exceptions import InsufficientEnergyError, MissionError


class MissionsTest(GameTestCase):
    def setUp(self):
        super().setUp()
        self.user, self.character = self.create_player()
        self.cid = self.character.id
        self.first_buy = self.id_of("missions", "Primeiras Compras")      # comprar 1 objeto
        self.goblins = self.id_of("missions", "Caçador de Goblins")       # derrotar 3 Goblins
        self.apprentice = self.id_of("missions", "Aprendiz")              # atingir o nível 3
        self.wolves = self.id_of("missions", "Praga das Cavernas")        # nível mínimo 3

    def mission(self, mission_id):
        return next(m for m in missions.list_missions(self.cid) if m.id == mission_id)

    # --- listar e aceitar -------------------------------------------------

    def test_all_missions_start_available(self):
        listed = missions.list_missions(self.cid)
        self.assertEqual(len(listed), 5)
        self.assertTrue(all(m.status == config.MISSION_AVAILABLE for m in listed))

    def test_accept_puts_mission_in_progress_and_costs_energy(self):
        mission, completed = missions.accept_mission(self.cid, self.first_buy)
        self.assertEqual(completed, [])
        self.assertEqual(self.mission(self.first_buy).status, config.MISSION_IN_PROGRESS)
        self.assertEqual(self.reload(self.cid).energy,
                         config.STARTING_ENERGY - config.ENERGY_COST_MISSION)

    def test_cannot_accept_twice(self):
        missions.accept_mission(self.cid, self.first_buy)
        with self.assertRaises(MissionError):
            missions.accept_mission(self.cid, self.first_buy)

    def test_level_requirement(self):
        with self.assertRaises(MissionError):
            missions.accept_mission(self.cid, self.wolves)
        self.assertEqual(self.mission(self.wolves).status, config.MISSION_AVAILABLE)

    def test_not_enough_energy_to_accept(self):
        self.set_character(self.cid, energy=config.ENERGY_COST_MISSION - 1)
        with self.assertRaises(InsufficientEnergyError):
            missions.accept_mission(self.cid, self.first_buy)
        self.assertEqual(self.mission(self.first_buy).status, config.MISSION_AVAILABLE)

    def test_unknown_mission(self):
        with self.assertRaises(MissionError):
            missions.accept_mission(self.cid, 99999)

    # --- abandonar / falhar -----------------------------------------------

    def test_abandon_marks_failed_and_can_be_retried(self):
        missions.accept_mission(self.cid, self.first_buy)
        missions.abandon_mission(self.cid, self.first_buy)
        self.assertEqual(self.mission(self.first_buy).status, config.MISSION_FAILED)

        missions.accept_mission(self.cid, self.first_buy)       # recomeça
        retried = self.mission(self.first_buy)
        self.assertEqual((retried.status, retried.progress), (config.MISSION_IN_PROGRESS, 0))

    def test_cannot_abandon_mission_not_in_progress(self):
        with self.assertRaises(MissionError):
            missions.abandon_mission(self.cid, self.first_buy)

    # --- conclusão --------------------------------------------------------

    def test_buy_mission_completes_and_pays_reward(self):
        missions.accept_mission(self.cid, self.first_buy)
        receipt = shop.buy_item(self.cid, self.id_of("items", "Pocao de Vida"), 1)   # -50 €

        self.assertEqual([m.name for m in receipt.completed_missions], ["Primeiras Compras"])
        self.assertEqual(self.mission(self.first_buy).status, config.MISSION_COMPLETED)
        after = self.reload(self.cid)
        self.assertEqual(after.money, 200 - 50 + 30)           # recompensa: 30 €
        self.assertEqual(after.experience, 40)                 # recompensa: 40 XP

    def test_completed_mission_cannot_be_accepted_again(self):
        missions.accept_mission(self.cid, self.first_buy)
        shop.buy_item(self.cid, self.id_of("items", "Pocao de Vida"), 1)
        with self.assertRaises(MissionError):
            missions.accept_mission(self.cid, self.first_buy)

    def test_progress_before_accepting_does_not_count(self):
        shop.buy_item(self.cid, self.id_of("items", "Pocao de Vida"), 1)   # compra ANTES de aceitar
        missions.accept_mission(self.cid, self.first_buy)
        self.assertEqual(self.mission(self.first_buy).progress, 0)

    def test_defeat_enemies_mission_counts_only_the_target(self):
        self.make_strong(self.cid)
        goblin = self.id_of("enemies", "Goblin")
        rat = self.id_of("enemies", "Rato Gigante")
        missions.accept_mission(self.cid, self.goblins)

        combat.fight(self.cid, rat, random.Random(1))            # outro adversário: não conta
        self.assertEqual(self.mission(self.goblins).progress, 0)

        combat.fight(self.cid, goblin, random.Random(2))
        self.assertEqual(self.mission(self.goblins).progress_text, "1/3")
        combat.fight(self.cid, goblin, random.Random(3))
        report = combat.fight(self.cid, goblin, random.Random(4))

        self.assertEqual([m.name for m in report.completed_missions], ["Caçador de Goblins"])
        self.assertEqual(self.mission(self.goblins).status, config.MISSION_COMPLETED)
        # 200 inicial + 15 (rato) + 3x25 (goblins) + 80 (recompensa da missão)
        self.assertEqual(self.reload(self.cid).money, 200 + 15 + 75 + 80)

    def test_defeat_does_not_advance_mission(self):
        missions.accept_mission(self.cid, self.goblins)
        self.set_character(self.cid, attack=1, health=1, agility=0)
        combat.fight(self.cid, self.id_of("enemies", "Goblin"), random.Random(1))
        self.assertEqual(self.mission(self.goblins).progress, 0)

    def test_reach_level_mission_completes_when_leveling_up(self):
        self.make_strong(self.cid)
        missions.accept_mission(self.cid, self.apprentice)
        self.set_character(self.cid, experience=40)

        # O Troll dá 350 XP: 40 + 350 = 390 -> sobe do nível 1 ao 3
        report = combat.fight(self.cid, self.id_of("enemies", "Troll"), random.Random(1))

        self.assertEqual(report.levels_gained, 2)
        self.assertIn("Aprendiz", [m.name for m in report.completed_missions])
        self.assertEqual(self.mission(self.apprentice).status, config.MISSION_COMPLETED)

    def test_reach_level_completes_immediately_if_already_there(self):
        self.set_character(self.cid, level=5)
        _, completed = missions.accept_mission(self.cid, self.apprentice)
        self.assertEqual([m.name for m in completed], ["Aprendiz"])

    def test_win_combats_mission(self):
        self.make_strong(self.cid)
        self.set_character(self.cid, level=4, energy=100)
        arena = self.id_of("missions", "Campeão da Arena")
        missions.accept_mission(self.cid, arena)
        self.set_character(self.cid, energy=500)      # energia para 10 combates
        rat = self.id_of("enemies", "Rato Gigante")
        for seed in range(9):
            combat.fight(self.cid, rat, random.Random(seed))
        self.assertEqual(self.mission(arena).progress_text, "9/10")
        report = combat.fight(self.cid, rat, random.Random(99))
        self.assertEqual([m.name for m in report.completed_missions], ["Campeão da Arena"])


if __name__ == "__main__":
    unittest.main()
