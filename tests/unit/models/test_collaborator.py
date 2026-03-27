"""Unit tests for the Collaborator ORM model.

These tests verify Collaborator model logic without requiring a database.
Uses pytest fixtures from conftest.py.
"""

import pytest
from unittest.mock import MagicMock

from models.collaborator import Collaborator, Role


class TestCollaboratorModel:
    """Unit tests for the Collaborator model."""

    def test_full_name_property(self):
        """full_name returns first_name + last_name."""
        collab = Collaborator(
            id=1,
            first_name="Marie",
            last_name="Dupont",
            email="marie@example.com",
            password_hash="hashed",
            role=Role.COMMERCIAL,
            is_active=True,
        )
        assert collab.full_name == "Marie Dupont"

    def test_full_name_formal_property(self):
        """full_name_formal returns LASTNAME, First name."""
        collab = Collaborator(
            id=1,
            first_name="Jean",
            last_name="Martin",
            email="jean@example.com",
            password_hash="hashed",
            role=Role.SUPPORT,
            is_active=True,
        )
        assert collab.full_name_formal == "MARTIN, Jean"

    def test_repr_includes_id_email_role(self):
        """repr contains id, email, and role."""
        collab = Collaborator(
            id=5,
            first_name="Alice",
            last_name="Smith",
            email="alice@epicevents.com",
            password_hash="xyz",
            role=Role.MANAGEMENT,
            is_active=True,
        )
        r = repr(collab)
        assert "id=5" in r
        assert "alice@epicevents.com" in r
        assert "MANAGEMENT" in r

    def test_is_active_default_true(self):
        """New Collaborator instances default to is_active=True."""
        collab = Collaborator(
            id=1,
            first_name="Test",
            last_name="User",
            email="test@example.com",
            password_hash="hash",
            role=Role.COMMERCIAL,
        )
        assert collab.is_active is True

    def test_role_enum_values(self):
        """Role enum has the expected string values."""
        assert Role.MANAGEMENT.value == "MANAGEMENT"
        assert Role.COMMERCIAL.value == "COMMERCIAL"
        assert Role.SUPPORT.value == "SUPPORT"

    def test_collaborator_can_be_deactivated(self):
        """A collaborator can have is_active set to False (deactivated)."""
        collab = Collaborator(
            id=1,
            first_name="Inactive",
            last_name="User",
            email="inactive@example.com",
            password_hash="hash",
            role=Role.COMMERCIAL,
            is_active=False,
        )
        assert collab.is_active is False
