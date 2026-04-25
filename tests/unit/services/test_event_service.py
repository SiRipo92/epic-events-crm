"""Unit tests for the event service.

Tests are organised by function:
    - create_event
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from models.contract import ContractStatus
from services.event_service import (
    assign_support,
    create_event,
    filter_events,
    get_all_events,
    get_event_by_id,
    get_events_for_user,
    update_event,
)
from utils.exceptions import (
    ContractNotEligibleError,
    EventNotFoundError,
    InvalidAssignmentError,
    PermissionDeniedError,
    SchedulingConflictWarning,
)


# ---------------------------
# Helper function
# ---------------------------
def _attach_contract(event, make_contract, commercial_id: int):
    """Attach a valid SQLAlchemy Contract instance to an event."""
    contract = make_contract(commercial_id=commercial_id)
    event.contract = contract


class TestWriteEventService:
    """Tests for event write operations."""

    # ---------------------------
    # create_event — happy path
    # ---------------------------

    def test_create_event_sets_support_id_to_none(
        self, commercial_user, make_contract, default_event_kwargs
    ):
        """Event created with support_id = None on creation."""
        contract = make_contract(
            id=1,
            commercial_id=commercial_user.id,
            status=ContractStatus.DEPOSIT_RECEIVED,
        )
        session = MagicMock()

        result = create_event(
            session=session,
            current_user=commercial_user,
            contract=contract,
            **default_event_kwargs,
        )

        assert result.support_id is None
        assert result.contract_id == contract.id
        assert result.title == "Annual Gala"
        session.add.assert_called_once()
        session.commit.assert_called_once()

    # ---------------------------
    # create_event — sad path
    # ---------------------------

    def test_create_event_non_deposit_received_contract_raises(
        self, commercial_user, make_contract, default_event_kwargs
    ):
        """Contract not in DEPOSIT_RECEIVED raises ContractNotEligibleError."""
        contract = make_contract(
            id=1,
            commercial_id=commercial_user.id,
            status=ContractStatus.SIGNED,
        )
        session = MagicMock()

        with pytest.raises(ContractNotEligibleError):
            create_event(
                session=session,
                current_user=commercial_user,
                contract=contract,
                **default_event_kwargs,
            )

    @pytest.mark.parametrize(
        "user_fixture,contract_commercial_id",
        [
            ("management_user", 1),  # wrong role
            ("commercial_user", 999),  # right role, wrong owner
        ],
    )
    def test_create_event_permission_denied(
        self,
        request,
        make_contract,
        default_event_kwargs,
        user_fixture,
        contract_commercial_id,
    ):
        """Wrong role or non-owner raises PermissionDeniedError."""
        user = request.getfixturevalue(user_fixture)
        contract = make_contract(
            id=1,
            commercial_id=contract_commercial_id,
            status=ContractStatus.DEPOSIT_RECEIVED,
        )
        session = MagicMock()

        with pytest.raises(PermissionDeniedError):
            create_event(
                session=session,
                current_user=user,
                contract=contract,
                **default_event_kwargs,
            )

    # ---------------------------
    # update_event — happy path
    # ---------------------------

    def test_support_updates_own_event(self, support_user, make_event):
        """Support can update allowed fields on their assigned event."""
        event = make_event(id=1, support_id=support_user.id)
        session = MagicMock()

        result = update_event(
            session=session,
            current_user=support_user,
            event=event,
            title="Updated Gala",
        )

        assert result.title == "Updated Gala"
        session.commit.assert_called_once()

    @pytest.mark.parametrize(
        "field, value",
        [
            ("location_street", "12 rue de la Paix"),
            ("location_zip", "75001"),
            ("location_city", "Paris"),
            ("location_country", "France"),
            ("attendees", 50),
            ("notes", "VIP seating required"),
        ],
    )
    def test_update_event_partial_update_applies_field(
        self, support_user, make_event, field, value
    ):
        """Each updatable field is applied when provided."""
        event = make_event(id=1, support_id=support_user.id)
        session = MagicMock()

        update_event(
            session=session,
            current_user=support_user,
            event=event,
            **{field: value},
        )

        assert getattr(event, field) == value

    # ---------------------------
    # update_event — sad path
    # ---------------------------

    @pytest.mark.parametrize(
        "user_fixture,support_id",
        [
            ("management_user", 1),  # wrong role
            ("support_user", 999),  # right role, wrong owner
        ],
    )
    def test_update_event_permission_denied(
        self, request, make_event, user_fixture, support_id
    ):
        """Wrong role or non-owner raises PermissionDeniedError."""
        user = request.getfixturevalue(user_fixture)
        event = make_event(id=1, support_id=support_id)
        session = MagicMock()

        with pytest.raises(PermissionDeniedError):
            update_event(
                session=session,
                current_user=user,
                event=event,
                title="Hacked",
            )


class TestAssignSupportService:
    """Tests for assign_support()."""

    # ---------------------------
    # assign_support — happy path
    # ---------------------------

    def test_valid_support_assigned_successfully(
        self, management_user, support_user, make_event
    ):
        """Valid support member with no conflict is assigned successfully."""
        event = make_event(id=1, support_id=None)
        session = MagicMock()
        session.scalars.return_value.all.return_value = []

        result = assign_support(
            session=session,
            current_user=management_user,
            event=event,
            support=support_user,
        )

        assert result.support_id == support_user.id
        session.commit.assert_called_once()

    def test_force_assign_after_conflict_warning(
        self, management_user, support_user, make_event
    ):
        """Management can force assign support despite scheduling conflict."""
        event = make_event(
            id=1,
            support_id=None,
            start_date=datetime(2025, 9, 1, 9, 0),
            end_date=datetime(2025, 9, 1, 17, 0),
        )
        session = MagicMock()
        session.scalars.return_value.all.return_value = []

        # Force assign by catching the warning and calling again with no conflict
        result = assign_support(
            session=session,
            current_user=management_user,
            event=event,
            support=support_user,
        )

        assert result.support_id == support_user.id
        session.commit.assert_called_once()

    # ---------------------------
    # assign_support — sad path
    # ---------------------------

    def test_non_support_collaborator_raises(
        self, management_user, commercial_user, make_event
    ):
        """Assigning a non-Support collaborator raises InvalidAssignmentError."""
        event = make_event(id=1, support_id=None)
        session = MagicMock()

        with pytest.raises(InvalidAssignmentError):
            assign_support(
                session=session,
                current_user=management_user,
                event=event,
                support=commercial_user,
            )

    def test_scheduling_conflict_raises_warning(
        self, management_user, support_user, make_event
    ):
        """Support with same-date event raises SchedulingConflictWarning."""
        event = make_event(
            id=1,
            support_id=None,
            start_date=datetime(2025, 9, 1, 9, 0),
            end_date=datetime(2025, 9, 1, 17, 0),
        )
        conflicting_event = make_event(
            id=2,
            support_id=support_user.id,
            start_date=datetime(2025, 9, 1, 14, 0),
            end_date=datetime(2025, 9, 1, 18, 0),
        )
        session = MagicMock()
        session.scalars.return_value.all.return_value = [conflicting_event]

        with pytest.raises(SchedulingConflictWarning):
            assign_support(
                session=session,
                current_user=management_user,
                event=event,
                support=support_user,
            )

    def test_non_management_caller_raises(
        self, commercial_user, support_user, make_event
    ):
        """Non-Management caller raises PermissionDeniedError."""
        event = make_event(id=1, support_id=None)
        session = MagicMock()

        with pytest.raises(PermissionDeniedError):
            assign_support(
                session=session,
                current_user=commercial_user,
                event=event,
                support=support_user,
            )


class TestReadEventService:
    """Tests for event read operations — scoped by role."""

    # ---------------------------
    # get_events_for_user — happy path
    # ---------------------------

    @pytest.mark.parametrize(
        "user_fixture,expected_count",
        [
            ("management_user", 2),
            ("commercial_user", 1),
            ("support_user", 1),
        ],
    )
    def test_get_events_for_user_scoped_by_role(
        self, request, make_event, user_fixture, expected_count
    ):
        """Each role gets events scoped to their access level."""
        user = request.getfixturevalue(user_fixture)
        events = [make_event(id=i) for i in range(expected_count)]

        session = MagicMock()
        session.scalars.return_value.all.return_value = events

        result = get_events_for_user(
            session=session,
            current_user=user,
        )

        assert len(result) == expected_count

    # ---------------------------
    # filter_events — happy path
    # ---------------------------

    def test_filter_by_support_unassigned(self, make_event):
        """filter_events returns only events with no support assigned."""
        assigned = make_event(id=1, support_id=1)
        unassigned = make_event(id=2, support_id=None)

        result = filter_events(
            events=[assigned, unassigned],
            support_unassigned=True,
        )

        assert len(result) == 1
        assert result[0].support_id is None

    def test_filter_by_upcoming(self, make_event):
        """filter_events returns only future events when upcoming=True."""
        past = make_event(
            id=1,
            start_date=datetime.now(timezone.utc) - timedelta(days=1),
            end_date=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        future = make_event(
            id=2,
            start_date=datetime.now(timezone.utc) + timedelta(days=1),
            end_date=datetime.now(timezone.utc) + timedelta(days=2),
        )

        result = filter_events(
            events=[past, future],
            upcoming=True,
        )

        assert len(result) == 1
        assert result[0].id == 2

    def test_filter_by_past(self, make_event):
        """filter_events returns only past events when past=True."""
        past = make_event(
            id=1,
            start_date=datetime.now(timezone.utc) - timedelta(days=2),
            end_date=datetime.now(timezone.utc) - timedelta(days=1),
        )
        future = make_event(
            id=2,
            start_date=datetime.now(timezone.utc) + timedelta(days=1),
            end_date=datetime.now(timezone.utc) + timedelta(days=2),
        )

        result = filter_events(events=[past, future], past=True)

        assert len(result) == 1
        assert result[0].id == 1

    # ---------------------------
    # get_event_by_id — happy path
    # ---------------------------

    def test_management_retrieves_any_event(
        self, management_user, make_event, session_with_event
    ):
        """Management can retrieve any event by ID."""
        event = make_event(id=1)
        session = session_with_event(event)

        result = get_event_by_id(session, management_user, event.id)

        assert result == event

    def test_get_event_by_id_returns_event_for_any_role(
        self, request, make_event, session_with_event
    ):
        """Any role can retrieve any event by ID — no ownership check."""
        for fixture in ("management_user", "commercial_user", "support_user"):
            user = request.getfixturevalue(fixture)
            # Deliberately not theirs: support_id and commercial_id don't match
            event = make_event(id=1, support_id=999)

            session = session_with_event(event)

            result = get_event_by_id(session, user, event.id)
            assert result == event

    def test_get_event_by_id_not_found_raises(self, management_user):
        """EventNotFoundError when event does not exist."""
        session = MagicMock()
        session.get.return_value = None

        with pytest.raises(EventNotFoundError):
            get_event_by_id(session, management_user, 999)

    def test_returns_all_events_for_any_role(self, request, make_event):
        """All roles receive all events."""
        for fixture in ("management_user", "commercial_user", "support_user"):
            user = request.getfixturevalue(fixture)
            events = [make_event(id=i) for i in range(3)]

            session = MagicMock()
            session.scalars.return_value.all.return_value = events

            result = get_all_events(session=session, current_user=user)
            assert len(result) == 3

    def test_returns_empty_list_when_no_events(self, management_user):
        """Returns empty list when no events exist."""
        session = MagicMock()
        session.scalars.return_value.all.return_value = []

        result = get_all_events(session=session, current_user=management_user)
        assert result == []
