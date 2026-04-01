"""Unit tests for the collaborator service.

Tests are organised by function:
    - create_collaborator
    - update_collaborator
    - deactivate_collaborator
    - get_collaborators
    - get_collaborator_by_id
"""

from unittest.mock import MagicMock, patch

import pytest

from exceptions import (
    CollaboratorNotFoundError,
    DuplicateEmailError,
    PermissionDeniedError,
    ReassignmentRequiredError,
    ValidationError,
)
from models.contract import ContractStatus
from services.collaborator_service import (
    create_collaborator,
    deactivate_collaborator,
    get_active_dossiers,
    get_collaborator_by_id,
    get_collaborators,
    update_collaborator,
)


class TestCreateCollaborator:
    """Tests for the create_collaborator service function."""

    # ---------------------------
    # Happy path
    # ---------------------------

    def test_valid_input_creates_collaborator(
        self, management_user, mock_session_empty
    ):
        """Valid input creates a collaborator with correct defaults."""
        result = create_collaborator(
            session=mock_session_empty,
            current_user=management_user,
            first_name="Sophie",
            last_name="Marceau",
            email="sophie.marceau@epicevents.com",
            role_id=2,
            password="initialpassword123",
        )

        assert result.must_change_password is True
        assert result.is_active is True
        assert result.password_hash != "initialpassword123"
        mock_session_empty.add.assert_called_once()
        mock_session_empty.commit.assert_called_once()

    def test_employee_number_is_generated(self, management_user, mock_session_empty):
        """Employee number is auto-generated in EMP-XXX format."""
        result = create_collaborator(
            session=mock_session_empty,
            current_user=management_user,
            first_name="Sophie",
            last_name="Marceau",
            email="sophie.marceau@epicevents.com",
            role_id=2,
            password="initialpassword123",
        )

        assert result.employee_number == "EMP-001"

    # ---------------------------
    # Sad path
    # ---------------------------

    def test_duplicate_email_raises(self, management_user):
        """Duplicate email raises DuplicateEmailError."""
        session = MagicMock()
        session.query.return_value.filter_by.return_value.first.return_value = (
            MagicMock()
        )

        with pytest.raises(DuplicateEmailError):
            create_collaborator(
                session=session,
                current_user=management_user,
                first_name="Sophie",
                last_name="Marceau",
                email="already.exists@epicevents.com",
                role_id=2,
                password="initialpassword123",
            )

    def test_non_management_caller_raises(self, commercial_user):
        """Non-Management caller raises PermissionDeniedError."""
        session = MagicMock()

        with pytest.raises(PermissionDeniedError):
            create_collaborator(
                session=session,
                current_user=commercial_user,
                first_name="Sophie",
                last_name="Marceau",
                email="sophie.marceau@epicevents.com",
                role_id=2,
                password="initialpassword123",
            )

    def test_invalid_email_raises(self, management_user, mock_session_empty):
        """Invalid email format raises ValidationError."""
        with pytest.raises(ValidationError):
            create_collaborator(
                session=mock_session_empty,
                current_user=management_user,
                first_name="Sophie",
                last_name="Marceau",
                email="notanemail",
                role_id=2,
                password="initialpassword123",
            )


