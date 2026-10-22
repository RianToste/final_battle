"""Testes do ranking, do histórico e da área de administração."""

import unittest

import config
from services import admin, authentication, history, ranking, shop
from tests.base import GameTestCase
from utils.exceptions import (
    InvalidOperationError,
    ItemNotFoundError,
    PermissionDeniedError,
    UserNotFoundError,
    ValidationError,
)


class RankingTest(GameTestCase):
    def setUp(self):
        super().setUp()
        _, self.a = self.create_player("ana")
        _, self.b = self.create_player("rui")
        _, self.c = self.create_player("eva")
        self.set_character(self.a.id, level=3, money=50, wins=1)
        self.set_character(self.b.id, level=5, money=10, wins=0)
        self.set_character(self.c.id, level=3, experience=40, money=900, wins=7)

    def test_order_by_level_then_experience(self):
        top = ranking.get_ranking("nivel")
        self.assertEqual([p["character_id"] for p in top], [self.b.id, self.c.id, self.a.id])
        self.assertEqual([p["position"] for p in top], [1, 2, 3])

    def test_other_criteria(self):
        self.assertEqual(ranking.get_ranking("dinheiro")[0]["character_id"], self.c.id)
        self.assertEqual(ranking.get_ranking("vitorias")[0]["character_id"], self.c.id)

    def test_my_position(self):
        self.assertEqual(ranking.get_my_position(self.a.id)["position"], 3)
        self.assertEqual(ranking.get_my_position(self.b.id, "dinheiro")["position"], 3)

    def test_limit(self):
        self.assertEqual(len(ranking.get_ranking("nivel", limit=2)), 2)

    def test_completed_missions_criterion(self):
        from services import missions
        missions.accept_mission(self.a.id, self.id_of("missions", "Primeiras Compras"))
        shop.buy_item(self.a.id, self.id_of("items", "Pocao de Vida"), 1)
        top = ranking.get_ranking("missoes")
        self.assertEqual(top[0]["character_id"], self.a.id)
        self.assertEqual(top[0]["missions_completed"], 1)

    def test_blocked_players_are_hidden(self):
        user_id = self.scalar("SELECT user_id FROM characters WHERE id = ?", (self.b.id,))
        admin.set_user_blocked(self.login_admin(), user_id, True)
        ids = [p["character_id"] for p in ranking.get_ranking("nivel")]
        self.assertNotIn(self.b.id, ids)
        self.assertIsNone(ranking.get_my_position(self.b.id))

    def test_invalid_criterion_is_rejected(self):
        with self.assertRaises(ValidationError):
            ranking.get_ranking("1; DROP TABLE users")


class HistoryTest(GameTestCase):
    def test_actions_appear_in_order_for_the_right_user(self):
        user, character = self.create_player("ana")
        other, other_char = self.create_player("rui")
        shop.buy_item(character.id, self.id_of("items", "Pocao de Vida"), 1)
        shop.buy_item(other_char.id, self.id_of("items", "Pocao de Energia"), 1)

        entries = history.get_user_history(user.id, 20)
        texts = [e["description"] for e in entries]
        self.assertIn(f"{character.name} comprou 1x Pocao de Vida por 50 €.", texts)
        self.assertFalse(any("Energia" in t for t in texts))     # nada do outro jogador
        # mais recente primeiro
        self.assertIn("comprou", entries[0]["description"])

    def test_limit_is_respected(self):
        user, _ = self.create_player("ana")
        self.assertEqual(len(history.get_user_history(user.id, 1)), 1)


