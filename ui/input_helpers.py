"""
Funções para pedir dados ao jogador.
"""

import getpass

from utils.exceptions import ValidationError


def ask_text(prompt, validator=None):
    """
    Pede um texto. Se for passada uma função 'validator' (ex.:
    validate_username), usa-a para validar e repete se der erro.
    Devolve o texto já validado.
    """
    while True:
        value = input(prompt)
        if validator is None:
            return value.strip()
        try:
            return validator(value)
        except ValidationError as error:
            print(f"  - {error}")


def ask_password(prompt, validator=None):
    """
    Pede uma password sem a mostrar no ecrã (getpass).
    """
    while True:
        value = getpass.getpass(prompt)
        if validator is None:
            return value
        try:
            return validator(value)
        except ValidationError as error:
            print(f"  - {error}")


def ask_int(prompt, minimum=None, maximum=None):
    """
    Pede um número inteiro, opcionalmente dentro de um intervalo.
    """
    while True:
        raw = input(prompt).strip()
        try:
            number = int(raw)
        except ValueError:
            print("  - Introduza um número inteiro válido.")
            continue

        if minimum is not None and number < minimum:
            print(f"  - O valor mínimo é {minimum}.")
            continue
        if maximum is not None and number > maximum:
            print(f"  - O valor máximo é {maximum}.")
            continue
        return number


def ask_yes_no(prompt):
    """Faz uma pergunta de sim/não. Devolve True (sim) ou False (não)."""
    while True:
        answer = input(f"{prompt} (s/n): ").strip().lower()
        if answer in ("s", "sim"):
            return True
        if answer in ("n", "nao", "não"):
            return False
        print("  - Responda com 's' ou 'n'.")


def ask_choice(prompt, options):
    """
    Mostra uma lista numerada de opções e devolve a escolhida.
    - options: lista de textos
    Devolve o TEXTO da opção escolhida.
    """
    for index, option in enumerate(options, start=1):
        print(f"  {index}. {option}")
    chosen = ask_int(prompt, minimum=1, maximum=len(options))
    return options[chosen - 1]


def pause():
    """Espera que o jogador prima Enter (para dar tempo de ler o ecrã)."""
    input("\nPrima Enter para continuar...")

def ask_list_choice(prompt, items):
    """
    Pede ao jogador que escolha um elemento de uma lista já mostrada
    (com numeração a começar em 1). O número 0 cancela.

    Devolve o elemento escolhido, ou None se o jogador cancelou.
    """
    number = ask_int(prompt, minimum=0, maximum=len(items))
    if number == 0:
        return None
    return items[number - 1]
