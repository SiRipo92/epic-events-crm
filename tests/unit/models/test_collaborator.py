"""Unit tests for the Collaborator ORM model."""

import pytest


class TestCollaboratorFullName:
    """Tests for full_name and full_name_formal computed properties."""

    @pytest.mark.parametrize(
        "first, last, expected",
        [
            ("Jean", "Durand", "Jean Durand"),
            ("Marie", "Leclerc", "Marie Leclerc"),
            ("Anne", "de la Rue", "Anne de la Rue"),
        ],
    )
    def test_full_name(self, make_collaborator, first, last, expected):
        """Return first name followed by last name."""
        c = make_collaborator(first_name=first, last_name=last)
        assert c.full_name == expected

    @pytest.mark.parametrize(
        "first, last, expected",
        [
            ("Jean", "Durand", "DURAND, Jean"),
            ("Marie", "Leclerc", "LECLERC, Marie"),
            ("Anne", "de la Rue", "DE LA RUE, Anne"),
        ],
    )
    def test_full_name_formal(self, make_collaborator, first, last, expected):
        """Return last name uppercased followed by first name."""
        c = make_collaborator(first_name=first, last_name=last)
        assert c.full_name_formal == expected


class TestCollaboratorPassword:
    """Tests for set_password and verify_password."""

    def test_set_password_does_not_store_plaintext(self, make_collaborator):
        """Stored hash is not equal to the plaintext input."""
        c = make_collaborator()
        c.set_password("securepassword123")
        assert c.password_hash != "securepassword123"

    def test_set_password_stores_bcrypt_hash(self, make_collaborator):
        """Stored hash starts with bcrypt prefix."""
        c = make_collaborator()
        c.set_password("securepassword123")
        assert c.password_hash.startswith("$2b$")

    def test_set_password_uses_cost_factor_12(self, make_collaborator):
        """Stored hash encodes cost factor 12."""
        c = make_collaborator()
        c.set_password("securepassword123")
        assert c.password_hash.startswith("$2b$12$")

    def test_verify_password_correct(self, make_collaborator):
        """Correct password returns True."""
        c = make_collaborator()
        c.set_password("securepassword123")
        assert c.verify_password("securepassword123") is True

    def test_verify_password_wrong(self, make_collaborator):
        """Wrong password returns False."""
        c = make_collaborator()
        c.set_password("securepassword123")
        assert c.verify_password("wrongpassword") is False

    def test_verify_password_empty_string(self, make_collaborator):
        """Empty string does not match a real password."""
        c = make_collaborator()
        c.set_password("securepassword123")
        assert c.verify_password("") is False

    def test_two_hashes_of_same_password_differ(self, make_collaborator):
        """
        Test bcrypt generates a unique salt each time.

        Note -- hashes are never identical.
        """
        c1 = make_collaborator(id=1)
        c2 = make_collaborator(id=2)
        c1.set_password("samepassword")
        c2.set_password("samepassword")
        assert c1.password_hash != c2.password_hash


class TestCollaboratorFlags:
    """Tests for is_active and must_change_password flag behaviour."""

    def test_active_user_is_active(self, management_user):
        """Active collaborator has is_active = True."""
        assert management_user.is_active is True

    def test_inactive_user_is_not_active(self, inactive_user):
        """Deactivated collaborator has is_active = False."""
        assert inactive_user.is_active is False

    def test_first_login_user_must_change_password(self, first_login_user):
        """Newly created collaborator has must_change_password = True."""
        assert first_login_user.must_change_password is True

    def test_existing_user_does_not_need_password_change(self, management_user):
        """Established collaborator has must_change_password = False."""
        assert management_user.must_change_password is False


class TestCollaboratorRoleRelationship:
    """Tests for the role relationship and role.name access."""

    def test_management_user_has_correct_role_name(self, management_user):
        """Management user's role.name is MANAGEMENT."""
        assert management_user.role.name == "MANAGEMENT"

    def test_commercial_user_has_correct_role_name(self, commercial_user):
        """Commercial user's role.name is COMMERCIAL."""
        assert commercial_user.role.name == "COMMERCIAL"

    def test_support_user_has_correct_role_name(self, support_user):
        """Support user's role.name is SUPPORT."""
        assert support_user.role.name == "SUPPORT"


class TestCollaboratorRoleProperties:
    """Tests for is_manager, is_commercial, is_support computed properties."""

    def test_is_manager_true_for_management(self, management_user):
        """Return True when role is MANAGEMENT."""
        assert management_user.is_manager is True

    def test_is_manager_false_for_commercial(self, commercial_user):
        """Return False when role is not MANAGEMENT."""
        assert commercial_user.is_manager is False

    def test_is_commercial_true_for_commercial(self, commercial_user):
        """Return True when role is COMMERCIAL."""
        assert commercial_user.is_commercial is True

    def test_is_commercial_false_for_support(self, support_user):
        """Return False when role is not COMMERCIAL."""
        assert support_user.is_commercial is False

    def test_is_support_true_for_support(self, support_user):
        """Return True when role is SUPPORT."""
        assert support_user.is_support is True

    def test_is_support_false_for_management(self, management_user):
        """Return False when role is not SUPPORT."""
        assert management_user.is_support is False
