"""
Integration tests for the collaborator service.

Tests run against a real PostgreSQL test database.
Each test runs in its own transaction that rolls back on teardown.
"""

import logging

import pytest

from exceptions import (
    CollaboratorNotFoundError,
    DuplicateEmailError,
    ReassignmentRequiredError,
)
from models.client import Client
from models.collaborator import Collaborator
from services.collaborator_service import (
    create_collaborator,
    deactivate_collaborator,
    get_collaborator_by_id,
    get_collaborators,
    update_collaborator,
)

logger = logging.getLogger(__name__)


class TestCreateCollaboratorIntegration:
    """Integration tests for create_collaborator()."""

    def test_creates_row_in_db(self, seeded_db, db_session):
        """create_collaborator writes a real row to the DB."""
        manager = seeded_db["management"]
        logger.info("Creating new collaborator as %s", manager.email)

        result = create_collaborator(
            session=db_session,
            current_user=manager,
            first_name="New",
            last_name="User",
            email="new.user@epicevents.com",
            role_id=2,
            password="password123",
        )
        logger.info(
            "Collaborator created — id=%s employee_number=%s",
            result.id,
            result.employee_number,
        )

        fetched = db_session.get(Collaborator, result.id)
        assert fetched is not None
        assert fetched.email == "new.user@epicevents.com"
        assert fetched.must_change_password is True
        assert fetched.password_hash != "password123"
        assert fetched.password_hash.startswith("$2b$")
        logger.info("Password stored as bcrypt hash — not plaintext")

    def test_duplicate_email_rejected_by_service(self, seeded_db, db_session):
        """Duplicate email raises DuplicateEmailError before hitting DB."""
        manager = seeded_db["management"]
        logger.info(
            "Attempting to create collaborator with duplicate email: %s",
            manager.email,
        )

        with pytest.raises(DuplicateEmailError):
            create_collaborator(
                session=db_session,
                current_user=manager,
                first_name="Copy",
                last_name="Cat",
                email=manager.email,
                role_id=2,
                password="password123",
            )
        logger.info("DuplicateEmailError raised as expected")


class TestUpdateCollaboratorIntegration:
    """Integration tests for update_collaborator()."""

    def test_fields_persisted_and_updated_at_set(self, seeded_db, db_session):
        """Updated fields and updated_at are committed to the DB."""
        manager = seeded_db["management"]
        commercial = seeded_db["commercial"]
        logger.info("Updating first_name for collaborator id=%s", commercial.id)

        update_collaborator(
            session=db_session,
            current_user=manager,
            collaborator=commercial,
            first_name="Roberto",
        )

        db_session.expire(commercial)
        assert commercial.first_name == "Roberto"
        assert commercial.updated_at is not None
        logger.info(
            "Update confirmed — first_name=%s updated_at=%s",
            commercial.first_name,
            commercial.updated_at,
        )

    def test_duplicate_email_rejected_on_update(self, seeded_db, db_session):
        """Updating to an existing email raises DuplicateEmailError."""
        manager = seeded_db["management"]
        commercial = seeded_db["commercial"]
        support = seeded_db["support"]
        logger.info(
            "Attempting to update commercial email to support's email: %s",
            support.email,
        )

        with pytest.raises(DuplicateEmailError):
            update_collaborator(
                session=db_session,
                current_user=manager,
                collaborator=commercial,
                email=support.email,
            )
        logger.info("DuplicateEmailError raised as expected")


class TestDeactivateCollaboratorIntegration:
    """Integration tests for deactivate_collaborator()."""

    def test_is_active_false_persisted(self, seeded_db, db_session, session_file):
        """is_active = False is committed to the DB."""
        manager = seeded_db["management"]
        support = seeded_db["support"]
        logger.info("Deactivating collaborator id=%s", support.id)

        deactivate_collaborator(
            session=db_session,
            current_user=manager,
            collaborator=support,
        )

        db_session.expire(support)
        assert support.is_active is False
        logger.info(
            "Deactivation confirmed — is_active=%s for id=%s",
            support.is_active,
            support.id,
        )

    def test_raises_if_active_dossiers_exist(self, seeded_db, db_session):
        """Deactivation blocked when collaborator has active clients."""
        manager = seeded_db["management"]
        commercial = seeded_db["commercial"]

        client = Client()
        client.first_name = "Test"
        client.last_name = "Client"
        client.email = "test.client@example.com"
        client.commercial_id = commercial.id
        db_session.add(client)
        db_session.flush()
        logger.info(
            "Created client id=%s linked to commercial id=%s",
            client.id,
            commercial.id,
        )

        with pytest.raises(ReassignmentRequiredError):
            deactivate_collaborator(
                session=db_session,
                current_user=manager,
                collaborator=commercial,
            )

        db_session.expire(commercial)
        assert commercial.is_active is True
        logger.info(
            "ReassignmentRequiredError raised — is_active unchanged: %s",
            commercial.is_active,
        )


class TestGetCollaboratorsIntegration:
    """Integration tests for get_collaborators()."""

    def test_returns_all_collaborators(self, seeded_db, db_session):
        """No filters returns all seeded collaborators."""
        manager = seeded_db["management"]
        logger.info("Fetching all collaborators with no filters")

        result = get_collaborators(session=db_session, current_user=manager)

        logger.info("Query returned %s collaborators", len(result))
        assert len(result) == 3

    def test_filter_by_role_returns_correct_rows(self, seeded_db, db_session):
        """Role filter returns only matching collaborators from real DB."""
        manager = seeded_db["management"]
        logger.info("Fetching collaborators filtered by role=COMMERCIAL")

        result = get_collaborators(
            session=db_session,
            current_user=manager,
            role="COMMERCIAL",
        )

        logger.info("Query returned %s collaborator(s)", len(result))
        assert len(result) == 1
        assert result[0].role.name == "COMMERCIAL"
        logger.info("Role confirmed: %s", result[0].role.name)


class TestGetCollaboratorByIdIntegration:
    """Integration tests for get_collaborator_by_id()."""

    def test_valid_id_returns_correct_collaborator(self, seeded_db, db_session):
        """Real DB lookup by primary key returns correct collaborator."""
        manager = seeded_db["management"]
        commercial = seeded_db["commercial"]
        logger.info("Looking up collaborator by id=%s", commercial.id)

        result = get_collaborator_by_id(
            session=db_session,
            current_user=manager,
            collaborator_id=commercial.id,
        )

        assert result.id == commercial.id
        assert result.email == commercial.email
        logger.info("Collaborator found — email=%s", result.email)

    def test_invalid_id_raises(self, seeded_db, db_session):
        """Non-existent ID raises CollaboratorNotFoundError from real DB."""
        manager = seeded_db["management"]
        logger.info("Looking up non-existent collaborator id=9999")

        with pytest.raises(CollaboratorNotFoundError):
            get_collaborator_by_id(
                session=db_session,
                current_user=manager,
                collaborator_id=9999,
            )
        logger.info("CollaboratorNotFoundError raised as expected")
