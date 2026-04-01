"""Unit tests for the client service.

Tests are organised by function:
    - create_client

"""

from unittest.mock import MagicMock

import pytest

from exceptions import (
    DuplicateEmailError,
    PermissionDeniedError,
    ValidationError,
)
from services.client_service import create_client, get_clients_for_user, update_client


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

    def test_create_client_duplicate_email_raises(self, commercial_user):
        """Duplicate email raises DuplicateEmailError."""
        session = MagicMock()
        session.query.return_value.filter_by.return_value.first.return_value = (
            MagicMock()
        )

        with pytest.raises(DuplicateEmailError):
            create_client(
                session=session,
                current_user=commercial_user,
                first_name="Marie",
                last_name="Curie",
                email="already.exists@example.com",
            )

    def test_create_client_invalid_email_raises(
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

    def test_create_client_non_commercial_caller_raises(self, management_user):
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

    # ---------------------------
    # update_client — happy path
    # ---------------------------

    def test_update_client_owner_can_update(self, commercial_user, make_client):
        """Owner can update their own client."""
        test_client = make_client(
            id=1,
            commercial_id=commercial_user.id,
        )
        session = MagicMock()
        session.query.return_value.filter_by.return_value.first.return_value = None

        result = update_client(
            session=session,
            current_user=commercial_user,
            client=test_client,
            first_name="Updated",
        )

        assert result.first_name == "Updated"
        session.commit.assert_called_once()

    @pytest.mark.parametrize(
        "field, value",
        [
            ("last_name", "Curie"),
            ("phone", "0612345678"),
            ("company_name", "Lab Corp"),
        ],
    )
    def test_update_client_partial_update_applies_field(
        self, commercial_user, make_client, field, value
    ):
        """Each updatable field is applied when provided."""
        test_client = make_client(id=1, commercial_id=commercial_user.id)
        session = MagicMock()
        session.query.return_value.filter_by.return_value.first.return_value = None

        update_client(
            session=session,
            current_user=commercial_user,
            client=test_client,
            **{field: value},
        )

        assert getattr(test_client, field) == value

    # ---------------------------
    # update_client — sad path
    # ---------------------------

    def test_update_client_non_owner_raises(self, commercial_user, make_client):
        """Commercial updating another's client raises PermissionDeniedError."""
        test_client = make_client(
            id=1,
            commercial_id=999,  # owned by a different commercial
        )
        session = MagicMock()

        with pytest.raises(PermissionDeniedError):
            update_client(
                session=session,
                current_user=commercial_user,
                client=test_client,
                first_name="Hacked",
            )

    def test_update_client_duplicate_email_raises(self, commercial_user, make_client):
        """Updating to an existing email raises DuplicateEmailError."""
        test_client = make_client(
            id=1,
            commercial_id=commercial_user.id,
        )
        existing = make_client(
            id=2,
            email="already.taken@example.com",
            commercial_id=commercial_user.id,
        )
        session = MagicMock()
        session.query.return_value.filter_by.return_value.first.return_value = existing

        with pytest.raises(DuplicateEmailError):
            update_client(
                session=session,
                current_user=commercial_user,
                client=test_client,
                email="already.taken@example.com",
            )

    def test_update_client_invalid_email_raises(self, commercial_user, make_client):
        """Invalid email format raises ValidationError on update."""
        test_client = make_client(
            id=1,
            commercial_id=commercial_user.id,
        )
        session = MagicMock()

        with pytest.raises(ValidationError):
            update_client(
                session=session,
                current_user=commercial_user,
                client=test_client,
                email="notanemail",
            )

    def test_update_client_non_commercial_caller_raises(
        self, management_user, make_client
    ):
        """Non-Commercial caller raises PermissionDeniedError."""
        test_client = make_client(id=1, commercial_id=1)
        session = MagicMock()

        with pytest.raises(PermissionDeniedError):
            update_client(
                session=session,
                current_user=management_user,
                client=test_client,
                first_name="Hacked",
            )


class TestReadClientService:
    """Tests for client read operations — scoped by role."""

    # ---------------------------
    # Read clients - happy path
    # ---------------------------

    def test_management_sees_all_clients(self, management_user):
        """Management user gets all clients."""
        session = MagicMock()
        session.scalars.return_value.all.return_value = [MagicMock(), MagicMock()]

        result = get_clients_for_user(
            session=session,
            current_user=management_user,
        )

        assert len(result) == 2
        session.scalars.assert_called_once()

    def test_commercial_sees_only_own_clients(self, commercial_user, make_client):
        """Commercial user gets only their own clients."""
        own_client = make_client(id=1, commercial_id=commercial_user.id)

        session = MagicMock()
        session.scalars.return_value.all.return_value = [own_client]

        result = get_clients_for_user(
            session=session,
            current_user=commercial_user,
        )

        assert len(result) == 1
        assert result[0].commercial_id == commercial_user.id

    def test_support_sees_only_clients_linked_to_assigned_events(
        self, support_user, make_client
    ):
        """Support user gets only clients linked to their assigned events."""
        linked_client = make_client(id=1)

        session = MagicMock()
        session.scalars.return_value.all.return_value = [linked_client]

        result = get_clients_for_user(
            session=session,
            current_user=support_user,
        )

        assert len(result) == 1
