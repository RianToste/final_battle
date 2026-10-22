"""
Ponto de entrada do jogo.

Passos:
  1. configura o registo de erros (ficheiro game_errors.log);
  2. prepara a base de dados (cria tabelas e dados iniciais, se for preciso);
  3. abre os menus.
"""

import logging

import config
from database.init_db import init_database
from ui.menus import run_application
from utils.exceptions import ConfigurationError


def setup_logging():
    """Os erros inesperados são guardados num ficheiro, não mostrados ao jogador."""
    logging.basicConfig(
        filename=config.LOG_FILE,
        level=logging.ERROR,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        encoding="utf-8",
    )


def main():
    """Arranca o jogo."""
    setup_logging()

    try:
        init_database()
    except ConfigurationError as error:
        print(f"[ERRO DE CONFIGURAÇÃO] {error}")
        return

    try:
        run_application()
    except (KeyboardInterrupt, EOFError):
        print("\nJogo terminado. Até breve!")


if __name__ == "__main__":
    main()