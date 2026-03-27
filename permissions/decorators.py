"""Role-based permission decorators for the Epic Events CRM.

These decorators enforce role checks at the CLI command level.
"""

from functools import wraps
from typing import Callable

from exceptions import PermissionDeniedError


# Lazy import to avoid circular imports
def _get_current_user():
    """Return the currently authenticated collaborator, or None if not logged in."""
    try:
        from services.auth_service import get_current_user
        return get_current_user()
    except Exception:
        return None


def require_role(*allowed_roles: str) -> Callable:
    """Decorator that restricts a CLI command to collaborators with specific role(s).

    Args:
        *allowed_roles: Role names that are permitted to execute the command.
            e.g. @require_role("MANAGEMENT") or @require_role("MANAGEMENT", "COMMERCIAL")

    Raises:
        PermissionDeniedError: If the current user does not have an allowed role.

    Usage:
        @require_role("MANAGEMENT")
        def delete_collaborator(collaborator_id: int, current_user: Collaborator):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, current_user=None, **kwargs):
            if current_user is None:
                current_user = _get_current_user()

            if current_user is None:
                raise PermissionDeniedError("You must be logged in to perform this action.")

            if current_user.role.value not in allowed_roles:
                raise PermissionDeniedError(
                    f"Permission denied. Required role(s): {', '.join(allowed_roles)}. "
                    f"Your role: {current_user.role.value}."
                )

            return func(*args, current_user=current_user, **kwargs)

        return wrapper

    return decorator
