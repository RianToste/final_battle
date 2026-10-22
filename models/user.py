"""
Modelo User: representa uma conta de utilizador (jogador ou administrador).

IMPORTANTE: este objeto NÃO guarda o hash da password. O hash só é lido
pelo módulo de autenticação, no momento do login. Assim, a informação
sensível nunca anda a "passear" pelo resto do programa.
"""

from dataclasses import dataclass

import config


# @dataclass gera automaticamente o __init__ (construtor), o __repr__ (texto
# para debug) e a comparação entre objetos, a partir dos campos listados.
@dataclass
class User:
    id: int
    username: str
    role: str
    status: str
    created_at: str

    @classmethod
    def from_row(cls, row):
        """Cria um User a partir de uma linha devolvida pela base de dados."""
        return cls(
            id=row["id"],
            username=row["username"],
            role=row["role"],
            status=row["status"],
            created_at=row["created_at"],
        )

    @property
    def is_admin(self):
        """True se o utilizador é administrador."""
        return self.role == config.ROLE_ADMIN

    @property
    def is_blocked(self):
        """True se a conta está bloqueada."""
        return self.status == config.STATUS_BLOCKED
