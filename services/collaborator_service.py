"""Business logic for collaborator management in the Epic Events CRM."""

import os
from pathlib import Path

from models.collaborator import Collaborator
from models.client import Client, ClientStatus
from models.contract import Contract, ContractStatus
from models.event import Event
from db.session import get_session
from exceptions import ReassignmentRequiredError


SESSION_DIR = Path.home() / ".epic_events"
SESSION_FILE = SESSION_DIR / "session"


def get_active_dossiers(collaborator_id: int) -> dict:
    """Return all active dossiers (clients, contracts, events) linked to a collaborator.

    An active dossier is:
      - A client where commercial_id = collaborator.id
      - An open contract where commercial_id = collaborator.id AND status NOT IN (CANCELLED, PAID_IN_FULL)
      - An active event where support_id = collaborator.id AND is_cancelled = False

    Args:
        collaborator_id: The ID of the collaborator to check.

    Returns:
        A dict with keys 'clients', 'contracts', 'events', each containing a list
        of active dossiers (empty lists if none found).
    """
    with get_session() as session:
        # Active clients assigned to this collaborator
        active_clients = (
            session.query(Client)
            .filter(Client.commercial_id == collaborator_id)
            .all()
        )

        # Active contracts: not CANCELLED and not PAID_IN_FULL
        active_contracts = (
            session.query(Contract)
            .filter(
                Contract.commercial_id == collaborator_id,
                Contract.status.notin_([ContractStatus.CANCELLED, ContractStatus.PAID_IN_FULL]),
            )
            .all()
        )

        # Active events: not cancelled
        active_events = (
            session.query(Event)
            .filter(
                Event.support_id == collaborator_id,
                Event.is_cancelled.is_(False),
            )
            .all()
        )

        return {
            "clients": [
                {"id": c.id, "name": c.full_name, "email": c.email}
                for c in active_clients
            ],
            "contracts": [
                {"id": c.id, "status": c.status.value, "total_amount": str(c.total_amount)}
                for c in active_contracts
            ],
            "events": [
                {"id": e.id, "title": e.title, "start_date": str(e.start_date)}
                for e in active_events
            ],
        }


def deactivate_collaborator(collaborator_id: int, current_user: Collaborator) -> dict:
    """Deactivate a collaborator after verifying all dossiers are reassigned.

    Only MANAGEMENT role can deactivate collaborators. The collaborator being
    deactivated must have no active clients, open contracts, or un-cancelled events.

    Args:
        collaborator_id: The ID of the collaborator to deactivate.
        current_user: The currently authenticated collaborator (must have MANAGEMENT role).

    Returns:
        A dict with a 'success' message.

    Raises:
        ReassignmentRequiredError: If the collaborator has unresolved active dossiers.
    """
    dossiers = get_active_dossiers(collaborator_id)

    unresolved = []
    if dossiers["clients"]:
        unresolved.append(f"{len(dossiers['clients'])} active client(s)")
    if dossiers["contracts"]:
        unresolved.append(f"{len(dossiers['contracts'])} open contract(s)")
    if dossiers["events"]:
        unresolved.append(f"{len(dossiers['events'])} active event(s)")

    if unresolved:
        raise ReassignmentRequiredError(
            f"Cannot deactivate collaborator {collaborator_id}: "
            f"{', '.join(unresolved)} must be reassigned first.",
            active_dossiers=dossiers,
        )

    with get_session() as session:
        collaborator = session.query(Collaborator).filter_by(id=collaborator_id).first()
        if not collaborator:
            raise ValueError(f"Collaborator {collaborator_id} not found.")

        collaborator.is_active = False
        session.commit()

    # Delete session file if it exists (logout the collaborator)
    if SESSION_FILE.exists():
        try:
            SESSION_FILE.unlink()
        except OSError:
            pass  # Ignore file deletion errors

    return {
        "success": True,
        "message": f"Collaborator {collaborator_id} ({collaborator.full_name}) has been deactivated.",
    }
