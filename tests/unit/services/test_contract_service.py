"""Unit tests for the contract service.

Tests are organised by function:
    - create_contract
    - edit_contract
"""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from exceptions import (
    ClientNotFoundError,
    ContractNotEditableError,
    InvalidStatusTransitionError,
    PaymentExceedsBalanceError,
    PermissionDeniedError,
)
from models.contract import ContractStatus
from services.contract_service import (
    cancel_contract,
    create_contract,
    edit_contract,
    record_client_signature,
    record_deposit_received,
    record_payment,
    submit_for_signature,
    get_contracts_for_user,
    filter_contracts,
)


class TestWriteContractService:
    """Tests for contract write operations — create and edit."""

    # ---------------------------
    # create_contract — happy path
    # ---------------------------

    def test_create_contract_sets_draft_status_and_remaining_amount(
        self, management_user, make_client
    ):
        """Contract created with DRAFT status and remaining_amount = total_amount."""
        test_client = make_client(id=1)
        session = MagicMock()
        session.get.return_value = test_client

        result = create_contract(
            session=session,
            current_user=management_user,
            client_id=1,
            commercial_id=2,
            total_amount=Decimal("5000.00"),
        )

        assert result.status == ContractStatus.DRAFT
        assert result.remaining_amount == Decimal("5000.00")
        assert result.total_amount == Decimal("5000.00")
        session.add.assert_called_once()
        session.commit.assert_called_once()

    # ---------------------------
    # create_contract — sad path
    # ---------------------------

    def test_create_contract_invalid_client_raises(self, management_user):
        """Non-existent client raises ClientNotFoundError."""
        session = MagicMock()
        session.get.return_value = None

        with pytest.raises(ClientNotFoundError):
            create_contract(
                session=session,
                current_user=management_user,
                client_id=999,
                commercial_id=2,
                total_amount=Decimal("5000.00"),
            )

    def test_create_contract_non_management_caller_raises(self, commercial_user):
        """Non-Management caller raises PermissionDeniedError."""
        session = MagicMock()

        with pytest.raises(PermissionDeniedError):
            create_contract(
                session=session,
                current_user=commercial_user,
                client_id=1,
                commercial_id=2,
                total_amount=Decimal("5000.00"),
            )

    # ---------------------------
    # edit_contract — happy path
    # ---------------------------

    def test_edit_draft_contract_persists_changes(self, management_user, make_contract):
        """Editing a DRAFT contract persists changes and commits."""
        contract = make_contract(
            id=1,
            status=ContractStatus.DRAFT,
            total_amount=Decimal("5000.00"),
            remaining_amount=Decimal("5000.00"),
        )
        session = MagicMock()

        result = edit_contract(
            session=session,
            current_user=management_user,
            contract=contract,
            total_amount=Decimal("6000.00"),
        )

        assert result.total_amount == Decimal("6000.00")
        session.commit.assert_called_once()

    # ---------------------------
    # edit_contract — sad path
    # ---------------------------

    def test_edit_non_draft_contract_raises(self, management_user, make_contract):
        """Editing a non-DRAFT contract raises ContractNotEditableError."""
        contract = make_contract(
            id=1,
            status=ContractStatus.SIGNED,
        )
        session = MagicMock()

        with pytest.raises(ContractNotEditableError):
            edit_contract(
                session=session,
                current_user=management_user,
                contract=contract,
                total_amount=Decimal("6000.00"),
            )

    def test_edit_contract_non_management_caller_raises(
        self, commercial_user, make_contract
    ):
        """Non-Management caller raises PermissionDeniedError."""
        contract = make_contract(id=1, status=ContractStatus.DRAFT)
        session = MagicMock()

        with pytest.raises(PermissionDeniedError):
            edit_contract(
                session=session,
                current_user=commercial_user,
                contract=contract,
                total_amount=Decimal("6000.00"),
            )

    @pytest.mark.parametrize(
        "field, value",
        [
            ("total_amount", Decimal("9000.00")),
            ("client_id", 2),
            ("commercial_id", 3),
        ],
    )
    def test_edit_contract_partial_update_applies_field(
        self, management_user, make_contract, field, value
    ):
        """Each editable field is applied when provided."""
        contract = make_contract(id=1, status=ContractStatus.DRAFT)
        session = MagicMock()

        edit_contract(
            session=session,
            current_user=management_user,
            contract=contract,
            **{field: value},
        )

        assert getattr(contract, field) == value