class AdminTest(GameTestCase):
    def setUp(self):
        super().setUp()
        self.admin = self.login_admin()
        self.player, self.character = self.create_player("ana")

    def item_data(self, **changes):
        data = dict(name="Lança", description="Uma lança.", type="arma", price=80,
                    stock=5, effect_type="bonus_ataque", effect_value=5)
        data.update(changes)
        return data

    # --- permissões -------------------------------------------------------

    def test_player_cannot_use_any_admin_operation(self):
        operations = [
            lambda: admin.list_users(self.player),
            lambda: admin.set_user_blocked(self.player, 1, True),
            lambda: admin.create_item(self.player, self.item_data()),
            lambda: admin.update_item(self.player, 1, {"price": 1}),
            lambda: admin.delete_item(self.player, 1),
            lambda: admin.create_enemy(self.player, {}),
            lambda: admin.list_combats(self.player),
            lambda: admin.get_system_statistics(self.player),
            lambda: admin.list_logs(self.player),
        ]
        for operation in operations:
            with self.subTest(operation=operation):
                with self.assertRaises((PermissionDeniedError, ValidationError)):
                    operation()
        # Nenhum objeto foi criado
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM items WHERE name = 'Lança'"), 0)

    def test_player_denied_even_with_valid_data(self):
        with self.assertRaises(PermissionDeniedError):
            admin.create_item(self.player, self.item_data())

    # --- utilizadores -----------------------------------------------------

    def test_list_users_shows_character(self):
        users = {u["username"]: u for u in admin.list_users(self.admin)}
        self.assertEqual(users["ana"]["character_name"], self.character.name)
        self.assertIsNone(users["admin"]["character_name"])

    def test_block_and_unblock(self):
        admin.set_user_blocked(self.admin, self.player.id, True)
        self.assertEqual(self.scalar("SELECT status FROM users WHERE id = ?", (self.player.id,)),
                         config.STATUS_BLOCKED)
        admin.set_user_blocked(self.admin, self.player.id, False)
        self.assertEqual(authentication.login("ana", "Senha1234").username, "ana")

    def test_cannot_block_yourself_or_unknown_users(self):
        with self.assertRaises(InvalidOperationError):
            admin.set_user_blocked(self.admin, self.admin.id, True)
        with self.assertRaises(UserNotFoundError):
            admin.set_user_blocked(self.admin, 99999, True)

    # --- objetos ----------------------------------------------------------

    def test_item_create_edit_delete(self):
        item_id = admin.create_item(self.admin, self.item_data())
        self.assertIn("Lança", [i.name for i in shop.list_shop_items()])

        admin.update_item(self.admin, item_id, {"price": "99", "stock": "2"})
        item = next(i for i in shop.list_shop_items() if i.id == item_id)
        self.assertEqual((item.price, item.stock), (99, 2))

        admin.delete_item(self.admin, item_id)
        self.assertNotIn("Lança", [i.name for i in shop.list_shop_items()])

    def test_item_validation(self):
        for bad in [self.item_data(price=-5), self.item_data(type="casa"),
                    self.item_data(name=""), self.item_data(stock="abc"),
                    self.item_data(effect_type="voar")]:
            with self.subTest(data=bad):
                with self.assertRaises(ValidationError):
                    admin.create_item(self.admin, bad)

    def test_duplicate_item_name_and_missing_field(self):
        admin.create_item(self.admin, self.item_data())
        with self.assertRaises(ValidationError):
            admin.create_item(self.admin, self.item_data())
        with self.assertRaises(ValidationError):
            admin.create_item(self.admin, {"name": "Só nome"})

    def test_cannot_delete_item_already_bought(self):
        potion = self.id_of("items", "Pocao de Vida")
        shop.buy_item(self.character.id, potion, 1)
        with self.assertRaises(InvalidOperationError):
            admin.delete_item(self.admin, potion)
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM items WHERE id = ?", (potion,)), 1)

    def test_edit_unknown_item_or_field(self):
        with self.assertRaises(ItemNotFoundError):
            admin.update_item(self.admin, 99999, {"price": 1})
        with self.assertRaises(ValidationError):
            admin.update_item(self.admin, self.id_of("items", "Pocao de Vida"), {"id": 7})
        with self.assertRaises(ValidationError):
            admin.update_item(self.admin, self.id_of("items", "Pocao de Vida"), {})

    # --- adversários e missões ---------------------------------------------

    def test_enemy_create_and_edit(self):
        enemy = dict(name="Dragão", level="10", health="500", attack="40", defense="25",
                     reward_money="500", reward_xp="900", dodge_chance="0,02", crit_chance="0.2")
        enemy_id = admin.create_enemy(self.admin, enemy)
        admin.update_enemy(self.admin, enemy_id, {"health": "600"})
        row = next(e for e in admin.list_enemies(self.admin) if e["id"] == enemy_id)
        self.assertEqual(row["health"], 600)
        self.assertEqual(row["dodge_chance"], 0.02)

    def test_enemy_probability_must_be_between_0_and_1(self):
        enemy = dict(name="Bug", level=1, health=10, attack=1, defense=1,
                     reward_money=1, reward_xp=1, dodge_chance=1.5, crit_chance=0.1)
        with self.assertRaises(ValidationError):
            admin.create_enemy(self.admin, enemy)

    def test_mission_create_and_edit(self):
        data = dict(name="Caça ao Rato", description="Mata ratos.", difficulty=1,
                    min_level=1, reward_money=10, reward_xp=10, objective_amount=2)
        rat = self.id_of("enemies", "Rato Gigante")
        mission_id = admin.create_mission(self.admin, data, "defeat_enemies", rat)
        admin.update_mission(self.admin, mission_id, {"reward_xp": "55"})

        row = next(m for m in admin.list_missions(self.admin) if m["id"] == mission_id)
        self.assertEqual((row["reward_xp"], row["objective_target_id"]), (55, rat))

    def test_mission_validation(self):
        data = dict(name="X", description="Y", difficulty=9, min_level=1,
                    reward_money=1, reward_xp=1, objective_amount=1)
        with self.assertRaises(ValidationError):
            admin.create_mission(self.admin, data, "win_combats")          # dificuldade 9
        data["difficulty"] = 2
        with self.assertRaises(ValidationError):
            admin.create_mission(self.admin, data, "voar")                  # tipo inválido

    # --- consultas ---------------------------------------------------------

    def test_statistics_combats_and_logs(self):
        import random
        from services import combat
        self.make_strong(self.character.id)
        combat.fight(self.character.id, self.id_of("enemies", "Rato Gigante"), random.Random(1))
        shop.buy_item(self.character.id, self.id_of("items", "Pocao de Vida"), 2)

        stats = admin.get_system_statistics(self.admin)
        self.assertEqual(stats["characters"]["total"], 1)
        self.assertEqual(stats["combats_by_result"], [{"result": "vitoria", "total": 1}])
        self.assertEqual(stats["best_selling_items"][0], {"name": "Pocao de Vida", "total": 2})

        combats = admin.list_combats(self.admin)
        self.assertEqual(combats[0]["enemy_name"], "Rato Gigante")

        logs = admin.list_logs(self.admin, 100)
        self.assertTrue(any("iniciou combate" in l["description"] for l in logs))

    def test_admin_actions_are_logged(self):
        admin.set_user_blocked(self.admin, self.player.id, True)
        logs = admin.list_logs(self.admin, 5)
        self.assertTrue(any(l["action"] == "ADMIN" and "bloqueou" in l["description"] for l in logs))

    def test_blocked_admin_loses_permissions(self):
        # Simula um admin bloqueado diretamente na BD
        from database.connection import transaction
        with transaction() as connection:
            connection.execute("UPDATE users SET status = 'bloqueado' WHERE id = ?", (self.admin.id,))
        with self.assertRaises(PermissionDeniedError):
            admin.list_users(self.admin)


if __name__ == "__main__":
    unittest.main()
