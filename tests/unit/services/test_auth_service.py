"""Unit tests for the authentication service.

Tests are organised by function:
    - _generate_token
    - _decode_token
    - change_password
    - login (uses mocked DB session)
    - logout
    - get_session_user (uses mocked DB session)
"""

import jwt
import pytest
from datetime import timedelta, timezone
import datetime as dt
from unittest.mock import MagicMock
from pathlib import Path

from config import settings
from exceptions import AuthenticationError, ValidationError
from services.auth_service import (
    _generate_token,
    _decode_token,
    change_password,
    _get_session_path
)

class TestGenerateToken:
    """Tests for JWT token generation."""

    def test_token_contains_user_id(self, management_user):
        """Token payload contains the collaborator's id."""
        token = _generate_token(management_user)
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        assert payload["user_id"] == management_user.id

    def test_token_contains_role(self, management_user):
        """Token payload contains the collaborator's role name."""
        token = _generate_token(management_user)
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        assert payload["role"] == "MANAGEMENT"

    def test_token_has_expiry(self, management_user):
        """Token payload contains an expiry timestamp."""
        token = _generate_token(management_user)
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        assert "exp" in payload


class TestDecodeToken:
    """Tests for JWT token decoding."""

    # ---------------------------
    # Happy path
    # ---------------------------

    def test_valid_token_returns_payload(self, management_user):
        """Valid token decodes to correct payload."""
        token = _generate_token(management_user)
        payload = _decode_token(token)
        assert payload["user_id"] == management_user.id

    # ---------------------------
    # Sad path
    # ---------------------------

    def test_expired_token_raises(self, management_user):
        """Expired token raises AuthenticationError."""
        payload = {
            "user_id": management_user.id,
            "role": "MANAGEMENT",
            "exp": dt.datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jwt.encode(payload, settings.secret_key, algorithm="HS256")

        with pytest.raises(AuthenticationError, match="expired"):
            _decode_token(token)

    def test_invalid_token_raises(self):
        """Tampered or malformed token raises AuthenticationError."""
        with pytest.raises(AuthenticationError, match="Invalid"):
            _decode_token("not.a.valid.token")


class TestChangePassword:
    """Tests for the change_password service function."""

    # ---------------------------
    # Happy path
    # ---------------------------

    def test_correct_current_password_updates_hash(
        self, make_collaborator, management_role
    ):
        """Valid password change updates the stored password hash."""
        c = make_collaborator(role=management_role)
        c.set_password("oldpassword")
        session = MagicMock()

        change_password(session, c, "oldpassword", "newpassword123")

        assert c.verify_password("newpassword123") is True

    def test_must_change_password_cleared(
            self, make_collaborator, management_role
    ):
        """Successful change sets must_change_password to False."""
        c = make_collaborator(role=management_role, must_change_password=True)
        c.set_password("oldpassword")
        session = MagicMock()

        change_password(session, c, "oldpassword", "newpassword123")

        assert c.must_change_password is False

    # ---------------------------
    # Sad path
    # ---------------------------

    def test_wrong_current_password_raises(
            self, make_collaborator, management_role
    ):
        """Wrong current password raises AuthenticationError."""
        c = make_collaborator(role=management_role)
        c.set_password("oldpassword")
        session = MagicMock()

        with pytest.raises(AuthenticationError):
            change_password(session, c, "wrongpassword", "newpassword123")

    def test_same_password_raises(
            self, make_collaborator, management_role
    ):
        """New password identical to current raises ValidationError."""
        c = make_collaborator(role=management_role)
        c.set_password("samepassword")
        session = MagicMock()

        with pytest.raises(ValidationError):
            change_password(session, c, "samepassword", "samepassword")

class TestGetSessionPath:
    """Tests for session path resolution."""

    # ---------------------------
    # Happy path
    # ---------------------------

    def test_returns_path_object(self):
        """Returns a Path instance."""
        result = _get_session_path()
        assert isinstance(result, Path)

    def test_returns_correct_path(self):
        """Returns the path defined in settings."""
        result = _get_session_path()
        assert result == settings.session_file
