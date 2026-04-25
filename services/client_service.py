"""
Client service.

Handles all client management operations — creation, update,
deactivation, and retrieval.

For creation/update, this requires a 'Commercial' role.
All roles have full read access via get_all_clients / get_client_by_id.
get_clients_for_user remains available for scoped "my records" filters.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.client import Client
from models.collaborator import Collaborator
from models.contract import Contract
from models.event import Event
from permissions.decorators import require_role
from utils.exceptions import (
    ClientNotFoundError,
    DuplicateEmailError,
    PermissionDeniedError,
)
from utils.validation import validate_email

# ── Client helpers ──────────────────────────────────────────────────────────────────


def _client_not_found(client_id: int) -> ClientNotFoundError:
    """Return a ClientNotFoundError for the given ID."""
    return ClientNotFoundError(f"No client found with ID {client_id}.")


# ── Public Interface ─────────────────────────────────────────────────────────────────


@require_role("COMMERCIAL")
def create_client(
    session: Session,
    current_user: Collaborator,
    first_name: str,
    last_name: str,
    email: str,
    phone: str | None = None,
    company_name: str | None = None,
) -> Client:
    """Create a new client profile.

    Args:
        session: SQLAlchemy database session.
        current_user: The authenticated Commercial collaborator.
        first_name: Client's first name.
        last_name: Client's last name.
        email: Client's email address — must be unique.
        phone: Optional phone number.
        company_name: Optional company name.

    Returns:
        Client: The newly created client instance.

    Raises:
        PermissionDeniedError: If current_user is not Commercial.
        DuplicateEmailError: If email already exists.
        ValidationError: If email format is invalid.
    """
    # Step 1 — validate email format
    validate_email(email)

    # Step 2 — check email uniqueness
    existing = session.query(Client).filter_by(email=email).first()
    if existing:
        raise DuplicateEmailError(f"A client with email '{email}' already exists.")

    # Step 3 — build client
    client = Client()
    client.first_name = first_name
    client.last_name = last_name
    client.email = email
    client.phone = phone
    client.company_name = company_name
    client.commercial_id = current_user.id

    session.add(client)
    session.commit()

    return client


@require_role("COMMERCIAL")
def update_client(
    session: Session,
    current_user: Collaborator,
    client: Client,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    company_name: str | None = None,
) -> Client:
    """Update an existing client profile.

    Args:
        session: SQLAlchemy database session.
        current_user: The authenticated Commercial collaborator.
        client: The Client instance to update.
        first_name: New first name, or None to leave unchanged.
        last_name: New last name, or None to leave unchanged.
        email: New email address, or None to leave unchanged.
        phone: New phone number, or None to leave unchanged.
        company_name: New company name, or None to leave unchanged.

    Returns:
        Client: The updated client instance.

    Raises:
        PermissionDeniedError: If current_user is not Commercial or
                               does not own this client.
        DuplicateEmailError: If new email belongs to another client.
        ValidationError: If email format is invalid.
    """
    # Step 1 — ownership check
    if client.commercial_id != current_user.id:
        raise PermissionDeniedError("You can only update your own clients.")

    # Step 2 — apply updates
    if first_name is not None:
        client.first_name = first_name

    if last_name is not None:
        client.last_name = last_name

    if email is not None:
        validate_email(email)
        existing = session.query(Client).filter_by(email=email).first()
        if existing and existing.id != client.id:
            raise DuplicateEmailError(f"A client with email '{email}' already exists.")
        client.email = email

    if phone is not None:
        client.phone = phone

    if company_name is not None:
        client.company_name = company_name

    session.commit()
    return client


@require_role("MANAGEMENT", "COMMERCIAL", "SUPPORT")
def get_clients_for_user(
    session: Session,
    current_user: Collaborator,
) -> list[Client]:
    """Return clients scoped to the current user's role.

    Args:
        session: SQLAlchemy database session.
        current_user: The authenticated collaborator.

    Returns:
        list[Client]: Clients visible to the current user based on role.

    Raises:
        PermissionDeniedError: If current_user has no valid role.
    """
    if current_user.role.name == "MANAGEMENT":
        return list(session.scalars(select(Client)).all())

    if current_user.role.name == "COMMERCIAL":
        return list(
            session.scalars(
                select(Client).where(Client.commercial_id == current_user.id)
            ).all()
        )

    # SUPPORT
    return list(
        session.scalars(
            select(Client)
            .join(Client.contracts)
            .join(Event, Event.contract_id == Contract.id)
            .where(Event.support_id == current_user.id)
        ).all()
    )


@require_role("MANAGEMENT", "COMMERCIAL", "SUPPORT")
def get_client_by_id(
    session: Session,
    current_user: Collaborator,  # noqa: ARG001 — consumed by @require_role
    client_id: int,
) -> Client:
    """Return a single client by ID. All roles have read access.

    Raises:
        ClientNotFoundError: If client does not exist.
    """
    client: Client | None = session.get(Client, client_id)
    if not client:
        raise _client_not_found(client_id)
    return client


@require_role("MANAGEMENT", "COMMERCIAL", "SUPPORT")
def get_all_clients(
    session: Session,
    current_user: Collaborator,  # noqa: ARG001 — consumed by @require_role
) -> list[Client]:
    """Return all clients. All roles have read access to all clients.

    Args:
        session: SQLAlchemy database session.
        current_user: Any authenticated collaborator.

    Returns:
        list[Client]: All clients in the system.
    """
    return list(session.scalars(select(Client)).all())
