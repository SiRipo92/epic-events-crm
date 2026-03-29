"""Unit tests for the collaborator service.

Tests are organised by function:
    - create_collaborator
    - update_collaborator
    - deactivate_collaborator
    - get_collaborators
    - get_collaborator_by_id
"""

from unittest.mock import MagicMock

import pytest

from exceptions import DuplicateEmailError, PermissionDeniedError
from services.collaborator_service import (
    create_collaborator,
    update_collaborator
)


class TestCreateCollaborator:
    """Tests for the create_collaborator service function."""

    # ---------------------------
    # Happy path
    # ---------------------------

    def test_valid_input_creates_collaborator(
        self, management_user, mock_session_empty
    ):
        """Valid input creates a collaborator with correct defaults."""
        result = create_collaborator(
            session=mock_session_empty,
            current_user=management_user,
            first_name="Sophie",
            last_name="Marceau",
            email="sophie.marceau@epicevents.com",
            role_id=2,
            password="initialpassword123",
        )

        assert result.must_change_password is True
        assert result.is_active is True
        assert result.password_hash != "initialpassword123"
        mock_session_empty.add.assert_called_once()
        mock_session_empty.commit.assert_called_once()

    def test_employee_number_is_generated(self, management_user, mock_session_empty):
        """Employoee number is auto-generated in EMP-XXX format."""
        result = create_collaborator(
            session=mock_session_empty,
            current_user=management_user,
            first_name="Sophie",
            last_name="Marceau",
            email="sophie.marceau@epicevents.com",
            role_id=2,
            password="initialpassword123",
        )

        assert result.employee_number == "EMP-001"

    # ---------------------------
    # Sad path
    # ---------------------------

    def test_duplicate_email_raises(self, management_user):
        """Duplicate email raises DuplicateEmailError."""
        session = MagicMock()
        session.query.return_value.filter_by.return_value.first.return_value = (
            MagicMock()
        )

        with pytest.raises(DuplicateEmailError):
            create_collaborator(
                session=session,
                current_user=management_user,
                first_name="Sophie",
                last_name="Marceau",
                email="already.exists@epicevents.com",
                role_id=2,
                password="initialpassword123",
            )

    def test_non_management_caller_raises(self, commercial_user):
        """Non-Management caller raises PermissionDeniedError."""
        session = MagicMock()

        with pytest.raises(PermissionDeniedError):
            create_collaborator(
                session=session,
                current_user=commercial_user,
                first_name="Sophie",
                last_name="Marceau",
                email="sophie.marceau@epicevents.com",
                role_id=2,
                password="initialpassword123",
            )

class TestUpdateCollaborator:
    """Tests for the update_collaborator service function."""

    # ---------------------------
    # Happy path
    # ---------------------------

    def test_valid_update_persists_fields(
            self, management_user, make_collaborator, management_role
    ):
        """Valid update persists changed fields and commits."""
        target = make_collaborator(
            id=2,
            first_name="Bob",
            last_name="Dupont",
            email="bob.dupont@epicevents.com",
            role=management_role,
        )

        session = MagicMock()
        session.query.return_value.filter_by.return_value.first.return_value = None

        result = update_collaborator(
            session=session,
            current_user=management_user,
            collaborator=target,
            first_name="Robert",
        )

        assert result.first_name == "Robert"
        session.commit.assert_called_once()

    # ---------------------------
    # Sad path
    # ---------------------------

    def test_duplicate_email_on_update_raises(
            self, management_user, make_collaborator, management_role
    ):
        """Updating to an existing email raises DuplicateEmailError."""
        target = make_collaborator(
            id=2,
            email="bob.dupont@epicevents.com",
            role=management_role,
        )
        existing = make_collaborator(
            id=3,
            email="already.taken@epicevents.com",
            role=management_role,
        )
        session = MagicMock()
        session.query.return_value.filter_by.return_value.first.return_value = existing

        with pytest.raises(DuplicateEmailError):
            update_collaborator(
                session=session,
                current_user=management_user,
                collaborator=target,
                email="already.taken@epicevents.com",
            )

    def test_non_management_caller_raises(
            self, commercial_user, make_collaborator, management_role
    ):
        """Non-Management caller raises PermissionDeniedError."""
        target = make_collaborator(
            id=2,
            email="bob.dupont@epicevents.com",
            role=management_role,
        )
        session = MagicMock()

        with pytest.raises(PermissionDeniedError):
            update_collaborator(
                session=session,
                current_user=commercial_user,
                collaborator=target,
                first_name="Robert",
            )
