"""Integration tests for collaborator_service: deactivate_collaborator.

These tests use a real in-memory SQLite database via the test conftest fixtures.
"""

import pytest
from unittest.mock import patch

from models.collaborator import Collaborator, Role
from models.client import Client, ClientStatus
from models.contract import Contract, ContractStatus
from models.event import Event
from db.session import get_session
from exceptions import ReassignmentRequiredError, PermissionDeniedError
from services.collaborator_service import get_active_dossiers, deactivate_collaborator


# --- Fixtures ---

@pytest.fixture
def management_user():
    """A MANAGEMENT-role collaborator for auth checks."""
    collab = Collaborator(
        id=10,
        first_name="Director",
        last_name="Admin",
        email="director@epicevents.com",
        password_hash="hash",
        role=Role.MANAGEMENT,
        is_active=True,
    )
    return collab


@pytest.fixture
def commercial_user():
    """A COMMERCIAL-role collaborator who should be deactivated."""
    collab = Collaborator(
        id=20,
        first_name="Pierre",
        last_name="Vendeur",
        email="pierre@epicevents.com",
        password_hash="hash",
        role=Role.COMMERCIAL,
        is_active=True,
    )
    return collab


@pytest.fixture
def support_user():
    """A SUPPORT-role collaborator."""
    collab = Collaborator(
        id=30,
        first_name="Sophie",
        last_name="Support",
        email="sophie@epicevents.com",
        password_hash="hash",
        role=Role.SUPPORT,
        is_active=True,
    )
    return collab


@pytest.fixture
def db_with_users(management_user, commercial_user, support_user):
    """Populate the in-memory DB with three collaborators."""
    with get_session() as session:
        session.add_all([management_user, commercial_user, support_user])
        session.commit()
    yield


# --- get_active_dossiers tests ---

class TestGetActiveDossiers:
    """Tests for get_active_dossiers()."""

    def test_no_dossiers_returns_empty_lists(self, db_with_users):
        """Collaborator with no clients/contracts/events returns empty lists."""
        dossiers = get_active_dossiers(collaborator_id=20)
        assert dossiers["clients"] == []
        assert dossiers["contracts"] == []
        assert dossiers["events"] == []

    def test_finds_active_client(self, db_with_users):
        """Detects an active client assigned to the collaborator."""
        with get_session() as session:
            client = Client(
                id=100,
                first_name="Acme",
                last_name="Corp",
                email="acme@corp.com",
                commercial_id=20,
                status=ClientStatus.ACTIVE,
            )
            session.add(client)
            session.commit()

        dossiers = get_active_dossiers(collaborator_id=20)
        assert len(dossiers["clients"]) == 1
        assert dossiers["clients"][0]["email"] == "acme@corp.com"

    def test_ignores_cancelled_contract(self, db_with_users):
        """Cancelled contracts are NOT included in active dossiers."""
        with get_session() as session:
            c = Contract(
                id=200,
                client_id=1,
                commercial_id=20,
                total_amount="5000.00",
                remaining_amount="5000.00",
                status=ContractStatus.CANCELLED,
            )
            session.add(c)
            session.commit()

        dossiers = get_active_dossiers(collaborator_id=20)
        assert dossiers["contracts"] == []

    def test_ignores_paid_in_full_contract(self, db_with_users):
        """PAID_IN_FULL contracts are NOT included in active dossiers."""
        with get_session() as session:
            c = Contract(
                id=201,
                client_id=1,
                commercial_id=20,
                total_amount="3000.00",
                remaining_amount="0.00",
                status=ContractStatus.PAID_IN_FULL,
            )
            session.add(c)
            session.commit()

        dossiers = get_active_dossiers(collaborator_id=20)
        assert dossiers["contracts"] == []

    def test_includes_open_contract(self, db_with_users):
        """Non-cancelled, non-paid contracts ARE included."""
        with get_session() as session:
            c = Contract(
                id=202,
                client_id=1,
                commercial_id=20,
                total_amount="8000.00",
                remaining_amount="4000.00",
                status=ContractStatus.SIGNED,
            )
            session.add(c)
            session.commit()

        dossiers = get_active_dossiers(collaborator_id=20)
        assert len(dossiers["contracts"]) == 1

    def test_ignores_cancelled_event(self, db_with_users):
        """Cancelled events are NOT included in active dossiers."""
        with get_session() as session:
            e = Event(
                id=300,
                contract_id=1,
                title="Cancelled Gala",
                start_date=None,
                end_date=None,
                support_id=20,
                is_cancelled=True,
            )
            session.add(e)
            session.commit()

        dossiers = get_active_dossiers(collaborator_id=20)
        assert dossiers["events"] == []

    def test_includes_active_event(self, db_with_users):
        """Non-cancelled events ARE included."""
        with get_session() as session:
            e = Event(
                id=301,
                contract_id=1,
                title="Tech Conference",
                start_date=None,
                end_date=None,
                support_id=20,
                is_cancelled=False,
            )
            session.add(e)
            session.commit()

        dossiers = get_active_dossiers(collaborator_id=20)
        assert len(dossiers["events"]) == 1


