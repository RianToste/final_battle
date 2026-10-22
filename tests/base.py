"""
Classe base dos testes.

Cada teste corre com uma base de dados NOVA e temporária (num ficheiro
dentro de uma pasta temporária), por isso os testes nunca mexem no jogo
real nem se influenciam uns aos outros.
"""

import os
import tempfile
import unittest

import config
from database.connection import transaction
from database.init_db import init_database
from services import authentication, character_service

# Valores de config que os testes alteram (guardamos os originais para repor)
_CONFIG_KEYS = ("DATABASE_PATH", "ADMIN_USERNAME", "ADMIN_PASSWORD", "PASSWORD_HASH_ITERATIONS")


class GameTestCase(unittest.TestCase):
    """Prepara e limpa uma base de dados de teste para cada teste."""

    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self._original_config = {key: getattr(config, key) for key in _CONFIG_KEYS}

        config.DATABASE_PATH = os.path.join(self._temp_dir.name, "test.db")
        config.ADMIN_USERNAME = "admin"
        config.ADMIN_PASSWORD = "Admin1234"
        # Menos iterações: o hashing fica rápido e os testes não demoram
        config.PASSWORD_HASH_ITERATIONS = 1000

        init_database()

    def tearDown(self):
        for key, value in self._original_config.items():
            setattr(config, key, value)
        self._temp_dir.cleanup()

    # ------------------------------------------------------------
    # Auxiliares reutilizados pelos testes
    # ------------------------------------------------------------

    def create_player(self, username="ana", class_name="Guerreiro", name=None):
        """Regista um jogador e cria-lhe a personagem. Devolve (user, character)."""
        authentication.register_user(username, "Senha1234")
        user = authentication.login(username, "Senha1234")
        character = character_service.create_character(
            user, name or f"Heroi {username}", class_name
        )
        return user, character

    def login_admin(self):
        """Devolve o User do administrador criado na inicialização."""
        return authentication.login("admin", "Admin1234")

    def set_character(self, character_id, **fields):
        """Altera diretamente colunas da personagem (para preparar cenários)."""
        assignments = ", ".join(f"{column} = ?" for column in fields)
        with transaction() as connection:
            connection.execute(
                f"UPDATE characters SET {assignments} WHERE id = ?",
                list(fields.values()) + [character_id],
            )

    def make_strong(self, character_id):
        """Torna a personagem praticamente invencível (vitória garantida)."""
        self.set_character(
            character_id, attack=5000, health=100000, max_health=100000, defense=500
        )

    def reload(self, character_id):
        """Volta a ler a personagem da base de dados."""
        with transaction() as connection:
            return character_service.load_character(connection, character_id)

    def id_of(self, table, name):
        """Devolve o id de um item/adversário/missão pelo nome."""
        with transaction() as connection:
            row = connection.execute(
                f"SELECT id FROM {table} WHERE name = ?", (name,)
            ).fetchone()
        return row["id"]

    def scalar(self, sql, params=()):
        """Executa um SELECT que devolve um único valor."""
        with transaction() as connection:
            return connection.execute(sql, params).fetchone()[0]