class TestContractStatusTransitions:
    """Tests for contract status transition functions."""

    # ---------------------------
    # submit_for_signature — happy path
    # ---------------------------

    def test_draft_contract_transitions_to_pending(
        self, management_user, make_contract
    ):
        """DRAFT contract transitions to PENDING on submit."""
        contract = make_contract(id=1, status=ContractStatus.DRAFT)
        session = MagicMock()

        result = submit_for_signature(
            session=session,
            current_user=management_user,
            contract=contract,
        )

        assert result.status == ContractStatus.PENDING
        session.commit.assert_called_once()

    # ---------------------------
    # submit_for_signature — sad path
    # ---------------------------

    def test_non_draft_contract_raises_on_submit(self, management_user, make_contract):
        """Non-DRAFT contract raises InvalidStatusTransitionError."""
        contract = make_contract(id=1, status=ContractStatus.PENDING)
        session = MagicMock()

        with pytest.raises(InvalidStatusTransitionError):
            submit_for_signature(
                session=session,
                current_user=management_user,
                contract=contract,
            )

    def test_submit_for_signature_non_management_raises(
        self, commercial_user, make_contract
    ):
        """Non-Management caller raises PermissionDeniedError."""
        contract = make_contract(id=1, status=ContractStatus.DRAFT)
        session = MagicMock()

        with pytest.raises(PermissionDeniedError):
            submit_for_signature(
                session=session,
                current_user=commercial_user,
                contract=contract,
            )

    # ---------------------------
    # record_client_signature — happy path
    # ---------------------------

    def test_pending_contract_transitions_to_signed(
        self, management_user, make_contract
    ):
        """PENDING contract transitions to SIGNED on signature."""
        contract = make_contract(id=1, status=ContractStatus.PENDING)
        session = MagicMock()

        result = record_client_signature(
            session=session,
            current_user=management_user,
            contract=contract,
        )

        assert result.status == ContractStatus.SIGNED
        session.commit.assert_called_once()

    # ---------------------------
    # record_client_signature — sad path
    # ---------------------------

    def test_non_pending_contract_raises_on_signature(
        self, management_user, make_contract
    ):
        """Non-PENDING contract raises InvalidStatusTransitionError."""
        contract = make_contract(id=1, status=ContractStatus.DRAFT)
        session = MagicMock()

        with pytest.raises(InvalidStatusTransitionError):
            record_client_signature(
                session=session,
                current_user=management_user,
                contract=contract,
            )

    def test_record_signature_non_management_raises(
        self, commercial_user, make_contract
    ):
        """Non-Management caller raises PermissionDeniedError."""
        contract = make_contract(id=1, status=ContractStatus.PENDING)
        session = MagicMock()

        with pytest.raises(PermissionDeniedError):
            record_client_signature(
                session=session,
                current_user=commercial_user,
                contract=contract,
            )

    # ---------------------------
    # record_deposit_received — happy path
    # ---------------------------

    def test_signed_contract_transitions_to_deposit_received(
        self, management_user, make_contract
    ):
        """SIGNED contract transitions to DEPOSIT_RECEIVED on submit."""
        contract = make_contract(id=1, status=ContractStatus.SIGNED)
        session = MagicMock()

        result = record_deposit_received(
            session=session,
            current_user=management_user,
            contract=contract,
        )

        assert result.status == ContractStatus.DEPOSIT_RECEIVED
        assert result.deposit_received is True
        session.commit.assert_called_once()

    # ---------------------------
    # record_deposit_received — sad path
    # ---------------------------

    def test_deposit_on_non_signed_contract_raises(
        self, management_user, make_contract
    ):
        """Test a non-signed contract does not accept deposit."""
        contract = make_contract(status=ContractStatus.PENDING)
        session = MagicMock()

        with pytest.raises(InvalidStatusTransitionError):
            record_deposit_received(
                session=session,
                current_user=management_user,
                contract=contract,
            )

    def test_deposit_non_management_user_raises(self, commercial_user, make_contract):
        """Test permissions on recording a deposit received."""
        contract = make_contract(status=ContractStatus.SIGNED)
        session = MagicMock()

        with pytest.raises(PermissionDeniedError):
            record_deposit_received(
                session=session,
                current_user=commercial_user,
                contract=contract,
            )

    # ---------------------------
    # record_payment — happy path
    # ---------------------------

    def test_payment_reduces_remaining_amount(self, management_user, make_contract):
        """Valid payment reduces remaining_amount correctly."""
        contract = make_contract(
            id=1,
            status=ContractStatus.DEPOSIT_RECEIVED,
            total_amount=Decimal("5000.00"),
            remaining_amount=Decimal("5000.00"),
        )
        session = MagicMock()

        result = record_payment(
            session=session,
            current_user=management_user,
            contract=contract,
            amount_paid=Decimal("2000.00"),
        )

        assert result.remaining_amount == Decimal("3000.00")
        assert result.status == ContractStatus.DEPOSIT_RECEIVED
        session.commit.assert_called_once()

    def test_payment_clears_balance_transitions_to_paid_in_full(
        self, management_user, make_contract
    ):
        """Payment clearing the balance auto-transitions to PAID_IN_FULL."""
        contract = make_contract(
            id=1,
            status=ContractStatus.DEPOSIT_RECEIVED,
            total_amount=Decimal("5000.00"),
            remaining_amount=Decimal("2000.00"),
        )
        session = MagicMock()

        result = record_payment(
            session=session,
            current_user=management_user,
            contract=contract,
            amount_paid=Decimal("2000.00"),
        )

        assert result.remaining_amount == Decimal("0.00")
        assert result.status == ContractStatus.PAID_IN_FULL
        session.commit.assert_called_once()

    # ---------------------------
    # record_payment — sad path
    # ---------------------------

    def test_payment_exceeding_balance_raises(self, management_user, make_contract):
        """Payment exceeding remaining balance raises PaymentExceedsBalanceError."""
        contract = make_contract(
            id=1,
            status=ContractStatus.DEPOSIT_RECEIVED,
            total_amount=Decimal("5000.00"),
            remaining_amount=Decimal("1000.00"),
        )
        session = MagicMock()

        with pytest.raises(PaymentExceedsBalanceError):
            record_payment(
                session=session,
                current_user=management_user,
                contract=contract,
                amount_paid=Decimal("2000.00"),
            )

        session.commit.assert_not_called()

    def test_payment_on_non_deposit_received_contract_raises(
        self, management_user, make_contract
    ):
        """Non-DEPOSIT_RECEIVED status raises InvalidStatusTransitionError."""
        contract = make_contract(
            id=1,
            status=ContractStatus.SIGNED,
        )
        session = MagicMock()

        with pytest.raises(InvalidStatusTransitionError):
            record_payment(
                session=session,
                current_user=management_user,
                contract=contract,
                amount_paid=Decimal("1000.00"),
            )

    def test_payment_non_management_caller_raises(self, commercial_user, make_contract):
        """Non-Management caller raises PermissionDeniedError."""
        contract = make_contract(
            id=1,
            status=ContractStatus.DEPOSIT_RECEIVED,
        )
        session = MagicMock()

        with pytest.raises(PermissionDeniedError):
            record_payment(
                session=session,
                current_user=commercial_user,
                contract=contract,
                amount_paid=Decimal("1000.00"),
            )

    # ---------------------------
    # cancel_contract — happy path
    # ---------------------------

    def test_cancel_contract_with_linked_event(
        self, management_user, make_contract, make_event
    ):
        """Cancelling a contract also cancels the linked event."""
        event = make_event(id=1, is_cancelled=False)
        contract = make_contract(
            id=1,
            status=ContractStatus.DEPOSIT_RECEIVED,
        )
        contract.event = event
        session = MagicMock()

        result = cancel_contract(
            session=session,
            current_user=management_user,
            contract=contract,
        )

        assert result.status == ContractStatus.CANCELLED
        assert event.is_cancelled is True
        session.commit.assert_called_once()

    def test_cancel_contract_without_event(self, management_user, make_contract):
        """Cancelling a contract with no linked event cancels contract only."""
        contract = make_contract(
            id=1,
            status=ContractStatus.SIGNED,
        )
        contract.event = None
        session = MagicMock()

        result = cancel_contract(
            session=session,
            current_user=management_user,
            contract=contract,
        )

        assert result.status == ContractStatus.CANCELLED
        session.commit.assert_called_once()

    # ---------------------------
    # cancel_contract — sad path
    # ---------------------------

    def test_cancel_already_cancelled_contract_raises(
        self, management_user, make_contract
    ):
        """Already CANCELLED contract raises InvalidStatusTransitionError."""
        contract = make_contract(id=1, status=ContractStatus.CANCELLED)
        session = MagicMock()

        with pytest.raises(InvalidStatusTransitionError):
            cancel_contract(
                session=session,
                current_user=management_user,
                contract=contract,
            )

    def test_cancel_paid_in_full_contract_raises(self, management_user, make_contract):
        """PAID_IN_FULL contract raises InvalidStatusTransitionError."""
        contract = make_contract(id=1, status=ContractStatus.PAID_IN_FULL)
        session = MagicMock()

        with pytest.raises(InvalidStatusTransitionError):
            cancel_contract(
                session=session,
                current_user=management_user,
                contract=contract,
            )

    def test_cancel_contract_non_management_raises(
        self, commercial_user, make_contract
    ):
        """Non-Management caller raises PermissionDeniedError."""
        contract = make_contract(id=1, status=ContractStatus.DRAFT)
        session = MagicMock()

        with pytest.raises(PermissionDeniedError):
            cancel_contract(
                session=session,
                current_user=commercial_user,
                contract=contract,
            )


