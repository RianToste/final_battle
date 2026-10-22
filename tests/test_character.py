"""Testes da personagem: criação, níveis/experiência, evolução e descanso."""

import unittest

import config
from models.character import Character
from services import character_service
from tests.base import GameTestCase
from utils.exceptions import (
    CharacterNotFoundError,
    InsufficientEnergyError,
    InsufficientFundsError,
    InvalidOperationError,
    ValidationError,
)


def make_character(**changes):
    """Cria uma Character em memória (sem base de dados) para testar as regras."""
    values = dict(
        id=1, user_id=1, name="Teste", character_class="Guerreiro", level=1,
        experience=0, health=120, max_health=120, energy=100, money=200,
        attack=12, defense=10, agility=5, wins=0, losses=0, created_at="2026-01-01 10:00:00",
    )
    values.update(changes)
    return Character(**values)


class CharacterModelTest(unittest.TestCase):
    """Regras da classe Character (não precisam de base de dados)."""

    def test_xp_needed_grows_with_level(self):
        self.assertEqual(Character.xp_needed_for_level(1), 100)
        self.assertGreater(Character.xp_needed_for_level(2), Character.xp_needed_for_level(1))

    def test_gain_experience_without_level_up(self):
        character = make_character()
        self.assertEqual(character.gain_experience(99), 0)
        self.assertEqual((character.level, character.experience), (1, 99))

    def test_level_up_applies_bonuses_and_keeps_extra_xp(self):
        character = make_character(health=10)
        gained = character.gain_experience(130)          # 100 para o nível + 30 de sobra
        self.assertEqual(gained, 1)
        self.assertEqual(character.level, 2)
        self.assertEqual(character.experience, 30)
        self.assertEqual(character.max_health, 120 + config.LEVEL_UP_HEALTH_BONUS)
        self.assertEqual(character.health, character.max_health)     # cura total
        self.assertEqual(character.attack, 12 + config.LEVEL_UP_ATTACK_BONUS)
        self.assertEqual(character.defense, 10 + config.LEVEL_UP_DEFENSE_BONUS)
        self.assertEqual(character.agility, 5 + config.LEVEL_UP_AGILITY_BONUS)

    def test_one_big_reward_can_give_several_levels(self):
        character = make_character()
        self.assertGreaterEqual(character.gain_experience(1000), 2)

    def test_max_level_is_never_exceeded(self):
        character = make_character(level=config.MAX_LEVEL)
        self.assertEqual(character.gain_experience(10 ** 9), 0)
        self.assertEqual(character.level, config.MAX_LEVEL)

    def test_spend_energy(self):
        character = make_character(energy=20)
        character.spend_energy(15)
        self.assertEqual(character.energy, 5)
        with self.assertRaises(InsufficientEnergyError):
            character.spend_energy(10)
        self.assertEqual(character.energy, 5)         # não mudou

    def test_money_rules(self):
        character = make_character(money=50)
        character.add_money(10)
        character.spend_money(60)
        self.assertEqual(character.money, 0)
        with self.assertRaises(InsufficientFundsError):
            character.spend_money(1)

    def test_heal_and_restore_energy_are_capped(self):
        character = make_character(health=100, energy=90)
        self.assertEqual(character.heal(50), 20)             # só curou até ao máximo
        self.assertEqual(character.restore_energy(40), 10)
        with self.assertRaises(InvalidOperationError):
            character.heal(10)
        with self.assertRaises(InvalidOperationError):
            character.restore_energy(10)


class CharacterServiceTest(GameTestCase):
    def test_create_character_uses_class_stats(self):
        user, character = self.create_player(class_name="Mago", name="Merlin")
        stats = config.CHARACTER_CLASSES["Mago"]
        self.assertEqual(character.name, "Merlin")
        self.assertEqual(character.character_class, "Mago")
        self.assertEqual(character.level, 1)
        self.assertEqual(character.experience, 0)
        self.assertEqual(character.health, stats["health"])
        self.assertEqual(character.attack, stats["attack"])
        self.assertEqual(character.money, config.STARTING_MONEY)
        self.assertEqual(character.energy, config.STARTING_ENERGY)
        self.assertTrue(character.created_at)

    def test_only_one_character_per_user(self):
        user, _ = self.create_player()
        with self.assertRaises(ValidationError):
            character_service.create_character(user, "Outro Nome", "Mago")

    def test_character_name_must_be_unique_ignoring_case(self):
        self.create_player("ana", name="Conan")
        user_2, _ = self._player_without_character("rui")
        with self.assertRaises(ValidationError):
            character_service.create_character(user_2, "conan", "Ladrao")

    def test_invalid_name_or_class(self):
        from services import authentication
        authentication.register_user("ana", "Senha1234")
        user = authentication.login("ana", "Senha1234")
        with self.assertRaises(ValidationError):
            character_service.create_character(user, "x", "Mago")
        with self.assertRaises(ValidationError):
            character_service.create_character(user, "Nome Bom", "Padeiro")

    def test_get_character_without_one_raises(self):
        from services import authentication
        authentication.register_user("ana", "Senha1234")
        user = authentication.login("ana", "Senha1234")
        self.assertIsNone(character_service.find_character(user.id))
        with self.assertRaises(CharacterNotFoundError):
            character_service.get_character(user)

    def _player_without_character(self, username):
        from services import authentication
        authentication.register_user(username, "Senha1234")
        return authentication.login(username, "Senha1234"), None

    def test_evolution_records_level_ups(self):
        user, character = self.create_player()
        from database.connection import transaction
        from database import queries
        with transaction() as connection:
            loaded = character_service.load_character(connection, character.id)
            levels = character_service.award_experience(connection, loaded, 130)
            queries.save_character(connection, loaded)
        self.assertEqual(levels, 1)

        evolution = character_service.get_evolution(character.id)
        self.assertEqual(len(evolution["level_ups"]), 1)
        self.assertIn("nível 2", evolution["level_ups"][0]["description"])
        self.assertEqual(self.reload(character.id).level, 2)

    def test_rest_restores_and_charges(self):
        _, character = self.create_player()
        self.set_character(character.id, health=10, energy=0)
        cost = character_service.rest(character.id)
        reloaded = self.reload(character.id)
        self.assertEqual(cost, config.REST_COST)
        self.assertEqual(reloaded.health, reloaded.max_health)
        self.assertEqual(reloaded.energy, config.MAX_ENERGY)
        self.assertEqual(reloaded.money, config.STARTING_MONEY - config.REST_COST)

    def test_rest_is_cheaper_when_player_is_broke(self):
        _, character = self.create_player()
        self.set_character(character.id, energy=0, money=5)
        self.assertEqual(character_service.rest(character.id), 5)
        self.assertEqual(self.reload(character.id).money, 0)

    def test_rest_when_already_full_is_refused(self):
        _, character = self.create_player()
        with self.assertRaises(ValidationError):
            character_service.rest(character.id)


if __name__ == "__main__":
    unittest.main()
