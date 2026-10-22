"""
Modelo Character: a personagem do jogador.

Esta classe contém as REGRAS que dizem respeito só à personagem:
subir de nível, gastar energia, gastar dinheiro, curar...
Ela não fala com a base de dados: quem a carrega e grava é o módulo de
serviços. Isto torna a classe fácil de testar e de perceber.
"""

from dataclasses import dataclass

import config
from utils.exceptions import (
    InsufficientEnergyError,
    InsufficientFundsError,
    InvalidOperationError,
)


@dataclass
class Character:
    id: int
    user_id: int
    name: str
    character_class: str
    level: int
    experience: int       # XP acumulado dentro do nível atual
    health: int
    max_health: int
    energy: int
    money: int
    attack: int
    defense: int
    agility: int
    wins: int
    losses: int
    created_at: str

    @classmethod
    def from_row(cls, row):
        """Cria uma Character a partir de uma linha da base de dados."""
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            name=row["name"],
            character_class=row["class"],   # 'class' é palavra reservada em Python
            level=row["level"],
            experience=row["experience"],
            health=row["health"],
            max_health=row["max_health"],
            energy=row["energy"],
            money=row["money"],
            attack=row["attack"],
            defense=row["defense"],
            agility=row["agility"],
            wins=row["wins"],
            losses=row["losses"],
            created_at=row["created_at"],
        )

    # ------------------------------------------------------------
    # Experiência e níveis
    # ------------------------------------------------------------

    @staticmethod
    def xp_needed_for_level(level):
        """XP necessário para passar do nível 'level' para o seguinte."""
        return int(config.XP_BASE * (level ** config.XP_EXPONENT))

    @property
    def xp_to_next_level(self):
        """XP necessário para o próximo nível (a partir do nível atual)."""
        return self.xp_needed_for_level(self.level)

    @property
    def is_max_level(self):
        """True se a personagem já atingiu o nível máximo."""
        return self.level >= config.MAX_LEVEL

    def gain_experience(self, amount):
        """
        Soma XP e sobe de nível as vezes que for preciso.
        Devolve quantos níveis foram ganhos (0 se não subiu).

        A cada nível: aumentam a vida máxima, o ataque, a defesa e a
        agilidade, e a vida fica totalmente recuperada.
        """
        self.experience += amount
        levels_gained = 0

        # "while": um único prémio grande pode dar vários níveis de uma vez
        while not self.is_max_level and self.experience >= self.xp_to_next_level:
            self.experience -= self.xp_to_next_level   # gasta o XP do nível
            self.level += 1
            self.max_health += config.LEVEL_UP_HEALTH_BONUS
            self.attack += config.LEVEL_UP_ATTACK_BONUS
            self.defense += config.LEVEL_UP_DEFENSE_BONUS
            self.agility += config.LEVEL_UP_AGILITY_BONUS
            self.health = self.max_health
            levels_gained += 1

        return levels_gained

    # ------------------------------------------------------------
    # Energia, vida e dinheiro
    # ------------------------------------------------------------

    def spend_energy(self, cost):
        """Gasta energia. Se não chegar, levanta InsufficientEnergyError."""
        if self.energy < cost:
            raise InsufficientEnergyError(
                f"Energia insuficiente: precisa de {cost}, tem {self.energy}. "
                "Use uma poção de energia ou descanse."
            )
        self.energy -= cost

    def restore_energy(self, amount):
        """
        Recupera energia (até ao máximo). Devolve quanto foi realmente
        recuperado. Se já estiver no máximo, levanta InvalidOperationError.
        """
        if self.energy >= config.MAX_ENERGY:
            raise InvalidOperationError("A energia já está no máximo.")
        before = self.energy
        self.energy = min(config.MAX_ENERGY, self.energy + amount)
        return self.energy - before

    def heal(self, amount):
        """
        Recupera vida (até ao máximo). Devolve quanto foi realmente curado.
        Se já tiver a vida cheia, levanta InvalidOperationError.
        """
        if self.health >= self.max_health:
            raise InvalidOperationError("A vida já está no máximo.")
        before = self.health
        self.health = min(self.max_health, self.health + amount)
        return self.health - before

    def add_money(self, amount):
        """Recebe dinheiro."""
        self.money += amount

    def spend_money(self, amount):
        """Gasta dinheiro. Se não chegar, levanta InsufficientFundsError."""
        if self.money < amount:
            raise InsufficientFundsError(
                f"Dinheiro insuficiente: precisa de {amount} €, tem {self.money} €."
            )
        self.money -= amount
