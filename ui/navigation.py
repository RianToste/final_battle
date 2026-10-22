"""
Navegação entre menus e tratamento de erros da interface.

  - run_menu:   mostra um menu, lê a escolha e executa a ação.
  - run_safely: executa uma ação e, se der erro "esperado", mostra uma
                mensagem em vez de deixar o programa terminar.
"""

import logging
import sqlite3

from ui.input_helpers import ask_int, pause
from ui.messages import print_error, print_title
from utils.exceptions import GameError

logger = logging.getLogger(__name__)


def run_safely(action):
    """
    Executa 'action' (uma função sem argumentos) protegendo o programa.

      - GameError: erro previsto (dinheiro insuficiente, dados inválidos...).
        A mensagem já está escrita para o jogador.
      - sqlite3.Error: problema na base de dados. Mostra uma mensagem
        genérica e guarda os detalhes no ficheiro de log.
      - Qualquer outro erro: também é registado no log. É um bug, mas o
        jogo não deve fechar de repente.
    """
    try:
        action()
    except GameError as error:
        print_error(str(error))
    except sqlite3.Error:
        logger.exception("Erro na base de dados")
        print_error("Ocorreu um erro na base de dados. Tente novamente.")
    except (KeyboardInterrupt, EOFError):
        raise   # Ctrl+C / fim de input: tratado em main.py
    except Exception:
        logger.exception("Erro inesperado")
        print_error("Ocorreu um erro inesperado. Os detalhes ficaram registados.")


def run_menu(title, options, back_label="Voltar", pause_after=True):
    """
    Mostra um menu numerado e repete até o jogador escolher "0".

    - options: lista de tuplos (texto, função). Cada função não recebe
      argumentos. (Usamos "lambda: minha_funcao(user)" para passar dados.)
    - pause_after: se True, espera por Enter depois de cada ação, para dar
      tempo de ler o resultado. Usa-se False nos menus cujas opções abrem
      outros menus.
    """
    while True:
        print_title(title)
        for number, (label, _) in enumerate(options, start=1):
            print(f"  {number}. {label}")
        print(f"  0. {back_label}")

        choice = ask_int("Escolha uma opção: ", minimum=0, maximum=len(options))
        if choice == 0:
            return

        _, action = options[choice - 1]
        run_safely(action)
        if pause_after:
            pause()
