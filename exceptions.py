"""Custom domain exceptions for the Epic Events CRM."""


class PermissionDeniedError(Exception):
    """Raised when a collaborator attempts an action they are not authorized to perform."""

    def __init__(self, message: str = "You do not have permission to perform this action."):
        self.message = message
        super().__init__(self.message)


class AuthenticationError(Exception):
    """Raised when authentication fails (invalid credentials, deactivated account)."""

    def __init__(self, message: str = "Authentication failed."):
        self.message = message
        super().__init__(self.message)


class ReassignmentRequiredError(Exception):
    """Raised when a collaborator cannot be deactivated because they still have active dossiers.

    Attributes:
        active_dossiers: A dict describing the unresolved dossiers.
    """

    def __init__(self, message: str, active_dossiers: dict | None = None):
        self.message = message
        self.active_dossiers = active_dossiers or {}
        super().__init__(self.message)