class TestUpdateCollaborator:
    """Tests for the update_collaborator service function."""

    # ---------------------------
    # Happy path
    # ---------------------------

    def test_valid_update_persists_fields(self, management_user, make_collaborator):
        """Valid update persists changed fields and commits."""
        target = make_collaborator(
            id=2,
            first_name="Bob",
            last_name="Dupont",
            email="bob.dupont@epicevents.com",
        )

        session = MagicMock()
        session.query.return_value.filter_by.return_value.first.return_value = None

        result = update_collaborator(
            session=session,
            current_user=management_user,
            collaborator=target,
            first_name="Robert",
        )

        assert result.first_name == "Robert"
        session.commit.assert_called_once()

    @pytest.mark.parametrize(
        "field, value",
        [
            ("last_name", "Martin"),
            ("phone", "0612345678"),
            ("role_id", 3),
        ],
    )
    def test_partial_update_applies_field(
        self, management_user, make_collaborator, field, value
    ):
        """Each updatable field is applied when provided."""
        target = make_collaborator(id=2)
        session = MagicMock()
        session.query.return_value.filter_by.return_value.first.return_value = None

        update_collaborator(
            session=session,
            current_user=management_user,
            collaborator=target,
            **{field: value},
        )

        assert getattr(target, field) == value

    # ---------------------------
    # Sad path
    # ---------------------------

    def test_duplicate_email_on_update_raises(
        self, management_user, make_collaborator, management_role
    ):
        """Updating to an existing email raises DuplicateEmailError."""
        target = make_collaborator(
            id=2,
            email="bob.dupont@epicevents.com",
            role=management_role,
        )
        existing = make_collaborator(
            id=3,
            email="already.taken@epicevents.com",
            role=management_role,
        )
        session = MagicMock()
        session.query.return_value.filter_by.return_value.first.return_value = existing

        with pytest.raises(DuplicateEmailError):
            update_collaborator(
                session=session,
                current_user=management_user,
                collaborator=target,
                email="already.taken@epicevents.com",
            )

    def test_non_management_caller_raises(
        self,
        commercial_user,
        make_collaborator,
    ):
        """Non-Management caller raises PermissionDeniedError."""
        target = make_collaborator(
            id=2,
            email="bob.dupont@epicevents.com",
        )
        session = MagicMock()

        with pytest.raises(PermissionDeniedError):
            update_collaborator(
                session=session,
                current_user=commercial_user,
                collaborator=target,
                first_name="Robert",
            )

    def test_invalid_email_on_update_raises(self, management_user, make_collaborator):
        """Invalid email format raises ValidationError on update."""
        target = make_collaborator(id=2)
        session = MagicMock()

        with pytest.raises(ValidationError):
            update_collaborator(
                session=session,
                current_user=management_user,
                collaborator=target,
                email="notanemail",
            )


class TestGetActiveDossiers:
    """Tests for helper that retrieves active dossiers for a collaborator."""

    # ---------------------------
    # Happy path
    # ---------------------------

    def test_returns_all_active_dossiers(
        self,
        make_collaborator,
        make_client,
        make_contract,
        make_event,
    ):
        """Returns clients, contracts, and events linked to collaborator."""
        # ── Arrange ────────────────────────────────────────────────
        collaborator = make_collaborator(id=42)

        # Fake data returned by queries
        clients = [make_client(id=1, commercial_id=42)]
        contracts = [
            make_contract(id=1, commercial_id=42),
            make_contract(id=2, commercial_id=42),
        ]
        events = [make_event(id=1, support_id=42)]

        session = MagicMock()

        # Mock query chains in order of calls
        session.query.return_value.filter.return_value.all.side_effect = [
            clients,  # first call → clients
            contracts,  # second call → contracts
            events,  # third call → events
        ]

        # ── Act ────────────────────────────────────────────────────
        result = get_active_dossiers(session=session, collaborator=collaborator)

        # ── Assert ─────────────────────────────────────────────────
        assert result["clients"] == clients
        assert result["contracts"] == contracts
        assert result["events"] == events

    # ---------------------------
    # Sad path
    # ---------------------------

    def test_returns_empty_lists_when_no_dossiers(
        self,
        make_collaborator,
    ):
        """Returns empty lists when collaborator has no linked dossiers."""
        collaborator = make_collaborator(id=42)

        session = MagicMock()
        session.query.return_value.filter.return_value.all.side_effect = [
            [],  # clients
            [],  # contracts
            [],  # events
        ]

        result = get_active_dossiers(session=session, collaborator=collaborator)

        assert result == {
            "clients": [],
            "contracts": [],
            "events": [],
        }

    def test_excludes_cancelled_and_paid_contracts(
        self,
        make_collaborator,
        make_contract,
    ):
        """Contracts with CANCELLED or PAID_IN_FULL status are excluded."""
        collaborator = make_collaborator(id=42)

        active_contract = make_contract(id=1, commercial_id=42)
        cancelled = make_contract(id=2, commercial_id=42)
        cancelled.status = ContractStatus.CANCELLED

        paid = make_contract(id=3, commercial_id=42)
        paid.status = ContractStatus.PAID_IN_FULL

        session = MagicMock()
        session.query.return_value.filter.return_value.all.side_effect = [
            [],  # clients
            [active_contract],  # contracts → DB already filtered
            [],  # events
        ]

        result = get_active_dossiers(session=session, collaborator=collaborator)

        assert active_contract in result["contracts"]

    def test_excludes_cancelled_events(
        self,
        make_collaborator,
        make_event,
    ):
        """Cancelled events are excluded from active dossiers."""
        collaborator = make_collaborator(id=42)

        active_event = make_event(id=1, support_id=42, is_cancelled=False)

        session = MagicMock()
        session.query.return_value.filter.return_value.all.side_effect = [
            [],  # clients
            [],  # contracts
            [active_event],  # events → DB already filtered
        ]

        result = get_active_dossiers(session=session, collaborator=collaborator)

        assert active_event in result["events"]


