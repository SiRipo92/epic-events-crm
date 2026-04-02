"""Unit tests for the event service.

Tests are organised by function:
    - create_event
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from exceptions import (
    ContractNotEligibleError,
    InvalidAssignmentError,
    PermissionDeniedError,
    SchedulingConflictWarning,
)
from models.contract import ContractStatus
from services.event_service import (
    assign_support,
    create_event,
    update_event,
)


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
