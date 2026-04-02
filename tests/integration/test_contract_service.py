"""
Integration tests for the contract service.

Tests run against a real PostgreSQL test database.
Each test runs in its own transaction that rolls back on teardown.
"""

import logging
from decimal import Decimal

from models.contract import Contract, ContractStatus
from models.event import Event
from services.contract_service import (
    cancel_contract,
    create_contract,
    get_contracts_for_user,
    record_payment,
)

logger = logging.getLogger(__name__)


class TestContractServiceIntegration:
    """Integration tests for contract service flows."""

    def test_create_contract_persists_to_db(
        self, seeded_db, db_session, seeded_client
    ):
        """create_contract writes row with correct defaults to real DB."""
        manager = seeded_db["management"]
        commercial = seeded_db["commercial"]
        logger.info("Creating contract for client id=%s", seeded_client.id)

        result = create_contract(
            session=db_session,
            current_user=manager,
            client_id=seeded_client.id,
            commercial_id=commercial.id,
            total_amount=Decimal("5000.00"),
        )

        fetched = db_session.get(Contract, result.id)
        assert fetched is not None
        assert fetched.status == ContractStatus.DRAFT
        assert fetched.remaining_amount == Decimal("5000.00")
        assert fetched.client_id == seeded_client.id
        logger.info(
            "Contract id=%s confirmed — status=%s remaining=%s",
            fetched.id,
            fetched.status,
            fetched.remaining_amount,
        )

    def test_full_payment_flow_transitions_to_paid_in_full(
        self, seeded_db, db_session, seeded_deposit_contract
    ):
        """record_payment clears balance and auto-transitions to PAID_IN_FULL."""
        manager = seeded_db["management"]
        logger.info(
            "Recording full payment on contract id=%s",
            seeded_deposit_contract.id,
        )

        record_payment(
            session=db_session,
            current_user=manager,
            contract=seeded_deposit_contract,
            amount_paid=Decimal("5000.00"),
        )

        db_session.expire(seeded_deposit_contract)
        assert seeded_deposit_contract.status == ContractStatus.PAID_IN_FULL
        assert seeded_deposit_contract.remaining_amount == Decimal("0.00")
        logger.info(
            "Payment confirmed — status=%s remaining=%s",
            seeded_deposit_contract.status,
            seeded_deposit_contract.remaining_amount,
        )

    def test_cancel_contract_cascades_to_linked_event(
        self, seeded_db, db_session, seeded_deposit_contract
    ):
        """cancel_contract sets contract CANCELLED and event is_cancelled in DB."""
        from datetime import datetime

        manager = seeded_db["management"]

        event = Event()
        event.contract_id = seeded_deposit_contract.id
        event.title = "Test Event"
        event.start_date = datetime(2026, 9, 1, 9, 0)
        event.end_date = datetime(2026, 9, 1, 17, 0)
        event.location_street = "34 rue de la Paix"
        event.location_city = "Paris"
        event.location_zip = "75001"
        event.is_cancelled = False
        db_session.add(event)
        db_session.flush()
        seeded_deposit_contract.event = event
        logger.info(
            "Linked event id=%s to contract id=%s",
            event.id,
            seeded_deposit_contract.id,
        )

        cancel_contract(
            session=db_session,
            current_user=manager,
            contract=seeded_deposit_contract,
        )

        db_session.expire(seeded_deposit_contract)
        db_session.expire(event)
        assert seeded_deposit_contract.status == ContractStatus.CANCELLED
        assert event.is_cancelled is True
        logger.info(
            "Cancellation confirmed — contract=%s event.is_cancelled=%s",
            seeded_deposit_contract.status,
            event.is_cancelled,
        )

    def test_get_contracts_scoped_by_role(
        self, seeded_db, db_session, seeded_contract
    ):
        """get_contracts_for_user returns correct rows per role against real DB."""
        manager = seeded_db["management"]
        commercial = seeded_db["commercial"]
        logger.info(
            "Verifying scoped contract queries — contract id=%s",
            seeded_contract.id,
        )

        commercial_results = get_contracts_for_user(
            session=db_session,
            current_user=commercial,
        )
        management_results = get_contracts_for_user(
            session=db_session,
            current_user=manager,
        )

        assert len(commercial_results) == 1
        assert commercial_results[0].commercial_id == commercial.id
        assert len(management_results) == 1
        logger.info(
            "Commercial sees %s contract(s), Management sees %s contract(s)",
            len(commercial_results),
            len(management_results),
        )