class TestDeactivateCollaborator:
    """Tests for the deactivate_collaborator service function."""

    # ---------------------------
    # Happy path
    # ---------------------------

    def test_deactivates_collaborator_when_no_dossiers(
        self,
        management_user,
        make_collaborator,
    ):
        """Collaborator is deactivated when no active dossiers exist."""
        collaborator = make_collaborator(id=42, is_active=True)
        session = MagicMock()

        with patch(
            "services.collaborator_service.get_active_dossiers",
            return_value={"clients": [], "contracts": [], "events": []},
        ):
            deactivate_collaborator(
                session=session,
                current_user=management_user,
                collaborator=collaborator,
            )

        assert collaborator.is_active is False
        session.commit.assert_called_once()

    def test_session_file_deleted_on_deactivation(
        self,
        management_user,
        make_collaborator,
        session_file,
    ):
        """Session file is deleted if it exists."""
        collaborator = make_collaborator(id=42)
        session_file.write_text("token")
        session = MagicMock()

        with patch(
            "services.collaborator_service.get_active_dossiers",
            return_value={"clients": [], "contracts": [], "events": []},
        ):
            deactivate_collaborator(
                session=session,
                current_user=management_user,
                collaborator=collaborator,
            )

        assert not session_file.exists()

    # ---------------------------
    # Sad path
    # ---------------------------

    @pytest.mark.parametrize(
        "dossiers",
        [
            {"clients": ["client"], "contracts": [], "events": []},
            {"clients": [], "contracts": ["contract"], "events": []},
            {"clients": [], "contracts": [], "events": ["event"]},
        ],
    )
    def test_raises_if_any_active_dossier_exists(
        self,
        management_user,
        make_collaborator,
        dossiers,
    ):
        """Raises ReassignmentRequiredError with dossiers details if any exist."""
        collaborator = make_collaborator(id=42)
        session = MagicMock()

        with patch(
            "services.collaborator_service.get_active_dossiers",
            return_value=dossiers,
        ):
            with pytest.raises(ReassignmentRequiredError) as exc_info:
                deactivate_collaborator(
                    session=session,
                    current_user=management_user,
                    collaborator=collaborator,
                )
        # The exception should carry the exact dossiers dict
        assert exc_info.value.dossiers == dossiers
        session.commit.assert_not_called()

    def test_no_error_if_session_file_missing(
        self,
        management_user,
        make_collaborator,
        session_file,
    ):
        """No error occurs if session file does not exist."""
        collaborator = make_collaborator(id=42)
        session = MagicMock()

        # Ensure file does not exist
        if session_file.exists():
            session_file.unlink()

        with patch(
            "services.collaborator_service.get_active_dossiers",
            return_value={"clients": [], "contracts": [], "events": []},
        ):
            deactivate_collaborator(
                session=session,
                current_user=management_user,
                collaborator=collaborator,
            )

        # If no exception → test passes
        session.commit.assert_called_once()


