"""
Modelo Mission: uma missão do catálogo, juntamente com o estado e o
progresso da personagem nessa missão.
"""

from dataclasses import dataclass
from typing import Optional

import config


@dataclass
class Mission:
    id: int
    name: str
    description: str
    difficulty: int
    min_level: int
    reward_money: int
    reward_xp: int
    objective_type: str
    objective_target_id: Optional[int]   # só existe em "defeat_enemies"
    objective_amount: int
    # Campos que dependem da personagem (vêm de character_missions).
    # Sem linha nessa tabela, a missão está "disponivel" com progresso 0.
    status: str = config.MISSION_AVAILABLE
    progress: int = 0
    target_name: Optional[str] = None    # nome do adversário-alvo (para mostrar)

    @classmethod
    def from_row(cls, row):
        """
        Cria uma Mission a partir de uma linha da base de dados.
        As colunas 'status', 'progress' e 'target_name' só existem nas
        consultas que juntam dados da personagem, por isso verificamos.
        """
        columns = row.keys()
        return cls(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            difficulty=row["difficulty"],
            min_level=row["min_level"],
            reward_money=row["reward_money"],
            reward_xp=row["reward_xp"],
            objective_type=row["objective_type"],
            objective_target_id=row["objective_target_id"],
            objective_amount=row["objective_amount"],
            status=row["status"] if "status" in columns and row["status"] else config.MISSION_AVAILABLE,
            progress=row["progress"] if "progress" in columns and row["progress"] else 0,
            target_name=row["target_name"] if "target_name" in columns else None,
        )

    @property
    def objective_text(self):
        """Frase legível com o objetivo da missão."""
        amount = self.objective_amount
        if self.objective_type == "defeat_enemies":
            return f"Derrotar {amount}x {self.target_name or 'adversário'}"
        if self.objective_type == "win_combats":
            return f"Vencer {amount} combates"
        if self.objective_type == "buy_items":
            return f"Comprar {amount} objeto(s)"
        if self.objective_type == "reach_level":
            return f"Atingir o nível {amount}"
        return self.description

    @property
    def progress_text(self):
        """Progresso no formato '2/3'."""
        return f"{self.progress}/{self.objective_amount}"
