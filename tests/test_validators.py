"""Testes da validação de dados e da segurança das passwords."""

import unittest

from utils.exceptions import ValidationError
from utils.formatting import format_datetime, format_table
from utils.security import hash_password, verify_password
from utils.validators import (
    validate_character_class,
    validate_character_name,
    validate_choice,
    validate_float_range,
    validate_int_range,
    validate_password,
    validate_positive_int,
    validate_username,
)


class ValidatorsTest(unittest.TestCase):
    def test_username_valid_is_trimmed(self):
        self.assertEqual(validate_username("  joao_99 "), "joao_99")

    def test_username_invalid(self):
        for bad in ["ab", "a" * 21, "joao silva", "joão", "", None, "ana!"]:
            with self.subTest(username=bad):
                with self.assertRaises(ValidationError):
                    validate_username(bad)

    def test_password_rules(self):
        self.assertEqual(validate_password("abcdef12"), "abcdef12")
        for bad in ["curta1", "semnumeros", "12345678", "", None]:
            with self.subTest(password=bad):
                with self.assertRaises(ValidationError):
                    validate_password(bad)

    def test_character_name_and_class(self):
        self.assertEqual(validate_character_name(" Ana Maria "), "Ana Maria")
        with self.assertRaises(ValidationError):
            validate_character_name("A")
        with self.assertRaises(ValidationError):
            validate_character_name("Nome@@")
        self.assertEqual(validate_character_class("Mago"), "Mago")
        with self.assertRaises(ValidationError):
            validate_character_class("Padeiro")

    def test_numbers(self):
        self.assertEqual(validate_positive_int("3"), 3)
        for bad in ["abc", "0", "-2", "", None, "1.5"]:
            with self.subTest(value=bad):
                with self.assertRaises(ValidationError):
                    validate_positive_int(bad)

        self.assertEqual(validate_int_range("5", "X", 1, 5), 5)
        with self.assertRaises(ValidationError):
            validate_int_range("6", "X", 1, 5)
        self.assertEqual(validate_float_range("0,25", "P", 0, 1), 0.25)
        with self.assertRaises(ValidationError):
            validate_float_range("1.5", "P", 0, 1)
        with self.assertRaises(ValidationError):
            validate_float_range("abc", "P", 0, 1)

    def test_choice(self):
        self.assertEqual(validate_choice("arma", ["arma", "pocao"]), "arma")
        with self.assertRaises(ValidationError):
            validate_choice("casa", ["arma", "pocao"])


class SecurityTest(unittest.TestCase):
    def test_hash_is_not_plain_text_and_verifies(self):
        password_hash, salt = hash_password("Senha1234")
        self.assertNotIn("Senha1234", password_hash)
        self.assertTrue(verify_password("Senha1234", password_hash, salt))
        self.assertFalse(verify_password("senha1234", password_hash, salt))

    def test_same_password_gives_different_hashes(self):
        # O "salt" aleatório faz com que o mesmo texto gere hashes diferentes
        first_hash, _ = hash_password("Senha1234")
        second_hash, _ = hash_password("Senha1234")
        self.assertNotEqual(first_hash, second_hash)


class FormattingTest(unittest.TestCase):
    def test_format_datetime(self):
        self.assertEqual(format_datetime("2026-09-21 10:32:05"), "21/09/2026 10:32")
        self.assertEqual(format_datetime(None), "-")
        self.assertEqual(format_datetime("texto estranho"), "texto estranho")

    def test_format_table(self):
        self.assertEqual(format_table(["A"], []), "(sem dados)")
        table = format_table(["Nome", "Qtd"], [["Espada", 2]])
        self.assertIn("Espada", table)
        self.assertEqual(len(table.splitlines()), 3)


if __name__ == "__main__":
    unittest.main()
