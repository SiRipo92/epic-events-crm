"""
Integration tests for the event service.

Tests run against a real PostgreSQL test database.
Each test runs in its own transaction that rolls back on teardown.
"""

import logging

from models.event import Event
from services.event_service import (
    assign_support,
    create_event,
    get_events_for_user,
)

logger = logging.getLogger(__name__)


class TestEventServiceIntegration:
    """Integration tests for event service flows."""

    def test_create_event_persists_to_db(
        self, seeded_db, db_session, seeded_deposit_contract
    ):
        """create_event writes row with support_id=None and FK to contract."""
        from datetime import datetime

        commercial = seeded_db["commercial"]
        logger.info(
            "Creating event for contract id=%s", seeded_deposit_contract.id
        )

        result = create_event(
            session=db_session,
            current_user=commercial,
            contract=seeded_deposit_contract,
            title="Annual Gala",
            start_date=datetime(2026, 9, 1, 9, 0),
            end_date=datetime(2026, 9, 1, 17, 0),
            location_street="34 rue de la Paix",
            location_city="Paris",
            location_zip="75001",
        )

        fetched = db_session.get(Event, result.id)
        assert fetched is not None
        assert fetched.support_id is None
        assert fetched.contract_id == seeded_deposit_contract.id
        logger.info(
            "Event id=%s confirmed — support_id=%s contract_id=%s",
            fetched.id,
            fetched.support_id,
            fetched.contract_id,
        )

    def test_assign_support_persists_to_db(
        self, seeded_db, db_session, seeded_event
    ):
        """assign_support persists support_id to DB and FK join works."""
        manager = seeded_db["management"]
        support = seeded_db["support"]
        logger.info(
            "Assigning support id=%s to event id=%s",
            support.id,
            seeded_event.id,
        )

        assign_support(
            session=db_session,
            current_user=manager,
            event=seeded_event,
            support=support,
        )

        db_session.expire(seeded_event)
        assert seeded_event.support_id == support.id
        logger.info(
            "Support assignment confirmed — support_id=%s",
            seeded_event.support_id,
        )

    def test_get_events_scoped_by_role(
        self, seeded_db, db_session, seeded_event
    ):
        """get_events_for_user returns correct rows per role against real DB."""
        manager = seeded_db["management"]
        support = seeded_db["support"]

        # Assign support so support can see the event
        assign_support(
            session=db_session,
            current_user=manager,
            event=seeded_event,
            support=support,
        )
        logger.info(
            "Verifying scoped event queries — event id=%s", seeded_event.id
        )

        management_results = get_events_for_user(
            session=db_session,
            current_user=manager,
        )
        support_results = get_events_for_user(
            session=db_session,
            current_user=support,
        )

        assert len(management_results) == 1
        assert len(support_results) == 1
        assert support_results[0].support_id == support.id
        logger.info(
            "Management sees %s event(s), Support sees %s event(s)",
            len(management_results),
            len(support_results),
        )
