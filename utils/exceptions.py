"""
Exceções próprias do jogo.
"""


class GameError(Exception):
    """Erro base do jogo. A mensagem é sempre legível para o jogador."""


class ValidationError(GameError):
    """Um dado introduzido não cumpre as regras (ex.: password curta)."""


class AuthenticationError(GameError):
    """Credenciais inválidas no login."""


class UserBlockedError(GameError):
    """A conta está bloqueada pelo administrador."""


class PermissionDeniedError(GameError):
    """O utilizador não tem permissão para esta operação."""


class DuplicateUserError(GameError):
    """O username já existe."""


class CharacterNotFoundError(GameError):
    """O utilizador ainda não tem personagem."""


class InsufficientEnergyError(GameError):
    """A personagem não tem energia suficiente."""


class ItemNotFoundError(GameError):
    """O item não existe ou o jogador não o possui."""


class InsufficientFundsError(GameError):
    """Dinheiro insuficiente para a compra."""


class OutOfStockError(GameError):
    """Quantidade pedida superior à disponível na loja."""


class InvalidOperationError(GameError):
    """Operação não permitida no estado atual (ex.: poção com vida cheia)."""


class MissionError(GameError):
    """Erro numa missão (já aceite, nível insuficiente, não concluída...)."""

class UserNotFoundError(GameError):
    """O utilizador pedido não existe."""


class EnemyNotFoundError(GameError):
    """O adversário pedido não existe."""


class ConfigurationError(GameError):
    """Falta alguma configuração obrigatória (ex.: password do admin no .env)."""
