"""
Modelo Enemy: um adversário que a personagem pode enfrentar.
"""

from dataclasses import dataclass


@dataclass
class Enemy:
    id: int
    name: str
    level: int
    health: int
    attack: int
    defense: int
    reward_money: int
    reward_xp: int
    dodge_chance: float   # probabilidade (0 a 1) de se esquivar a um ataque
    crit_chance: float    # probabilidade (0 a 1) de acertar um golpe crítico

    @classmethod
    def from_row(cls, row):
        """Cria um Enemy a partir de uma linha da base de dados."""
        return cls(
            id=row["id"],
            name=row["name"],
            level=row["level"],
            health=row["health"],
            attack=row["attack"],
            defense=row["defense"],
            reward_money=row["reward_money"],
            reward_xp=row["reward_xp"],
            dodge_chance=row["dodge_chance"],
            crit_chance=row["crit_chance"],
        )
