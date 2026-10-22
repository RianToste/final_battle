"""
Hashing e verificação de passwords.

Usamos PBKDF2-HMAC-SHA256 (biblioteca padrão do Python) com um "salt"
aleatório por utilizador. Assim:
  - a password nunca é guardada em texto simples;
  - duas pessoas com a mesma password têm hashes diferentes.
"""

import hashlib
import hmac
import os

import config


def hash_password(password):
    """
    Gera o hash de uma password.
    Devolve um tuplo (hash_hex, salt_hex), ambos em texto, prontos
    para guardar nas colunas password_hash e password_salt.
    """
    salt = os.urandom(config.PASSWORD_SALT_BYTES)  # bytes aleatórios seguros
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        config.PASSWORD_HASH_ITERATIONS,
    )
    return password_hash.hex(), salt.hex()


def verify_password(password, stored_hash, stored_salt):
    """
    Verifica se a password escrita corresponde ao hash guardado.
    Devolve True ou False.
    """
    salt = bytes.fromhex(stored_salt)
    new_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        config.PASSWORD_HASH_ITERATIONS,
    )
    # compare_digest compara em tempo constante: evita ataques por
    # medição do tempo de resposta.
    return hmac.compare_digest(new_hash.hex(), stored_hash)