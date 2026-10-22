"""
Modelos Item (um objeto da loja) e InventoryEntry (um objeto no inventário
de uma personagem, com a respetiva quantidade).
"""

from dataclasses import dataclass

import config


@dataclass
class Item:
    id: int
    name: str
    description: str
    type: str            # arma, armadura, pocao, ferramenta ou especial
    price: int           # preço de compra
    stock: int           # quantidade disponível na loja
    effect_type: str     # nenhum, curar, energia, bonus_ataque, bonus_defesa
    effect_value: int    # intensidade do efeito

    @classmethod
    def from_row(cls, row):
        """Cria um Item a partir de uma linha da base de dados."""
        return cls(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            type=row["type"],
            price=row["price"],
            stock=row["stock"],
            effect_type=row["effect_type"],
            effect_value=row["effect_value"],
        )

    @property
    def sell_price(self):
        """Quanto a loja paga quando o jogador vende este objeto."""
        return int(self.price * config.SELL_PRICE_RATIO)

    @property
    def is_equipment(self):
        """Armas e armaduras são equipamento (aplicam-se sozinhas em combate)."""
        return self.effect_type in ("bonus_ataque", "bonus_defesa")

    @property
    def is_consumable(self):
        """Poções e afins: gastam-se ao usar (curam vida ou energia)."""
        return self.effect_type in ("curar", "energia")

    @property
    def effect_text(self):
        """Descrição curta do efeito, para mostrar nas tabelas."""
        texts = {
            "curar": f"+{self.effect_value} vida",
            "energia": f"+{self.effect_value} energia",
            "bonus_ataque": f"+{self.effect_value} ataque",
            "bonus_defesa": f"+{self.effect_value} defesa",
        }
        return texts.get(self.effect_type, "-")


@dataclass
class InventoryEntry:
    """Uma linha do inventário: um Item e quantas unidades a personagem tem."""

    item: Item
    quantity: int

    @classmethod
    def from_row(cls, row):
        """
        A consulta do inventário junta as tabelas inventory e items, por isso
        a linha tem as colunas do item e também a coluna 'quantity'.
        """
        return cls(item=Item.from_row(row), quantity=row["quantity"])
