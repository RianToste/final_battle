"""
Funções de validação de dados, reutilizadas em todo o projeto.

Regra de todas as funções:
  - se o valor é válido   -> devolvem o valor já "limpo" (sem espaços extra);
  - se o valor é inválido -> levantam ValidationError com uma mensagem clara.

Os limites vêm do config.py.
"""

import re

import config
from utils.exceptions import ValidationError

# Expressões regulares (padrões de texto permitidos)
_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")        # letras, números e _
_NAME_PATTERN = re.compile(r"^[A-Za-zÀ-ÿ0-9 ]+$")          # inclui acentos e espaços


def validate_username(username):
    """Username: 3 a 20 caracteres, só letras, números e underscore."""
    username = (username or "").strip()

    if not (config.USERNAME_MIN_LENGTH <= len(username) <= config.USERNAME_MAX_LENGTH):
        raise ValidationError(
            f"O username deve ter entre {config.USERNAME_MIN_LENGTH} "
            f"e {config.USERNAME_MAX_LENGTH} caracteres."
        )
    if not _USERNAME_PATTERN.match(username):
        raise ValidationError(
            "O username só pode conter letras, números e underscore (_)."
        )
    return username


def validate_password(password):
    """Password: mínimo de caracteres, com pelo menos uma letra e um número."""
    password = password or ""

    if len(password) < config.PASSWORD_MIN_LENGTH:
        raise ValidationError(
            f"A password deve ter pelo menos {config.PASSWORD_MIN_LENGTH} caracteres."
        )
    if not any(char.isalpha() for char in password):
        raise ValidationError("A password deve conter pelo menos uma letra.")
    if not any(char.isdigit() for char in password):
        raise ValidationError("A password deve conter pelo menos um número.")
    # A password NÃO leva strip(): espaços podem fazer parte dela.
    return password


def validate_character_name(name):
    """Nome da personagem: 3 a 20 caracteres (letras, números e espaços)."""
    name = (name or "").strip()

    if not (config.CHARACTER_NAME_MIN_LENGTH <= len(name) <= config.CHARACTER_NAME_MAX_LENGTH):
        raise ValidationError(
            f"O nome deve ter entre {config.CHARACTER_NAME_MIN_LENGTH} "
            f"e {config.CHARACTER_NAME_MAX_LENGTH} caracteres."
        )
    if not _NAME_PATTERN.match(name):
        raise ValidationError("O nome só pode conter letras, números e espaços.")
    return name


def validate_character_class(class_name):
    """A classe tem de existir em config.CHARACTER_CLASSES."""
    if class_name not in config.CHARACTER_CLASSES:
        valid = ", ".join(config.CHARACTER_CLASSES)
        raise ValidationError(f"Classe inválida. Classes disponíveis: {valid}.")
    return class_name


def validate_positive_int(value, field_name="Valor"):
    """
    Converte para inteiro e garante que é maior que zero.
    Aceita texto (ex.: "3"). Usado para quantidades.
    """
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} deve ser um número inteiro.")

    if number <= 0:
        raise ValidationError(f"{field_name} deve ser maior que zero.")
    return number


def validate_non_empty(text, field_name="Campo"):
    """Garante que o texto não está vazio (nem só com espaços)."""
    text = (text or "").strip()
    if not text:
        raise ValidationError(f"{field_name} não pode estar vazio.")
    return text

# ------------------------------------------------------------
# Validadores genéricos, usados sobretudo na área de administração
# (criar/editar objetos, adversários e missões).
# ------------------------------------------------------------

def validate_text(text, field_name="Campo", max_length=None):
    """Texto obrigatório (não vazio) com um comprimento máximo."""
    max_length = max_length or config.MAX_TEXT_LENGTH
    text = validate_non_empty(text, field_name)
    if len(text) > max_length:
        raise ValidationError(f"{field_name} deve ter no máximo {max_length} caracteres.")
    return text


def validate_int_range(value, field_name="Valor", minimum=None, maximum=None):
    """
    Converte para inteiro e verifica se está dentro de [minimum, maximum].
    Qualquer um dos limites pode ser None (sem limite).
    """
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} deve ser um número inteiro.")

    if minimum is not None and number < minimum:
        raise ValidationError(f"{field_name} deve ser pelo menos {minimum}.")
    if maximum is not None and number > maximum:
        raise ValidationError(f"{field_name} deve ser no máximo {maximum}.")
    return number


def validate_float_range(value, field_name="Valor", minimum=None, maximum=None):
    """
    Converte para número decimal dentro de [minimum, maximum].
    Aceita vírgula ou ponto como separador (0,05 ou 0.05).
    """
    try:
        number = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} deve ser um número (ex.: 0.05).")

    if minimum is not None and number < minimum:
        raise ValidationError(f"{field_name} deve ser pelo menos {minimum}.")
    if maximum is not None and number > maximum:
        raise ValidationError(f"{field_name} deve ser no máximo {maximum}.")
    return number


def validate_choice(value, valid_options, field_name="Valor"):
    """Garante que o valor é uma das opções permitidas."""
    value = (value or "").strip()
    if value not in valid_options:
        raise ValidationError(
            f"{field_name} inválido. Opções: {', '.join(valid_options)}."
        )
    return value
