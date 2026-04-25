"""Unit tests for the client service.

Tests are organised by function:
    - create_client

"""

from unittest.mock import MagicMock

import pytest

from services.client_service import (
    create_client,
    get_all_clients,
    get_client_by_id,
    get_clients_for_user,
    update_client,
)
from utils.exceptions import (
    ClientNotFoundError,
    DuplicateEmailError,
    PermissionDeniedError,
    ValidationError,
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
    # get_client_by_id — happy path
    # ---------------------------

    def test_get_client_by_id_returns_client_for_any_role(self, request, make_client):
        """Any role can retrieve any client by ID."""
        for fixture in ("management_user", "commercial_user", "support_user"):
            user = request.getfixturevalue(fixture)
            client = make_client(id=1, commercial_id=999)  # deliberately not theirs

            session = MagicMock()
            session.get.return_value = client

            result = get_client_by_id(session=session, current_user=user, client_id=1)
            assert result == client

    def test_get_client_by_id_not_found_raises(self, management_user):
        """Returns ClientNotFoundError when client does not exist."""
        session = MagicMock()
        session.get.return_value = None

        with pytest.raises(ClientNotFoundError):
            get_client_by_id(
                session=session, current_user=management_user, client_id=999
            )

    def test_returns_all_clients_for_any_role(self, request, make_client):
        """All roles receive all clients."""
        for fixture in ("management_user", "commercial_user", "support_user"):
            user = request.getfixturevalue(fixture)
            clients = [make_client(id=i, commercial_id=999) for i in range(3)]

            session = MagicMock()
            session.scalars.return_value.all.return_value = clients

            result = get_all_clients(session=session, current_user=user)
            assert len(result) == 3

    def test_returns_empty_list_when_no_clients(self, management_user):
        """Returns empty list when no clients exist."""
        session = MagicMock()
        session.scalars.return_value.all.return_value = []

        result = get_all_clients(session=session, current_user=management_user)
        assert result == []
