"""Unit tests for the client service.

Tests are organised by function:
    - create_client

"""

from unittest.mock import MagicMock

import pytest

from exceptions import (
    ClientNotFoundError,
    DuplicateEmailError,
    PermissionDeniedError,
    ValidationError,
)
from services.client_service import (
    create_client,
    get_client_by_id,
    get_clients_for_user,
    update_client,
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

    # ---------------------------
    # Shared Permissions Checks for Write Operations
    # ---------------------------

    @pytest.mark.parametrize(
        "fn,extra_kwargs",
        [
            (
                create_client,
                {
                    "first_name": "Marie",
                    "last_name": "Curie",
                    "email": "marie.curie@example.com",
                },
            ),
            (update_client, {"client": None}),
        ],
    )
    def test_non_commercial_caller_raises_on_write(
        self, management_user, fn, extra_kwargs
    ):
        """Non-Commercial caller raises PermissionDeniedError on any write."""
        session = MagicMock()
        if fn == update_client:
            extra_kwargs["client"] = MagicMock(commercial_id=1)

        with pytest.raises(PermissionDeniedError):
            fn(session=session, current_user=management_user, **extra_kwargs)

    # ---------------------------
    # Shared validation — email
    # ---------------------------

    @pytest.mark.parametrize(
        "fn,extra_kwargs",
        [
            (create_client, {"first_name": "Marie", "last_name": "Curie"}),
            (update_client, {"client": None}),  # client set in test body
        ],
    )
    def test_invalid_email_raises_on_write(
        self, commercial_user, mock_session_empty, fn, extra_kwargs
    ):
        """Invalid email raises ValidationError on both create and update."""
        if fn == update_client:
            extra_kwargs["client"] = MagicMock(commercial_id=commercial_user.id)

        with pytest.raises(ValidationError):
            fn(
                session=mock_session_empty,
                current_user=commercial_user,
                email="notanemail",
                **extra_kwargs,
            )


class TestReadClientService:
    """Tests for client read operations — scoped by role."""

    # ---------------------------
    # get_clients_for_user — happy path
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

    # ---------------------------
    # get_client_by_id — happy path
    # ---------------------------

    @pytest.mark.parametrize(
        "role_fixture,client_kwargs,scalars_clients",
        [
            ("management_user", {"id": 1}, None),
            ("commercial_user", {"id": 1}, None),  # commercial_id set in test
            ("support_user", {"id": 1}, "linked"),
        ],
    )
    def test_get_client_by_id_returns_client(
        self, request, make_client, role_fixture, client_kwargs, scalars_clients
    ):
        """Each role can retrieve a client within their scope."""
        user = request.getfixturevalue(role_fixture)

        if role_fixture == "commercial_user":
            client_kwargs["commercial_id"] = user.id

        test_client = make_client(**client_kwargs)
        session = MagicMock()
        session.get.return_value = test_client

        if scalars_clients == "linked":
            session.scalars.return_value.all.return_value = [test_client]

        result = get_client_by_id(
            session=session,
            current_user=user,
            client_id=1,
        )

        assert result == test_client

    # ---------------------------
    # get_client_by_id - sad path
    # ---------------------------

    def test_commercial_retrieves_other_client_raises(
        self, commercial_user, make_client
    ):
        """Commercial retrieving anothers' client raises ClientNotFoundError."""
        test_client = make_client(id=1, commercial_id=999)

        session = MagicMock()
        session.get.return_value = test_client

        with pytest.raises(ClientNotFoundError):
            get_client_by_id(
                session=session,
                current_user=commercial_user,
                client_id=1,
            )

    def test_support_retrieves_unlinked_client_raises(self, support_user, make_client):
        """Support retrieving a client not linked to them raises ClientNotFoundError."""
        test_client = make_client(id=1)
        other_client = make_client(id=2)

        session = MagicMock()
        session.get.return_value = test_client
        # Support only has access to other_client, not client id=1
        session.scalars.return_value.all.return_value = [other_client]

        with pytest.raises(ClientNotFoundError):
            get_client_by_id(
                session=session,
                current_user=support_user,
                client_id=1,
            )
