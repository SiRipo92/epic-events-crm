"""
Collaborator service.

Handles all collaborator management operations — creation, update,
deactivation, and retrieval. All functions require Management role
via the @require_role decorator.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from exceptions import DuplicateEmailError
from models.collaborator import Collaborator
from permissions.decorators import require_role

# ── Collaborator creation helpers ─────────────────────────────────────────────────────


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

    # Step 3 - create the collaborator
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
