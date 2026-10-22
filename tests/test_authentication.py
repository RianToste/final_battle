"""Testes de registo, login, alteração de conta e permissões."""

import unittest

import config
from database.connection import transaction
from services import authentication
from tests.base import GameTestCase
from utils.exceptions import (
    AuthenticationError,
    DuplicateUserError,
    PermissionDeniedError,
    UserBlockedError,
    ValidationError,
)


class RegistrationTest(GameTestCase):
    def test_register_creates_player(self):
        user = authentication.register_user("ana", "Senha1234")
        self.assertEqual(user.username, "ana")
        self.assertEqual(user.role, config.ROLE_PLAYER)
        self.assertFalse(user.is_admin)

    def test_password_is_never_stored_in_plain_text(self):
        authentication.register_user("ana", "Senha1234")
        stored_hash = self.scalar("SELECT password_hash FROM users WHERE username = 'ana'")
        self.assertNotEqual(stored_hash, "Senha1234")
        self.assertNotIn("Senha1234", stored_hash)

    def test_duplicate_username_is_rejected_ignoring_case(self):
        authentication.register_user("ana", "Senha1234")
        with self.assertRaises(DuplicateUserError):
            authentication.register_user("ANA", "Outra1234")

    def test_invalid_data_is_rejected(self):
        with self.assertRaises(ValidationError):
            authentication.register_user("a", "Senha1234")
        with self.assertRaises(ValidationError):
            authentication.register_user("ana", "curta")
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM users WHERE username = 'a'"), 0)

    def test_sql_injection_attempt_is_just_an_invalid_username(self):
        with self.assertRaises(ValidationError):
            authentication.register_user("x'; DROP TABLE users;--", "Senha1234")
        self.assertGreaterEqual(self.scalar("SELECT COUNT(*) FROM users"), 1)


class LoginTest(GameTestCase):
    def setUp(self):
        super().setUp()
        authentication.register_user("ana", "Senha1234")

    def test_login_success(self):
        user = authentication.login("ana", "Senha1234")
        self.assertEqual(user.username, "ana")

    def test_login_username_is_case_insensitive(self):
        self.assertEqual(authentication.login("ANA", "Senha1234").username, "ana")

    def test_wrong_password(self):
        with self.assertRaises(AuthenticationError):
            authentication.login("ana", "Errada123")

    def test_unknown_user_gets_the_same_message(self):
        with self.assertRaises(AuthenticationError) as unknown:
            authentication.login("fantasma", "Senha1234")
        with self.assertRaises(AuthenticationError) as wrong_password:
            authentication.login("ana", "Errada123")
        # Mensagens iguais: não revela que usernames existem
        self.assertEqual(str(unknown.exception), str(wrong_password.exception))

    def test_blocked_user_cannot_login(self):
        admin_user = self.login_admin()
        ana_id = self.scalar("SELECT id FROM users WHERE username = 'ana'")
        from services import admin
        admin.set_user_blocked(admin_user, ana_id, True)
        with self.assertRaises(UserBlockedError):
            authentication.login("ana", "Senha1234")

    def test_login_and_logout_are_logged(self):
        user = authentication.login("ana", "Senha1234")
        authentication.logout(user)
        actions = [row[0] for row in self._actions(user.id)]
        self.assertIn("LOGIN", actions)
        self.assertIn("LOGOUT", actions)

    def _actions(self, user_id):
        with transaction() as connection:
            return connection.execute(
                "SELECT action FROM activity_logs WHERE user_id = ?", (user_id,)
            ).fetchall()


class AccountChangesTest(GameTestCase):
    def setUp(self):
        super().setUp()
        authentication.register_user("ana", "Senha1234")
        authentication.register_user("rui", "Senha1234")
        self.user = authentication.login("ana", "Senha1234")

    def test_change_password(self):
        authentication.change_password(self.user, "Senha1234", "Nova12345")
        with self.assertRaises(AuthenticationError):
            authentication.login("ana", "Senha1234")
        self.assertEqual(authentication.login("ana", "Nova12345").username, "ana")

    def test_change_password_needs_current_password(self):
        with self.assertRaises(AuthenticationError):
            authentication.change_password(self.user, "Errada123", "Nova12345")

    def test_change_password_validates_new_one(self):
        with self.assertRaises(ValidationError):
            authentication.change_password(self.user, "Senha1234", "fraca")

    def test_change_username(self):
        authentication.change_username(self.user, "Senha1234", "ana_nova")
        self.assertEqual(self.user.username, "ana_nova")
        self.assertEqual(authentication.login("ana_nova", "Senha1234").username, "ana_nova")

    def test_change_username_to_existing_one_fails(self):
        with self.assertRaises(DuplicateUserError):
            authentication.change_username(self.user, "Senha1234", "rui")
        self.assertEqual(self.user.username, "ana")


class PermissionsTest(GameTestCase):
    def test_admin_passes_and_player_fails(self):
        admin_user = self.login_admin()
        player, _ = self.create_player()
        with transaction() as connection:
            authentication.require_admin(connection, admin_user)          # não levanta erro
            with self.assertRaises(PermissionDeniedError):
                authentication.require_admin(connection, player)
            with self.assertRaises(PermissionDeniedError):
                authentication.require_admin(connection, None)

    def test_changing_role_in_memory_does_not_grant_permissions(self):
        player, _ = self.create_player()
        player.role = config.ROLE_ADMIN       # "batota" só no objeto em memória
        with transaction() as connection:
            with self.assertRaises(PermissionDeniedError):
                authentication.require_admin(connection, player)


if __name__ == "__main__":
    unittest.main()
