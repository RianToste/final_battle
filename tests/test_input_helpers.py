"""
Testa que o programa NÃO termina quando o jogador escreve algo inválido
(ex.: "Idade: abc"): mostra uma mensagem e volta a perguntar.
"""

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from ui.input_helpers import ask_int, ask_list_choice, ask_text, ask_yes_no
from utils.validators import validate_username


class InputHelpersTest(unittest.TestCase):
    def ask_with_inputs(self, function, inputs, *args, **kwargs):
        """Corre 'function' simulando que o jogador escreveu 'inputs' por ordem."""
        with patch("builtins.input", side_effect=inputs), redirect_stdout(io.StringIO()) as output:
            result = function(*args, **kwargs)
        return result, output.getvalue()

    def test_ask_int_repeats_until_valid(self):
        result, output = self.ask_with_inputs(ask_int, ["abc", "", "-5", "7"], "Idade: ", minimum=0)
        self.assertEqual(result, 7)
        self.assertIn("número inteiro", output)

    def test_ask_int_respects_maximum(self):
        result, _ = self.ask_with_inputs(ask_int, ["99", "3"], "N: ", minimum=1, maximum=5)
        self.assertEqual(result, 3)

    def test_ask_text_with_validator_repeats(self):
        result, output = self.ask_with_inputs(ask_text, ["x", "joao_1"], "User: ", validate_username)
        self.assertEqual(result, "joao_1")
        self.assertIn("username", output)

    def test_ask_yes_no(self):
        result, _ = self.ask_with_inputs(ask_yes_no, ["talvez", "S"], "Continuar")
        self.assertTrue(result)

    def test_ask_list_choice_zero_cancels(self):
        result, _ = self.ask_with_inputs(ask_list_choice, ["0"], "Nº: ", ["a", "b"])
        self.assertIsNone(result)
        result, _ = self.ask_with_inputs(ask_list_choice, ["2"], "Nº: ", ["a", "b"])
        self.assertEqual(result, "b")


if __name__ == "__main__":
    unittest.main()
