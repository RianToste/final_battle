"""Testes da loja, inventário, compra, venda e uso de objetos."""

import unittest

import config
from database.connection import transaction
from services import character_service, shop
from tests.base import GameTestCase
from utils.exceptions import (
    InsufficientFundsError,
    InvalidOperationError,
    ItemNotFoundError,
    OutOfStockError,
    ValidationError,
)


class BuyTest(GameTestCase):
    def setUp(self):
        super().setUp()
        _, self.character = self.create_player()
        self.potion_id = self.id_of("items", "Pocao de Vida")      # 50 €, stock 50

    def test_buy_updates_money_stock_inventory_and_transactions(self):
        receipt = shop.buy_item(self.character.id, self.potion_id, 2)

        self.assertEqual(receipt.total, 100)
        self.assertEqual(receipt.balance_before, 200)
        self.assertEqual(receipt.balance_after, 100)
        self.assertEqual(self.reload(self.character.id).money, 100)
        self.assertEqual(self.scalar("SELECT stock FROM items WHERE id = ?", (self.potion_id,)), 48)

        inventory = shop.get_inventory(self.character.id)
        self.assertEqual([(e.item.name, e.quantity) for e in inventory], [("Pocao de Vida", 2)])

        transactions = shop.get_transactions(self.character.id)
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0]["type"], config.TRANSACTION_BUY)
        self.assertEqual(transactions[0]["balance_before"], 200)
        self.assertEqual(transactions[0]["balance_after"], 100)

    def test_buying_twice_adds_to_same_inventory_line(self):
        shop.buy_item(self.character.id, self.potion_id, 1)
        shop.buy_item(self.character.id, self.potion_id, 2)
        inventory = shop.get_inventory(self.character.id)
        self.assertEqual(len(inventory), 1)
        self.assertEqual(inventory[0].quantity, 3)

    def test_not_enough_money_changes_nothing(self):
        amulet_id = self.id_of("items", "Amuleto Antigo")          # 500 €
        with self.assertRaises(InsufficientFundsError):
            shop.buy_item(self.character.id, amulet_id, 1)

        self.assertEqual(self.reload(self.character.id).money, 200)
        self.assertEqual(self.scalar("SELECT stock FROM items WHERE id = ?", (amulet_id,)), 3)
        self.assertEqual(shop.get_inventory(self.character.id), [])
        self.assertEqual(shop.get_transactions(self.character.id), [])

    def test_out_of_stock(self):
        self.set_character(self.character.id, money=100000)
        amulet_id = self.id_of("items", "Amuleto Antigo")
        with self.assertRaises(OutOfStockError):
            shop.buy_item(self.character.id, amulet_id, 4)          # só há 3
        self.assertEqual(self.reload(self.character.id).money, 100000)

    def test_invalid_quantity_or_item(self):
        for bad in [0, -1, "abc"]:
            with self.subTest(quantity=bad):
                with self.assertRaises(ValidationError):
                    shop.buy_item(self.character.id, self.potion_id, bad)
        with self.assertRaises(ItemNotFoundError):
            shop.buy_item(self.character.id, 99999, 1)

    def test_purchase_is_logged_in_history(self):
        shop.buy_item(self.character.id, self.potion_id, 1)
        from services import history
        user_id = self.scalar("SELECT user_id FROM characters WHERE id = ?", (self.character.id,))
        descriptions = [e["description"] for e in history.get_user_history(user_id, 10)]
        self.assertTrue(any("comprou 1x Pocao de Vida" in d for d in descriptions))


class SellTest(GameTestCase):
    def setUp(self):
        super().setUp()
        _, self.character = self.create_player()
        self.potion_id = self.id_of("items", "Pocao de Vida")
        shop.buy_item(self.character.id, self.potion_id, 2)     # saldo: 100 €

    def test_sell_pays_half_price_and_restocks_shop(self):
        receipt = shop.sell_item(self.character.id, self.potion_id, 1)

        self.assertEqual(receipt.total, 25)                      # 50% de 50 €
        self.assertEqual(self.reload(self.character.id).money, 125)
        self.assertEqual(self.scalar("SELECT stock FROM items WHERE id = ?", (self.potion_id,)), 49)
        self.assertEqual(shop.get_inventory(self.character.id)[0].quantity, 1)
        self.assertEqual(shop.get_transactions(self.character.id)[0]["type"], config.TRANSACTION_SELL)

    def test_selling_everything_removes_inventory_line(self):
        shop.sell_item(self.character.id, self.potion_id, 2)
        self.assertEqual(shop.get_inventory(self.character.id), [])

    def test_cannot_sell_more_than_owned(self):
        with self.assertRaises(InvalidOperationError):
            shop.sell_item(self.character.id, self.potion_id, 3)
        self.assertEqual(self.reload(self.character.id).money, 100)

    def test_cannot_sell_what_you_do_not_have(self):
        with self.assertRaises(ItemNotFoundError):
            shop.sell_item(self.character.id, self.id_of("items", "Escudo de Madeira"), 1)


class UseItemTest(GameTestCase):
    def setUp(self):
        super().setUp()
        _, self.character = self.create_player()
        self.set_character(self.character.id, money=2000)
        self.life_id = self.id_of("items", "Pocao de Vida")
        self.energy_id = self.id_of("items", "Pocao de Energia")
        self.sword_id = self.id_of("items", "Espada de Ferro")
        self.tools_id = self.id_of("items", "Kit de Ferramentas")

    def test_life_potion_heals_and_is_consumed(self):
        shop.buy_item(self.character.id, self.life_id, 2)
        self.set_character(self.character.id, health=50)

        result = shop.use_item(self.character.id, self.life_id)

        self.assertEqual(result.amount, 50)
        self.assertEqual(self.reload(self.character.id).health, 100)
        self.assertEqual(shop.get_inventory(self.character.id)[0].quantity, 1)

    def test_energy_potion(self):
        shop.buy_item(self.character.id, self.energy_id, 1)
        self.set_character(self.character.id, energy=30)
        shop.use_item(self.character.id, self.energy_id)
        self.assertEqual(self.reload(self.character.id).energy, 70)

    def test_potion_is_not_wasted_when_already_full(self):
        shop.buy_item(self.character.id, self.life_id, 1)
        with self.assertRaises(InvalidOperationError):
            shop.use_item(self.character.id, self.life_id)
        self.assertEqual(shop.get_inventory(self.character.id)[0].quantity, 1)

    def test_cannot_use_item_you_do_not_own(self):
        with self.assertRaises(ItemNotFoundError):
            shop.use_item(self.character.id, self.life_id)

    def test_equipment_and_tools_cannot_be_used(self):
        shop.buy_item(self.character.id, self.sword_id, 1)
        shop.buy_item(self.character.id, self.tools_id, 1)
        with self.assertRaises(InvalidOperationError):
            shop.use_item(self.character.id, self.sword_id)
        with self.assertRaises(InvalidOperationError):
            shop.use_item(self.character.id, self.tools_id)

    def test_equipment_bonus_uses_best_item_of_each_kind(self):
        self.assertEqual(character_service.get_equipment_bonuses(self.character.id), (0, 0))
        shop.buy_item(self.character.id, self.sword_id, 1)                        # +4 ataque
        shop.buy_item(self.character.id, self.id_of("items", "Cajado Arcano"), 1)  # +7 ataque
        shop.buy_item(self.character.id, self.id_of("items", "Escudo de Madeira"), 1)  # +3 defesa
        self.assertEqual(character_service.get_equipment_bonuses(self.character.id), (7, 3))


if __name__ == "__main__":
    unittest.main()
