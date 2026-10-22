"""
Serviço da loja e do inventário: comprar, vender, usar objetos e
consultar o que se tem.

Compras e vendas são feitas dentro de UMA transação: ou acontece tudo
(dinheiro, stock, inventário e registo) ou não acontece nada.
"""

from dataclasses import dataclass, field
from typing import List

import config
from database import queries
from database.connection import transaction
from models.item import InventoryEntry, Item
from services import character_service, history, missions
from utils.exceptions import (
    InvalidOperationError,
    ItemNotFoundError,
    OutOfStockError,
)
from utils.validators import validate_positive_int


@dataclass
class Receipt:
    """Recibo de uma compra ou venda (para mostrar ao jogador)."""

    kind: str               # "compra" ou "venda"
    item_name: str
    quantity: int
    unit_price: int
    total: int
    balance_before: int
    balance_after: int
    completed_missions: List = field(default_factory=list)


@dataclass
class UseResult:
    """Resultado de usar um objeto."""

    item_name: str
    effect_type: str        # "curar" ou "energia"
    amount: int             # quanto foi realmente recuperado


# ------------------------------------------------------------
# Consultas
# ------------------------------------------------------------

def list_shop_items():
    """Todos os objetos da loja."""
    with transaction() as connection:
        rows = queries.list_items(connection)
    return [Item.from_row(row) for row in rows]


def get_inventory(character_id):
    """O inventário da personagem (lista de InventoryEntry)."""
    with transaction() as connection:
        rows = queries.list_inventory(connection, character_id)
    return [InventoryEntry.from_row(row) for row in rows]


def get_transactions(character_id, limit=config.HISTORY_DEFAULT_LIMIT):
    """Últimas compras/vendas da personagem."""
    with transaction() as connection:
        rows = queries.list_transactions(connection, character_id, limit)
    return [dict(row) for row in rows]


def _load_item(connection, item_id):
    """Carrega um Item ou levanta ItemNotFoundError."""
    row = queries.get_item_by_id(connection, item_id)
    if row is None:
        raise ItemNotFoundError("Esse objeto não existe.")
    return Item.from_row(row)


# ------------------------------------------------------------
# Comprar
# ------------------------------------------------------------

def buy_item(character_id, item_id, quantity):
    """
    Compra 'quantity' unidades de um objeto.

    Validações (cada uma levanta a sua exceção):
      - quantidade positiva;                      -> ValidationError
      - o objeto existe;                          -> ItemNotFoundError
      - há stock suficiente na loja;              -> OutOfStockError
      - a personagem tem dinheiro suficiente;     -> InsufficientFundsError
    Devolve um Receipt.
    """
    quantity = validate_positive_int(quantity, "A quantidade")

    with transaction() as connection:
        character = character_service.load_character(connection, character_id)
        item = _load_item(connection, item_id)

        if item.stock < quantity:
            raise OutOfStockError(
                f"Stock insuficiente: a loja tem {item.stock} unidade(s) de {item.name}."
            )

        total = item.price * quantity
        balance_before = character.money
        character.spend_money(total)          # levanta erro se não chegar

        # Tudo o que se segue é gravado na mesma transação
        queries.save_character(connection, character)
        queries.change_item_stock(connection, item.id, -quantity)
        queries.add_to_inventory(connection, character_id, item.id, quantity)
        queries.insert_transaction(
            connection, character_id, item.id, config.TRANSACTION_BUY,
            quantity, item.price, total, balance_before, character.money,
        )
        history.log_activity(
            connection, history.ACTION_BUY,
            f"{character.name} comprou {quantity}x {item.name} por {total} €.",
            user_id=character.user_id, character_id=character_id,
        )

        completed = missions.register_items_bought(connection, character_id, quantity)

        return Receipt(
            kind=config.TRANSACTION_BUY, item_name=item.name, quantity=quantity,
            unit_price=item.price, total=total, balance_before=balance_before,
            balance_after=character.money, completed_missions=completed,
        )


# ------------------------------------------------------------
# Vender
# ------------------------------------------------------------

def sell_item(character_id, item_id, quantity):
    """
    Vende 'quantity' unidades de um objeto do inventário.
    A loja paga config.SELL_PRICE_RATIO do preço original e fica com
    as unidades (o stock da loja aumenta). Devolve um Receipt.
    """
    quantity = validate_positive_int(quantity, "A quantidade")

    with transaction() as connection:
        character = character_service.load_character(connection, character_id)
        item = _load_item(connection, item_id)

        owned = queries.get_inventory_quantity(connection, character_id, item.id)
        if owned == 0:
            raise ItemNotFoundError(f"Não possui nenhum(a) {item.name}.")
        if owned < quantity:
            raise InvalidOperationError(
                f"Só tem {owned} unidade(s) de {item.name}."
            )

        total = item.sell_price * quantity
        balance_before = character.money
        character.add_money(total)

        queries.save_character(connection, character)
        queries.remove_from_inventory(connection, character_id, item.id, quantity)
        queries.change_item_stock(connection, item.id, quantity)
        queries.insert_transaction(
            connection, character_id, item.id, config.TRANSACTION_SELL,
            quantity, item.sell_price, total, balance_before, character.money,
        )
        history.log_activity(
            connection, history.ACTION_SELL,
            f"{character.name} vendeu {quantity}x {item.name} por {total} €.",
            user_id=character.user_id, character_id=character_id,
        )

        return Receipt(
            kind=config.TRANSACTION_SELL, item_name=item.name, quantity=quantity,
            unit_price=item.sell_price, total=total, balance_before=balance_before,
            balance_after=character.money,
        )


# ------------------------------------------------------------
# Usar objetos
# ------------------------------------------------------------

def use_item(character_id, item_id):
    """
    Usa uma unidade de um objeto consumível (poção).
      - "curar":   recupera vida;
      - "energia": recupera energia.
    Armas e armaduras NÃO se "usam": os seus bónus aplicam-se sozinhos
    em combate enquanto estiverem no inventário.
    Só gasta o objeto se o efeito for aplicado. Devolve um UseResult.
    """
    with transaction() as connection:
        character = character_service.load_character(connection, character_id)
        item = _load_item(connection, item_id)

        if queries.get_inventory_quantity(connection, character_id, item.id) == 0:
            raise ItemNotFoundError(f"Não possui nenhum(a) {item.name}.")

        if item.is_equipment:
            raise InvalidOperationError(
                f"{item.name} é equipamento: o bónus aplica-se automaticamente "
                "em combate enquanto estiver no seu inventário."
            )
        if not item.is_consumable:
            raise InvalidOperationError(f"{item.name} não tem nenhum efeito utilizável.")

        # heal()/restore_energy() levantam erro se já estiver no máximo,
        # e nesse caso o objeto NÃO é gasto.
        if item.effect_type == "curar":
            amount = character.heal(item.effect_value)
        else:
            amount = character.restore_energy(item.effect_value)

        queries.save_character(connection, character)
        queries.remove_from_inventory(connection, character_id, item.id, 1)
        history.log_activity(
            connection, history.ACTION_USE_ITEM,
            f"{character.name} usou {item.name}.",
            user_id=character.user_id, character_id=character_id,
        )

        return UseResult(item_name=item.name, effect_type=item.effect_type, amount=amount)
