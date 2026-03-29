"""
Collaborator service.

Handles all collaborator management operations — creation, update,
deactivation, and retrieval. All functions require Management role
via the @require_role decorator.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from exceptions import DuplicateEmailError, ReassignmentRequiredError
from models.client import Client
from models.collaborator import Collaborator
from models.contract import Contract, ContractStatus
from models.event import Event
from models.role import Role
from permissions.decorators import require_role
from services.auth_service import _delete_session_file

# ── Collaborator helpers ─────────────────────────────────────────────────────


def _generate_employee_number(session: Session) -> str:
    """Generate the next sequential employee number.

    Counts all collaborators regardless of active status to ensure
    numbers are never reused after deactivation.

    Args:
        session: SQLAlchemy database session.

    Returns:
        str: Employee number in EMP-XXX format.
    """
    count = session.query(Collaborator).count()
    return f"EMP-{count + 1:03d}"


def _has_active_dossiers(dossiers: dict) -> bool:
    """
    Check if any active dossiers exist.

    Args:
        dossiers: Dict of dossier lists.

    Returns:
        bool: True if any dossier list is non-empty.
    """
    return any(dossiers.values())


def get_active_dossiers(session: Session, collaborator: Collaborator) -> dict:
    """
    Retrieve all active dossiers linked to a collaborator.

    Args:
        session: SQLAlchemy database session.
        collaborator: The collaborator to inspect.

    Returns:
        dict: {
            "clients": list[Client],
            "contracts": list[Contract],
            "events": list[Event],
        }
    """
    # ── Clients ────────────────────────────────────────────────
    clients = (
        session.query(Client).filter(Client.commercial_id == collaborator.id).all()
    )

    # ── Contracts (exclude CANCELLED + PAID_IN_FULL) ───────────
    contracts = (
        session.query(Contract)
        .filter(
            Contract.commercial_id == collaborator.id,
            Contract.status.notin_(
                [ContractStatus.CANCELLED, ContractStatus.PAID_IN_FULL]
            ),
        )
        .all()
    )

    # ── Events (only active, not cancelled) ────────────────────
    events = (
        session.query(Event)
        .filter(
            Event.support_id == collaborator.id,
            Event.is_cancelled.is_(False),
        )
        .all()
    )

    # ── Return structured result ───────────────────────────────
    return {
        "clients": clients,
        "contracts": contracts,
        "events": events,
    }


# ── Public Interface ─────────────────────────────────────────────────────────────────


@require_role("MANAGEMENT")
def create_collaborator(
    session: Session,
    current_user: Collaborator,  # noqa: ARG001 — consumed by @require_role
    first_name: str,
    last_name: str,
    email: str,
    role_id: int,
    password: str,
) -> Collaborator:
    """
    Create a new collaborator account.

    Args:
        session: SQLAlchemy database session.
        current_user: The authenticated Management collaborator.
                    Consumed by @require_role — not used in the function body.
        first_name: New collaborator's first name.
        last_name: New collaborator's last name.
        email: New collaborator's email address — must be unique.
        role_id: FK reference to the Role table.
        password: Initial plaintext password — will be hashed.

    Returns:
        Collaborator: The newly created collaborator instance.

    Raises:
        PermissionDeniedError: If current_user is not Management.
        DuplicateEmailError: If email already exists.
    """
    # Step 1 — check email uniqueness
    existing = session.query(Collaborator).filter_by(email=email).first()
    if existing:
        raise DuplicateEmailError(
            f"A collaborator with email '{email}' already exists."
        )

    # Step 2 — generate employee number
    employee_number = _generate_employee_number(session)

    # Step 3 - build the collaborator
    collaborator = Collaborator()
    collaborator.employee_number = employee_number
    collaborator.first_name = first_name
    collaborator.last_name = last_name
    collaborator.email = email
    collaborator.role_id = role_id
    collaborator.is_active = True
    collaborator.must_change_password = True
    collaborator.set_password(password)

    session.add(collaborator)
    session.commit()

    return collaborator


@require_role("MANAGEMENT")
def update_collaborator(
    session: Session,
    current_user: Collaborator,  # noqa: ARG001 — consumed by @require_role
    collaborator: Collaborator,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    role_id: int | None = None,
) -> Collaborator:
    """
    Update an existing collaborator account/details.

    Args:
        session: SQLAlchemy database session.
        current_user: The authenticated Management collaborator.
        collaborator: The Collaborator instance to update.
        first_name: New first name, or None to leave unchanged.
        last_name: New last name, or None to leave unchanged.
        email: New email address, or None to leave unchanged.
        phone: New phone number, or None to leave unchanged.
        role_id: New role FK, or None to leave unchanged.

    Returns:
        Collaborator: The updated collaborator instance.

    Raises:
        PermissionDeniedError: If current_user is not Management.
        DuplicateEmailError: If new email already belongs to another collaborator.
    """
    if first_name is not None:
        collaborator.first_name = first_name

    if last_name is not None:
        collaborator.last_name = last_name

    if email is not None:
        existing = session.query(Collaborator).filter_by(email=email).first()
        if existing and existing.id != collaborator.id:
            raise DuplicateEmailError(
                f"A collaborator with email '{email}' already exists."
            )
        collaborator.email = email

    if phone is not None:
        collaborator.phone = phone

    if role_id is not None:
        collaborator.role_id = role_id

    session.commit()
    return collaborator


@require_role("MANAGEMENT")
def deactivate_collaborator(
    session: Session,
    current_user: Collaborator,  # noqa: ARG001
    collaborator: Collaborator,
) -> None:
    """
    Deactivate a collaborator after ensuring no active dossiers remain.

    Raises:
        ReassignmentRequiredError: If active dossiers exist.
    """
    # Step 1 — retrieve active dossiers
    dossiers = get_active_dossiers(
        session=session,
        collaborator=collaborator,
    )

    # Step 2 - enforce reassignment rule
    if _has_active_dossiers(dossiers):
        # Pass the full dossiers dict for detailed error handling
        raise ReassignmentRequiredError(dossiers=dossiers)

    # Step 3 - deactivate collaborator
    collaborator.is_active = False

    # Step 4 - cleanup session
    _delete_session_file()

    # Step 5 — persist changes
    session.commit()


@require_role("MANAGEMENT")
def get_collaborators(
    session: Session,
    current_user: Collaborator,  # noqa: ARG001 — consumed by @require_role
    role: str | None = None,
    is_active: bool | None = None,
) -> list[Collaborator]:
    """
    Return all collaborators, optionally filtered by role or active status.

    Args:
        session: SQLAlchemy database session.
        current_user: The authenticated Management collaborator.
        role: Optional role name to filter by e.g. 'MANAGEMENT'.
        is_active: Optional active status filter.

    Returns:
        list[Collaborator]: Matching collaborators.

    Raises:
        PermissionDeniedError: If current_user is not Management.
    """
    query = session.query(Collaborator)

    if role is not None:
        query = query.join(Role).filter(Role.name == role)

    if is_active is not None:
        query = query.filter(Collaborator.is_active == is_active)

    results: list[Collaborator] = query.all()  # type: ignore[assignment]
    return results
