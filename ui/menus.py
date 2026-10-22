"""
Menus de entrada da aplicação: início, registo, login e área do jogador.
Fluxo geral:
    Menu inicial -> (login) -> administrador? -> menu de administração
                                    |
                                    +-> jogador -> (criar personagem) -> menu do jogador
"""

from services import authentication, character_service
from ui import admin_menus, game_menus, messages
from ui.input_helpers import ask_password, ask_text
from ui.navigation import run_menu
from utils.exceptions import AuthenticationError, UserBlockedError
from utils.validators import validate_password, validate_username

MAX_LOGIN_ATTEMPTS = 3


def run_application():
    """Ponto de entrada da interface: mostra o menu inicial."""
    options = [
        ("Iniciar sessão", login_flow),
        ("Registar nova conta", register_flow),
    ]
    messages.print_title("JOGO DE GESTÃO E ESTRATÉGIA")
    run_menu("MENU INICIAL", options, back_label="Sair", pause_after=False)
    messages.print_info("Até à próxima aventura!")


def register_flow():
    """Ecrã de registo: pede username e password (duas vezes)."""
    messages.print_title("REGISTAR CONTA")
    messages.print_info("Username: 3-20 caracteres (letras, números e _).")
    messages.print_info("Password: mínimo 8 caracteres, com letras e números.\n")

    username = ask_text("Username: ", validate_username)
    password = ask_password("Password: ", validate_password)
    repeated = ask_password("Repita a password: ")

    if password != repeated:
        messages.print_error("As passwords não coincidem.")
        return

    authentication.register_user(username, password)
    messages.print_success("Conta criada! Já pode iniciar sessão.")


def login_flow():
    """
    Ecrã de login. Dá até MAX_LOGIN_ATTEMPTS tentativas; depois volta
    ao menu inicial.
    """
    messages.print_title("INICIAR SESSÃO")

    for attempt in range(1, MAX_LOGIN_ATTEMPTS + 1):
        username = ask_text("Username: ")
        password = ask_password("Password: ")

        try:
            user = authentication.login(username, password)
        except AuthenticationError as error:
            messages.print_error(f"{error} (tentativa {attempt}/{MAX_LOGIN_ATTEMPTS})")
            continue
        except UserBlockedError as error:
            messages.print_error(str(error))
            return

        messages.print_success(f"Bem-vindo(a), {user.username}!")
        try:
            open_user_area(user)
        finally:
            # Mesmo que algo corra mal, a sessão fica sempre registada como terminada
            authentication.logout(user)
            messages.print_info("Sessão terminada.")
        return

    messages.print_error("Demasiadas tentativas falhadas.")


def open_user_area(user):
    """Encaminha o utilizador para a área certa conforme o tipo de conta."""
    if user.is_admin:
        admin_menus.admin_menu(user)
        return

    # Um jogador sem personagem tem primeiro de criar uma
    if character_service.find_character(user.id) is None:
        if game_menus.create_character_flow(user) is None:
            return

    options = [
        ("Ver personagem e evolução", lambda: game_menus.show_profile(user)),
        ("Inventário", lambda: game_menus.inventory_menu(user)),
        ("Loja", lambda: game_menus.shop_menu(user)),
        ("Missões", lambda: game_menus.missions_menu(user)),
        ("Combate", lambda: game_menus.combat_menu(user)),
        ("Descansar", lambda: game_menus.rest_action(user)),
        ("Ranking", lambda: game_menus.ranking_menu(user)),
        ("Histórico de atividade", lambda: game_menus.history_menu(user)),
        ("A minha conta", lambda: game_menus.account_menu(user)),
    ]
    # pause_after=False: o ecrã não é limpo, por isso o resultado de cada opção
    # fica visível por cima do menu seguinte. Os sub-menus tratam das suas pausas.
    run_menu(f"MENU DO JOGADOR - {user.username}", options,
             back_label="Terminar sessão", pause_after=False)
