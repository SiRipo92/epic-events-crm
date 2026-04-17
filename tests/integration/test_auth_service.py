"""
Integration tests for the authentication service.

Tests run against a real PostgreSQL test database.
Each test runs in its own transaction that rolls back on teardown.
"""

import logging

from services.auth_service import (
    change_password,
    get_session_user,
    login,
    logout,
)

logger = logging.getLogger(__name__)


class TestLoginIntegration:
    """Integration tests for the login() auth service function."""

    def test_valid_credentials_returns_collaborator(
        self, seeded_db, db_session, session_file
    ):
        """Full login flow: real DB query + bcrypt verify + token written."""
        manager = seeded_db["management"]
        logger.info("Attempting login for %s", manager.email)

        result = login(db_session, manager.email, "Password123")

        logger.info("Login successful — collaborator id=%s", result.id)
        assert result.id == manager.id
        assert session_file.exists()
        logger.info("Session file written at %s", session_file)

    def test_get_session_user_returns_correct_collaborator(
        self, seeded_db, db_session, session_file
    ):
        """JWT round trip: login writes token, get_session_user reads it back."""
        manager = seeded_db["management"]
        logger.info("Logging in as %s to establish session", manager.email)
        login(db_session, manager.email, "Password123")

        logger.info("Reading session user from token")
        result = get_session_user(db_session)

        logger.info(
            "Session user resolved — id=%s role=%s",
            result.id,
            result.role.name,
        )
        assert result.id == manager.id
        assert result.role.name == "MANAGEMENT"

    def test_logout_deletes_session_file(self, seeded_db, db_session, session_file):
        """Logout removes the session file written by login."""
        manager = seeded_db["management"]
        login(db_session, manager.email, "Password123")
        logger.info("Session file exists before logout: %s", session_file.exists())

        logout()

        logger.info("Session file exists after logout: %s", session_file.exists())
        assert not session_file.exists()

    def test_change_password_persists_to_db(self, seeded_db, db_session):
        """New password hash is actually written to the database."""
        manager = seeded_db["management"]
        logger.info("Changing password for %s", manager.email)

        change_password(db_session, manager, "Password123", "NewPassword456")
        logger.info("Password changed — expiring instance to force DB reload")

        db_session.expire(manager)
        assert manager.verify_password("NewPassword456") is True
        assert manager.verify_password("Password123") is False
        logger.info("New password verified from DB — old password rejected")
