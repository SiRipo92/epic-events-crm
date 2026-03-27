"""
Domain exceptions for the Epic Events CRM.

All custom exceptions are defined here and imported wherever needed.
No business logic lives in this file — exceptions are raised by the
service layer and caught by the CLI/view layer for display.

Exception hierarchy:
    EpicEventsError                 ← base for all custom exceptions
    ├── AuthenticationError         ← login failures, expired sessions
    ├── MustChangePasswordError     ← first-login password gate
    ├── PermissionDeniedError       ← role or ownership check failed
    ├── ValidationError             ← invalid input before a write
    ├── NotFoundError               ← base for entity not found
    │   ├── CollaboratorNotFoundError
    │   ├── ClientNotFoundError
    │   ├── ContractNotFoundError
    │   └── EventNotFoundError
    ├── ConflictError               ← base for uniqueness violations
    │   └── DuplicateEmailError
    ├── ContractError               ← base for contract rule violations
    │   ├── ContractNotEligibleError
    │   ├── ContractNotEditableError
    │   └── InvalidStatusTransitionError
    ├── PaymentError
    │   └── PaymentExceedsBalanceError
    ├── ReassignmentRequiredError   ← deactivation blocked
    ├── InvalidAssignmentError      ← wrong role assigned to event
    └── SchedulingConflictWarning   ← non-blocking, prompts confirmation
"""


class EpicEventsError(Exception):
    """Base exception for all Epic Events domain errors.

    All custom exceptions inherit from this class so callers can catch
    any domain error with a single except clause if needed.
    """

    pass


# ── Authentication & session ───────────────────────────────────────────────────


class AuthenticationError(EpicEventsError):
    """Raised when login fails or a session is invalid or expired.

    Used for:
        - Unknown email address
        - Wrong password (same message as unknown email — no enumeration)
        - Deactivated account
        - Expired JWT token
        - Invalid or missing session file
    """

    pass


class MustChangePasswordError(EpicEventsError):
    """Raised when a collaborator logs in with must_change_password = True.

    Intercepts before the main menu is shown and forces the password
    change flow to complete before any CRM access is granted.
    """

    pass


# ── Authorisation ──────────────────────────────────────────────────────────────


class PermissionDeniedError(EpicEventsError):
    """Raised when a collaborator attempts an action outside their role.

    Raised by:
        - @require_role decorator when role is not in the allowed list
        - Ownership checks (e.g. commercial accessing another commercial's client)
    """

    pass


# ── Validation ─────────────────────────────────────────────────────────────────


class ValidationError(EpicEventsError):
    """Raised when input data fails validation before a write operation.

    Used for missing required fields, invalid formats, or values that
    violate business rules before reaching the database.
    """

    pass


# ── Entity not found ───────────────────────────────────────────────────────────


class NotFoundError(EpicEventsError):
    """Base exception for entity lookup failures.

    Raised when a requested record does not exist or is outside the
    current user's scope.
    """

    pass


class CollaboratorNotFoundError(NotFoundError):
    """Raised when a collaborator cannot be found by the given identifier."""

    pass


class ClientNotFoundError(NotFoundError):
    """Raised when a client cannot be found or is outside the user's scope."""

    pass


class ContractNotFoundError(NotFoundError):
    """Raised when a contract cannot be found or is outside the user's scope."""

    pass


class EventNotFoundError(NotFoundError):
    """Raised when an event cannot be found or is outside the user's scope."""

    pass


# ── Uniqueness conflicts ────────────────────────────────────────────────────────


class ConflictError(EpicEventsError):
    """Base exception for uniqueness constraint violations."""

    pass


class DuplicateEmailError(ConflictError):
    """Raised when a collaborator or client email already exists in the system."""

    pass


# ── Contract rules ─────────────────────────────────────────────────────────────


class ContractError(EpicEventsError):
    """Base exception for contract rule violations."""

    pass


class ContractNotEligibleError(ContractError):
    """Raised when an event creation is attempted on a non-DEPOSIT_RECEIVED contract.

    The contract must have status DEPOSIT_RECEIVED before an event
    can be created against it.
    """

    pass


class ContractNotEditableError(ContractError):
    """Raised when an edit is attempted on a contract past DRAFT status.

    Once a contract has moved beyond DRAFT, its fields are locked.
    Only status transitions are permitted via dedicated service methods.
    """

    pass


class InvalidStatusTransitionError(ContractError):
    """Raised when a contract status transition is attempted from an invalid state.

    Examples:
        - Submitting for signature when status is not DRAFT
        - Recording a signature when status is not PENDING
        - Recording a deposit when status is not SIGNED
        - Cancelling an already CANCELLED or PAID_IN_FULL contract
    """

    pass


# ── Payment rules ──────────────────────────────────────────────────────────────


class PaymentError(EpicEventsError):
    """Base exception for payment rule violations."""

    pass


class PaymentExceedsBalanceError(PaymentError):
    """Raised when a recorded payment would reduce remaining_amount below zero.

    The service layer catches this before any write occurs — the
    database is never updated when this exception is raised.
    """

    pass


# ── Collaborator deactivation ──────────────────────────────────────────────────


class ReassignmentRequiredError(EpicEventsError):
    """Raised when deactivation is attempted with active dossiers still assigned.

    Deactivation is blocked until all clients, open contracts, and
    non-cancelled events belonging to the collaborator are reassigned
    to another collaborator.
    """

    pass


# ── Event assignment ───────────────────────────────────────────────────────────


class InvalidAssignmentError(EpicEventsError):
    """Raised when a non-Support collaborator is assigned to an event.

    Only collaborators with role.name == 'SUPPORT' can be assigned
    as the support member for an event.
    """

    pass


class SchedulingConflictWarning(EpicEventsError):
    """Raised when a support member already has an event on the target date.

    This is intentionally non-blocking — it is caught by the CLI layer
    and presented as a confirmation prompt. Management can choose to
    force assign despite the conflict or select a different member.
    """

    pass
