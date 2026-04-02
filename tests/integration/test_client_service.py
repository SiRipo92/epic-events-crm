"""
Integration tests for the client service.

Tests run against a real PostgreSQL test database.
Each test runs in its own transaction that rolls back on teardown.
"""

import logging

from models.client import Client
from services.client_service import (
    create_client,
    get_clients_for_user,
    update_client,
)

logger = logging.getLogger(__name__)


class TestClientServiceIntegration:
    """Integration tests for client service flows."""

    def test_create_client_persists_to_db(self, seeded_db, db_session):
        """create_client writes row with correct commercial_id to real DB."""
        commercial = seeded_db["commercial"]
        logger.info("Creating client as commercial id=%s", commercial.id)

        result = create_client(
            session=db_session,
            current_user=commercial,
            first_name="Marie",
            last_name="Curie",
            email="marie.curie@epicevents.com",
        )

        fetched = db_session.get(Client, result.id)
        assert fetched is not None
        assert fetched.commercial_id == commercial.id
        logger.info(
            "Client id=%s confirmed in DB with commercial_id=%s",
            fetched.id,
            fetched.commercial_id,
        )

    def test_update_client_persists_and_sets_updated_at(
        self, seeded_db, db_session, seeded_client
    ):
        """update_client persists fields and updated_at is auto-set by DB."""
        commercial = seeded_db["commercial"]
        logger.info("Updating client id=%s", seeded_client.id)

        update_client(
            session=db_session,
            current_user=commercial,
            client=seeded_client,
            first_name="Maria",
        )

        db_session.expire(seeded_client)
        assert seeded_client.first_name == "Maria"
        assert seeded_client.updated_at is not None
        logger.info(
            "Update confirmed — first_name=%s updated_at=%s",
            seeded_client.first_name,
            seeded_client.updated_at,
        )

    def test_get_clients_scoped_by_role(
        self, seeded_db, db_session, seeded_client
    ):
        """get_clients_for_user returns correct rows per role against real DB."""
        commercial = seeded_db["commercial"]
        manager = seeded_db["management"]
        logger.info(
            "Verifying scoped client queries — client id=%s", seeded_client.id
        )

        commercial_results = get_clients_for_user(
            session=db_session,
            current_user=commercial,
        )
        management_results = get_clients_for_user(
            session=db_session,
            current_user=manager,
        )

        assert len(commercial_results) == 1
        assert commercial_results[0].commercial_id == commercial.id
        assert len(management_results) == 1
        logger.info(
            "Commercial sees %s client(s), Management sees %s client(s)",
            len(commercial_results),
            len(management_results),
        )
