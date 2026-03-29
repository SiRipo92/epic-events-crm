"""Unit tests for the authentication service.

Tests are organised by function:
    - _generate_token
    - _decode_token
    - change_password
    - _get_session_path
    - _write_session_file
    - _read_session_file
    - login
    - logout
    - get_session_user
"""

import datetime as dt
from datetime import timedelta, timezone
from unittest.mock import MagicMock, patch

import jwt
import pytest

from config import settings
from exceptions import AuthenticationError, ValidationError
from services.auth_service import (
    _decode_token,
    _generate_token,
    _get_session_path,
    _read_session_file,
    _write_session_file,
    change_password,
    get_session_user,
    login,
    logout,
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

    def test_must_change_password_cleared(self, make_collaborator, management_role):
        """Successful change sets must_change_password to False."""
        c = make_collaborator(role=management_role, must_change_password=True)
        c.set_password("oldpassword")
        session = MagicMock()

        change_password(session, c, "oldpassword", "newpassword123")

        assert c.must_change_password is False

    # ---------------------------
    # Sad path
    # ---------------------------

    def test_wrong_current_password_raises(self, make_collaborator, management_role):
        """Wrong current password raises AuthenticationError."""
        c = make_collaborator(role=management_role)
        c.set_password("oldpassword")
        session = MagicMock()

        with pytest.raises(AuthenticationError):
            change_password(session, c, "wrongpassword", "newpassword123")

    def test_same_password_raises(self, make_collaborator, management_role):
        """New password identical to current raises ValidationError."""
        c = make_collaborator(role=management_role)
        c.set_password("samepassword")
        session = MagicMock()

        with pytest.raises(ValidationError):
            change_password(session, c, "samepassword", "samepassword")


class TestGetSessionPath:
    """Tests for session path resolution."""

    def test_returns_settings_session_file(self, session_file):
        """Returns the path defined in settings."""
        assert _get_session_path() == settings.session_file


class TestWriteSessionFile:
    """Tests for session file writing."""

    # ---------------------------
    # Happy path
    # ---------------------------

    def test_session_file_is_created(self, session_file):
        """Token is written to the session file."""
        _write_session_file("test.token.value")
        assert session_file.exists()

    def test_session_file_contains_token(self, session_file):
        """Session file content matches the written token."""
        _write_session_file("test.token.value")
        assert session_file.read_text() == "test.token.value"

    def test_session_file_permissions_are_restricted(self, session_file):
        """Session file should have chmod 600 permissions."""
        _write_session_file("test.token.value")
        file_mode = session_file.stat().st_mode & 0o777
        assert file_mode == 0o600


class TestLogin:
    """Tests for the login service function."""

    # ---------------------------
    # Happy path
    # ---------------------------

    def test_valid_credentials_returns_collaborator(
        self, make_collaborator, management_role
    ):
        """Valid email and password returns the collaborator."""
        c = make_collaborator(
            role=management_role,
            is_active=True,
            must_change_password=False,
        )
        c.set_password("correctpassword")

        session = MagicMock()
        session.query.return_value.filter_by.return_value.first.return_value = c

        with patch("services.auth_service._write_session_file"):
            result = login(session, c.email, "correctpassword")

        assert result == c

    # ---------------------------
    # Sad path
    # ---------------------------

    @pytest.mark.parametrize(
        "setup,expected_match",
        [
            ("wrong_password", None),
            ("unknown_email", None),
            ("inactive_account", "deactivated"),
        ],
    )
    def test_invalid_login_raises(
        self, setup, expected_match, make_collaborator, management_role
    ):
        """Invalid credentials or inactive account raises AuthenticationError."""
        session = MagicMock()

        if setup == "wrong_password":
            c = make_collaborator(role=management_role, is_active=True)
            c.set_password("correctpassword")
            session.query.return_value.filter_by.return_value.first.return_value = c
            password = "wrongpassword"
            email = c.email
        elif setup == "unknown_email":
            session.query.return_value.filter_by.return_value.first.return_value = None
            email = "unknown@example.com"
            password = "anypassword"
        else:  # inactive_account
            c = make_collaborator(role=management_role, is_active=False)
            c.set_password("correctpassword")
            session.query.return_value.filter_by.return_value.first.return_value = c
            email = c.email
            password = "correctpassword"

        with patch("services.auth_service._write_session_file"):
            if expected_match:
                with pytest.raises(AuthenticationError, match=expected_match):
                    login(session, email, password)
            else:
                with pytest.raises(AuthenticationError):
                    login(session, email, password)


class TestLogout:
    """Tests for the logout service function."""

    # ---------------------------
    # Happy path
    # ---------------------------

    def test_logout_deletes_session_file(self, session_file):
        """Logout should delete the session file if it exists."""
        session_file.write_text("fake-token")
        assert session_file.exists()
        logout()
        assert not session_file.exists()

    # ---------------------------
    # Sad path
    # ---------------------------

    def test_logout_no_error_if_no_session(self, session_file):
        """Logout should not raise if no session file exists."""
        logout()
        assert not session_file.exists()


class TestReadSessionFile:
    """Tests for the reading session file function."""

    # ---------------------------
    # Happy path
    # ---------------------------

    def test_returns_token_if_file_exists(self, session_file):
        """Should return the token stored in the session file."""
        session_file.write_text("test.token.value")
        result = _read_session_file()
        assert result == "test.token.value"

    def test_strips_whitespace_from_token(self, session_file):
        """Should strip whitespace and newlines from token."""
        session_file.write_text("  test.token.value\n")
        result = _read_session_file()
        assert result == "test.token.value"

    # ---------------------------
    # Sad path
    # ---------------------------

    def test_returns_none_if_file_does_not_exist(self, session_file):
        """Should return None when session file is missing."""
        result = _read_session_file()
        assert result is None


class TestGetSessionUser:
    """Tests for retrieving the current session user."""

    class _ActiveCollaborator:
        is_active = True

    class _InactiveCollaborator:
        is_active = False

    class _SessionReturning:
        def __init__(self, obj):
            self._obj = obj

        def get(self, model, user_id):
            return self._obj

    class _SessionReturningNone:
        def get(self, model, user_id):
            return None

    # ---------------------------
    # Happy path
    # ---------------------------

    def test_returns_collaborator_if_token_valid(self, mock_authenticated_session):
        """Return collaborator when token and user are valid."""
        result = get_session_user(
            session=self._SessionReturning(self._ActiveCollaborator())
        )
        assert isinstance(result, self._ActiveCollaborator)

    # ---------------------------
    # Sad path
    # ---------------------------

    def test_returns_none_if_no_token(self, mock_no_token):
        """Return None when no session token exists."""
        result = get_session_user(session=None)
        assert result is None

    def test_raises_if_user_not_found(self, mock_authenticated_session, mocker):
        """Delete session and raise if user does not exist in DB."""
        mock_delete = mocker.patch("services.auth_service._delete_session_file")

        with pytest.raises(AuthenticationError):
            get_session_user(session=self._SessionReturningNone())

        mock_delete.assert_called_once()

    def test_raises_if_user_inactive(self, mock_authenticated_session, mocker):
        """Delete session and raise if user is deactivated."""
        mock_delete = mocker.patch("services.auth_service._delete_session_file")

        with pytest.raises(AuthenticationError):
            get_session_user(
                session=self._SessionReturning(self._InactiveCollaborator())
            )

        mock_delete.assert_called_once()

    def test_raises_if_token_invalid(self, monkeypatch):
        """Raise AuthenticationError if token cannot be decoded."""
        monkeypatch.setattr(
            "services.auth_service._read_session_file",
            lambda: "some.token.value",
        )

        def fake_decode(token):
            raise AuthenticationError("Invalid token")

        monkeypatch.setattr("services.auth_service._decode_token", fake_decode)

        with pytest.raises(AuthenticationError):
            get_session_user(session=None)