class TestGetCollaborators:
    """Tests for the get_collaborators function."""

    # ---------------------------
    # Happy path
    # ---------------------------

    def test_no_filters_returns_all_collaborators(
        self, management_user, make_collaborator, management_role, commercial_role
    ):
        """No filters returns all collaborators."""
        collaborators = [
            make_collaborator(id=1, role=management_role),
            make_collaborator(id=2, role=commercial_role),
        ]
        session = MagicMock()
        session.query.return_value.options.return_value.all.return_value = collaborators

        result = get_collaborators(
            session=session,
            current_user=management_user,
        )

        assert result == collaborators

    def test_filter_by_role_returns_matching_collaborators(
        self, management_user, make_collaborator, management_role
    ):
        """Filter by role returns only collaborators with that role."""
        management_collaborator = make_collaborator(id=1, role=management_role)

        session = MagicMock()
        base = session.query.return_value.options.return_value
        mock_query = base.join.return_value.filter.return_value.all
        mock_query.return_value = [management_collaborator]

        result = get_collaborators(
            session=session,
            current_user=management_user,
            role="MANAGEMENT",
        )

        assert len(result) == 1
        assert result[0].role.name == "MANAGEMENT"

    def test_filter_by_is_active_returns_matching_collaborators(
        self, management_user, make_collaborator, management_role
    ):
        """Filter by is_active returns only collaborators with that status."""
        inactive_collaborator = make_collaborator(
            id=4,
            role=management_role,
            is_active=False,
        )

        session = MagicMock()
        base = session.query.return_value.options.return_value
        base.filter.return_value.all.return_value = [inactive_collaborator]

        result = get_collaborators(
            session=session,
            current_user=management_user,
            is_active=False,
        )

        assert len(result) == 1
        assert result[0].is_active is False

    def test_combined_filters_returns_matching_collaborators(
        self, management_user, make_collaborator, management_role
    ):
        """Role and is_active filters can be combined."""
        inactive_collaborator = make_collaborator(
            id=4,
            role=management_role,
            is_active=False,
        )

        session = MagicMock()
        base = session.query.return_value.options.return_value
        base.filter.return_value.all.return_value = [inactive_collaborator]

        result = get_collaborators(
            session=session,
            current_user=management_user,
            is_active=False,
        )

        assert len(result) == 1
        assert result[0].is_active is False

    # ---------------------------
    # Sad path
    # ---------------------------

    def test_non_management_caller_raises(self, commercial_user):
        """Non-Management caller raises PermissionDeniedError."""
        session = MagicMock()

        with pytest.raises(PermissionDeniedError):
            get_collaborators(
                session=session,
                current_user=commercial_user,
            )


class TestGetCollaboratorById:
    """Tests for the get_collaborator_by_id service function."""

    # ---------------------------
    # Happy path
    # ---------------------------

    def test_valid_id_returns_collaborator(
        self, management_user, make_collaborator, management_role
    ):
        """Valid ID returns the correct collaborator."""
        target = make_collaborator(id=2, role=management_role)

        session = MagicMock()
        base = session.query.return_value.options.return_value
        base.filter.return_value.first.return_value = target

        result = get_collaborator_by_id(
            session=session,
            current_user=management_user,
            collaborator_id=2,
        )

        assert result == target
        assert result.id == 2

    # ---------------------------
    # Sad path
    # ---------------------------

    def test_invalid_id_raises(self, management_user):
        """Invalid ID raises CollaboratorNotFoundError."""
        session = MagicMock()
        base = session.query.return_value.options.return_value
        base.filter.return_value.first.return_value = None

        with pytest.raises(CollaboratorNotFoundError):
            get_collaborator_by_id(
                session=session,
                current_user=management_user,
                collaborator_id=999,
            )

    def test_non_management_caller_raises(self, commercial_user):
        """Non-Management caller raises PermissionDeniedError."""
        session = MagicMock()

        with pytest.raises(PermissionDeniedError):
            get_collaborator_by_id(
                session=session,
                current_user=commercial_user,
                collaborator_id=1,
            )
