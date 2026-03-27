"""Unit tests for the @require_role permission decorator."""

import pytest

from exceptions import PermissionDeniedError
from permissions.decorators import require_role

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_service(allowed_roles):
    """Return a minimal service function decorated with require_role."""

    @require_role(*allowed_roles)
    def service_function(session, current_user):
        """Return a sentinel value to confirm the function ran."""
        return "executed"

    return service_function


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestRequireRoleSingleRole:
    """Tests for @require_role with a single allowed role."""

    def test_correct_role_passes(self, management_user):
        """Management user can call a MANAGEMENT-only function."""
        fn = _make_service(["MANAGEMENT"])
        result = fn(session=None, current_user=management_user)
        assert result == "executed"

    def test_wrong_role_raises(self, commercial_user):
        """Commercial user cannot call a MANAGEMENT-only function."""
        fn = _make_service(["MANAGEMENT"])
        with pytest.raises(PermissionDeniedError):
            fn(session=None, current_user=commercial_user)

    def test_support_blocked_from_management_function(self, support_user):
        """Support user cannot call a MANAGEMENT-only function."""
        fn = _make_service(["MANAGEMENT"])
        with pytest.raises(PermissionDeniedError):
            fn(session=None, current_user=support_user)


class TestRequireRoleMultipleRoles:
    """Tests for @require_role with multiple allowed roles."""

    def test_first_allowed_role_passes(self, management_user):
        """Management user can call a MANAGEMENT+COMMERCIAL function."""
        fn = _make_service(["MANAGEMENT", "COMMERCIAL"])
        result = fn(session=None, current_user=management_user)
        assert result == "executed"

    def test_second_allowed_role_passes(self, commercial_user):
        """Commercial user can call a MANAGEMENT+COMMERCIAL function."""
        fn = _make_service(["MANAGEMENT", "COMMERCIAL"])
        result = fn(session=None, current_user=commercial_user)
        assert result == "executed"

    def test_excluded_role_raises(self, support_user):
        """Support user cannot call a MANAGEMENT+COMMERCIAL function."""
        fn = _make_service(["MANAGEMENT", "COMMERCIAL"])
        with pytest.raises(PermissionDeniedError):
            fn(session=None, current_user=support_user)


class TestRequireRoleAllRoles:
    """Tests for @require_role when all three roles are permitted."""

    @pytest.mark.parametrize(
        "user_fixture",
        [
            "management_user",
            "commercial_user",
            "support_user",
        ],
    )
    def test_all_roles_pass(self, request, user_fixture):
        """All three roles can call a function open to everyone."""
        fn = _make_service(["MANAGEMENT", "COMMERCIAL", "SUPPORT"])
        user = request.getfixturevalue(user_fixture)
        result = fn(session=None, current_user=user)
        assert result == "executed"


class TestRequireRoleErrorMessage:
    """Tests for the PermissionDeniedError message content."""

    def test_error_message_contains_required_role(self, support_user):
        """Test PermissionDeniedError message names the required role."""
        fn = _make_service(["MANAGEMENT"])
        with pytest.raises(PermissionDeniedError) as exc_info:
            fn(session=None, current_user=support_user)
        assert "MANAGEMENT" in str(exc_info.value)

    def test_error_message_contains_user_role(self, support_user):
        """Test PermissionDeniedError message names the user's actual role."""
        fn = _make_service(["MANAGEMENT"])
        with pytest.raises(PermissionDeniedError) as exc_info:
            fn(session=None, current_user=support_user)
        assert "SUPPORT" in str(exc_info.value)


class TestRequireRoleNoUser:
    """Tests for missing current_user argument."""

    def test_none_user_raises(self):
        """None as current_user raises PermissionDeniedError."""
        fn = _make_service(["MANAGEMENT"])
        with pytest.raises(PermissionDeniedError):
            fn(session=None, current_user=None)

    def test_missing_user_raises(self):
        """Calling without current_user raises PermissionDeniedError."""
        fn = _make_service(["MANAGEMENT"])
        with pytest.raises((PermissionDeniedError, TypeError)):
            fn(session=None)


class TestRequireRolePreservesFunction:
    """Tests that the decorator preserves the wrapped function's metadata."""

    def test_function_name_preserved(self):
        """Decorated function retains its original __name__."""

        @require_role("MANAGEMENT")
        def my_service(session, current_user):
            """Do something."""
            return "done"

        assert my_service.__name__ == "my_service"

    def test_function_docstring_preserved(self):
        """Decorated function retains its original docstring."""

        @require_role("MANAGEMENT")
        def my_service(session, current_user):
            """Do something."""
            return "done"

        assert my_service.__doc__ == "Do something."