# --- deactivate_collaborator tests ---

class TestDeactivateCollaborator:
    """Tests for deactivate_collaborator()."""

    def test_deactivates_clean_collaborator(self, db_with_users, management_user):
        """Collaborator with no active dossiers is deactivated successfully."""
        result = deactivate_collaborator(collaborator_id=20, current_user=management_user)
        assert result["success"] is True

        # Verify is_active = False in DB
        with get_session() as session:
            collab = session.query(Collaborator).filter_by(id=20).first()
            assert collab.is_active is False

    def test_raises_on_active_client(self, db_with_users, management_user):
        """ReassignmentRequiredError raised if collaborator owns an active client."""
        with get_session() as session:
            client = Client(
                id=101,
                first_name="Beta",
                last_name="Inc",
                email="beta@beta.com",
                commercial_id=20,
                status=ClientStatus.ACTIVE,
            )
            session.add(client)
            session.commit()

        with pytest.raises(ReassignmentRequiredError) as exc_info:
            deactivate_collaborator(collaborator_id=20, current_user=management_user)

        assert "active client" in str(exc_info.value).lower()
        assert exc_info.value.active_dossiers["clients"][0]["email"] == "beta@beta.com"

    def test_raises_on_open_contract(self, db_with_users, management_user):
        """ReassignmentRequiredError raised if collaborator has an open contract."""
        with get_session() as session:
            c = Contract(
                id=203,
                client_id=1,
                commercial_id=20,
                total_amount="9000.00",
                remaining_amount="9000.00",
                status=ContractStatus.DRAFT,
            )
            session.add(c)
            session.commit()

        with pytest.raises(ReassignmentRequiredError) as exc_info:
            deactivate_collaborator(collaborator_id=20, current_user=management_user)

        assert "open contract" in str(exc_info.value).lower()

    def test_raises_on_active_event(self, db_with_users, management_user):
        """ReassignmentRequiredError raised if collaborator has an active event."""
        with get_session() as session:
            e = Event(
                id=302,
                contract_id=1,
                title="Live Show",
                start_date=None,
                end_date=None,
                support_id=20,
                is_cancelled=False,
            )
            session.add(e)
            session.commit()

        with pytest.raises(ReassignmentRequiredError) as exc_info:
            deactivate_collaborator(collaborator_id=20, current_user=management_user)

        assert "active event" in str(exc_info.value).lower()

    def test_lists_all_unresolved_dossiers(self, db_with_users, management_user):
        """Error message and active_dossiers include ALL types of unresolved items."""
        with get_session() as session:
            session.add(Client(
                id=102, first_name="C1", last_name="C1", email="c1@test.com",
                commercial_id=20, status=ClientStatus.ACTIVE,
            ))
            session.add(Contract(
                id=204, client_id=1, commercial_id=20,
                total_amount="1000.00", remaining_amount="1000.00",
                status=ContractStatus.SIGNED,
            ))
            session.add(Event(
                id=303, contract_id=1, title="E1",
                start_date=None, end_date=None,
                support_id=20, is_cancelled=False,
            ))
            session.commit()

        with pytest.raises(ReassignmentRequiredError) as exc_info:
            deactivate_collaborator(collaborator_id=20, current_user=management_user)

        err = str(exc_info.value).lower()
        assert "active client" in err
        assert "open contract" in err
        assert "active event" in err

        dossiers = exc_info.value.active_dossiers
        assert len(dossiers["clients"]) == 1
        assert len(dossiers["contracts"]) == 1
        assert len(dossiers["events"]) == 1

    @patch("services.collaborator_service.SESSION_FILE")
    def test_deletes_session_file_on_deactivation(self, mock_session_file, db_with_users, management_user):
        """Session file is deleted when a collaborator is deactivated."""
        mock_session_file.exists.return_value = True

        deactivate_collaborator(collaborator_id=20, current_user=management_user)
        mock_session_file.unlink.assert_called_once()

    def test_success_message_contains_collaborator_name(self, db_with_users, management_user):
        """Success result contains the collaborator's full name."""
        result = deactivate_collaborator(collaborator_id=20, current_user=management_user)
        assert "Pierre Vendeur" in result["message"]
        assert result["success"] is True
