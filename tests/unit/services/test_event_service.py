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
from services.event_service import create_event


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
