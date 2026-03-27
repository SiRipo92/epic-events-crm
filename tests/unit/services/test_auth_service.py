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

from config import settings
from services.auth_service import _generate_token

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
