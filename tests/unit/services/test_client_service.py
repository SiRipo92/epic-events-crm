"""Unit tests for the client service.

Tests are organised by function:
    - create_client

"""

from unittest.mock import MagicMock

import pytest

from exceptions import (
    PermissionDeniedError,
    DuplicateEmailError,
    ValidationError,
)
from services.client_service import (
    create_client,
)

class TestWriteClientService:
    """Tests for client write operations — create and update."""

    # ---------------------------
    # create_client — happy path
    # ---------------------------

    def test_create_client_sets_commercial_id_from_current_user(
            self, commercial_user, mock_session_empty
    ):
        """Client is created with commercial_id set from current_user.id."""
        result = create_client(
            session=mock_session_empty,
            current_user=commercial_user,
            first_name="Marie",
            last_name="Curie",
            email="marie.curie@example.com",
        )

        assert result.commercial_id == commercial_user.id
        assert result.first_name == "Marie"
        assert result.last_name == "Curie"
        mock_session_empty.add.assert_called_once()
        mock_session_empty.commit.assert_called_once()


    # ---------------------------
    # create_client — sad path
    # ---------------------------

    def test_client_invalid_email_raises(
            self, commercial_user, mock_session_empty
    ):
        """Invalid email format raises ValidationError."""
        with pytest.raises(ValidationError):
            create_client(
                session=mock_session_empty,
                current_user=commercial_user,
                first_name="Marie",
                last_name="Curie",
                email="notanemail",
            )

    def test_create_client_duplicate_email_raises(
            self, commercial_user
    ):
        """Duplicate email raises DuplicateEmailError."""
        session = MagicMock()
        session.query.return_value.filter_by.return_value.first.return_value = MagicMock()

        with pytest.raises(DuplicateEmailError):
            create_client(
                session=session,
                current_user=commercial_user,
                first_name="Marie",
                last_name="Curie",
                email="already.exists@example.com",
            )

    def test_create_client_non_commercial_caller_raises(
            self, management_user
    ):
        """Non-Commercial caller raises PermissionDeniedError."""
        session = MagicMock()

        with pytest.raises(PermissionDeniedError):
            create_client(
                session=session,
                current_user=management_user,
                first_name="Marie",
                last_name="Curie",
                email="marie.curie@example.com",
            )

    def test_create_client_commercial_id_cannot_be_overridden(
            self, commercial_user, mock_session_empty
    ):
        """commercial_id is always set from current_user.id regardless of input."""
        result = create_client(
            session=mock_session_empty,
            current_user=commercial_user,
            first_name="Marie",
            last_name="Curie",
            email="marie.curie@example.com",
        )

        assert result.commercial_id == commercial_user.id
        assert result.commercial_id != 999
