"""Unit tests for the Role ORM model."""

import pytest


class TestRoleStr:
    """Tests for the __str__ method."""

    @pytest.mark.parametrize(
        "name",
        [
            "MANAGEMENT",
            "COMMERCIAL",
            "SUPPORT",
        ],
    )
    def test_str_returns_name(self, make_role, name):
        """Return the role name as string representation."""
        r = make_role(name=name)
        assert str(r) == name


class TestRoleAttributes:
    """Tests for Role attribute integrity."""

    def test_management_role_name(self, management_role):
        """Management role has correct name."""
        assert management_role.name == "MANAGEMENT"

    def test_commercial_role_name(self, commercial_role):
        """Commercial role has correct name."""
        assert commercial_role.name == "COMMERCIAL"

    def test_support_role_name(self, support_role):
        """Support role has correct name."""
        assert support_role.name == "SUPPORT"

    def test_role_has_collaborators_list(self, management_role):
        """Role initialises with an empty collaborators relationship."""
        assert hasattr(management_role, "collaborators")
