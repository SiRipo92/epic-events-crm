"""Permission decorators for the Epic Events CRM service layer."""

from functools import wraps

from exceptions import PermissionDeniedError


def require_role(*allowed_roles: str):
    """Restrict a service function to collaborators with an allowed role.

    Args:
        *allowed_roles: One or more role name strings e.g. "MANAGEMENT",
                        "COMMERCIAL", "SUPPORT".

    Usage:
        @require_role("MANAGEMENT")
        def create_collaborator(session, current_user, ...):
            ...

        @require_role("MANAGEMENT", "COMMERCIAL")
        def get_clients(session, current_user, ...):
            ...

    Raises:
        PermissionDeniedError: If current_user.role.name is not in allowed_roles.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # current_user is always the second positional argument
            # after session in every service function
            current_user = kwargs.get("current_user") or (
                args[1] if len(args) > 1 else None
            )
            if current_user is None:
                raise PermissionDeniedError("No authenticated user found.")
            if current_user.role.name not in allowed_roles:
                raise PermissionDeniedError(
                    f"Access denied. Allowed roles: {', '.join(allowed_roles)}. "
                    f"Your role: {current_user.role.name}."
                )
            return func(*args, **kwargs)

        return wrapper

    return decorator
