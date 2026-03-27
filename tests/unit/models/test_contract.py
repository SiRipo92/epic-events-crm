"""
Unit tests for the Contract ORM model.

Tests cover:
    - is_signed computed property (all ContractStatus values)
    - is_cancelled computed property (all ContractStatus values)
    - is_deposit_received computed property (all ContractStatus values)
    - is_fully_paid computed property (all ContractStatus values)
"""

import pytest
from decimal import Decimal

from models.contract import Contract, ContractStatus


class TestContractStatusProperties:
    """Tests for is_signed and is_cancelled computed properties."""

    @pytest.mark.parametrize("status, expected", [
        (ContractStatus.SIGNED,            True),
        (ContractStatus.DEPOSIT_RECEIVED,  True),
        (ContractStatus.PAID_IN_FULL,      True),
        (ContractStatus.DRAFT,             False),
        (ContractStatus.PENDING,           False),
        (ContractStatus.CANCELLED,         False),
    ])
    def test_is_signed(self, draft_contract, status, expected):
        """Parametrized: is_signed returns correct value for every status."""
        draft_contract.status = status
        assert draft_contract.is_signed is expected

    @pytest.mark.parametrize("status, expected", [
        (ContractStatus.CANCELLED,         True),
        (ContractStatus.DRAFT,             False),
        (ContractStatus.PENDING,           False),
        (ContractStatus.SIGNED,            False),
        (ContractStatus.DEPOSIT_RECEIVED,  False),
        (ContractStatus.PAID_IN_FULL,      False),
    ])
    def test_is_cancelled(self, draft_contract, status, expected):
        """Parametrized: is_cancelled returns correct value for every status."""
        draft_contract.status = status
        assert draft_contract.is_cancelled is expected


class TestContractIsDepositReceived:
    """Tests for the is_deposit_received computed property.

    True only when status is DEPOSIT_RECEIVED or PAID_IN_FULL.
    This is the gate that unlocks event creation.
    """

    @pytest.mark.parametrize("status, expected", [
        (ContractStatus.DEPOSIT_RECEIVED,  True),
        (ContractStatus.PAID_IN_FULL,      True),
        (ContractStatus.DRAFT,             False),
        (ContractStatus.PENDING,           False),
        (ContractStatus.SIGNED,            False),
        (ContractStatus.CANCELLED,         False),
    ])
    def test_is_deposit_received(self, draft_contract, status, expected):
        """Parametrized: is_deposit_received returns correct value for every status."""
        draft_contract.status = status
        assert draft_contract.is_deposit_received is expected


class TestContractIsFullyPaid:
    """Tests for the is_fully_paid computed property.

    is_fully_paid reflects status == PAID_IN_FULL only.
    The remaining_amount balance is reduced by record_payment() in the
    service layer — when it reaches zero the service auto-transitions
    the status to PAID_IN_FULL. The property itself checks status, not
    the balance directly.
    """

    @pytest.mark.parametrize("status, expected", [
        (ContractStatus.PAID_IN_FULL,      True),
        (ContractStatus.DRAFT,             False),
        (ContractStatus.PENDING,           False),
        (ContractStatus.SIGNED,            False),
        (ContractStatus.DEPOSIT_RECEIVED,  False),
        (ContractStatus.CANCELLED,         False),
    ])
    def test_is_fully_paid(self, draft_contract, status, expected):
        """Parametrized: is_fully_paid returns True only for PAID_IN_FULL status."""
        draft_contract.status = status
        assert draft_contract.is_fully_paid is expected
