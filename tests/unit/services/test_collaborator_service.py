"""Unit tests for the collaborator service.

Tests are organised by function:
    - create_collaborator
    - update_collaborator
    - deactivate_collaborator
    - get_collaborators
    - get_collaborator_by_id
"""
from unittest.mock import MagicMock

from services.collaborator_service import (
create_collaborator,
)

class TestCreateCollaborator:
    """Tests for the create_collaborator service function."""

    def test_valid_input_creates_collaborator(
            self, management_user, management_role
    ):
        """Valid input creates a collaborator with correct defaults."""
        session = MagicMock()
        session.query.return_value.filter_by.return_value.first.return_value = None

        result = create_collaborator(
            session=session,
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
        session.add.assert_called_once()
        session.commit.assert_called_once()
