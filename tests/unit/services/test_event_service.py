"""Unit tests for the event service.

Tests are organised by function:
    - create_event
"""

from unittest.mock import MagicMock

import pytest

from exceptions import (
    ContractNotEligibleError,
    PermissionDeniedError,
)
from models.contract import ContractStatus
from services.event_service import (
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