class TestReadContractService:
    """Tests for contract read operations — scoped by role."""

    # ---------------------------
    # get_contracts_for_user — happy path
    # ---------------------------

    @pytest.mark.parametrize("user_fixture,expected_count", [
        ("management_user", 2),
        ("commercial_user", 1),
        ("support_user", 1),
    ])
    def test_get_contracts_for_user_scoped_by_role(
            self, request, make_contract, user_fixture, expected_count
    ):
        """Each role gets contracts scoped to their access level."""
        user = request.getfixturevalue(user_fixture)
        contracts = [make_contract(id=i) for i in range(expected_count)]

        session = MagicMock()
        session.scalars.return_value.all.return_value = contracts

        result = get_contracts_for_user(
            session=session,
            current_user=user,
        )

        assert len(result) == expected_count


class TestFilterContracts:
    """Tests for filter_contracts() — applied on top of scoped list."""

    # ---------------------------
    # filter_contracts — happy path
    # ---------------------------

    def test_filter_by_status(self, make_contract):
        """Filter by status returns only matching contracts."""
        signed = make_contract(id=1, status=ContractStatus.SIGNED)
        draft = make_contract(id=2, status=ContractStatus.DRAFT)

        result = filter_contracts(
            contracts=[signed, draft],
            status=ContractStatus.SIGNED,
        )

        assert len(result) == 1
        assert result[0].status == ContractStatus.SIGNED

    def test_filter_by_client_name(self, make_contract, make_client):
        """Filter by client name returns only matching contracts."""
        client_a = make_client(id=1, first_name="Marie", last_name="Curie")
        client_b = make_client(id=2, first_name="Jean", last_name="Dupont")

        contract_a = make_contract(id=1)
        contract_b = make_contract(id=2)
        contract_a.client = client_a
        contract_b.client = client_b

        result = filter_contracts(
            contracts=[contract_a, contract_b],
            client_name="Curie",
        )

        assert len(result) == 1
        assert result[0].client.last_name == "Curie"
