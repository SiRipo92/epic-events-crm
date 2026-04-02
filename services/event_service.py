"""
Event service.

Handles all event management operations — creation, support assignment,
update, and retrieval.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from exceptions import ContractNotEligibleError, PermissionDeniedError
from models.collaborator import Collaborator
from models.contract import Contract, ContractStatus
from models.event import Event
from permissions.decorators import require_role

# ── Public Interface ─────────────────────────────────────────────────────────────────


@require_role("COMMERCIAL")
def create_event(
    session: Session,
    current_user: Collaborator,
    contract: Contract,
    title: str,
    start_date: datetime,
    end_date: datetime,
    location_street: str | None = None,
    location_zip: str | None = None,
    location_city: str | None = None,
    location_country: str | None = None,
    attendees: int = 0,
    notes: str | None = None,
) -> Event:
    """Create a new event linked to a DEPOSIT_RECEIVED contract.

    Args:
        session: SQLAlchemy database session.
        current_user: The authenticated Commercial collaborator.
        contract: The Contract instance to link the event to.
        title: Event title.
        start_date: Event start date and time.
        end_date: Event end date and time.
        location_street: Optional street address.
        location_zip: Optional zip code.
        location_city: Optional city.
        location_country: Optional country.
        attendees: Expected number of attendees.
        notes: Optional notes.

    Returns:
        Event: The newly created event instance.

    Raises:
        PermissionDeniedError: If current_user is not Commercial or
                               does not own the contract.
        ContractNotEligibleError: If contract status is not
                                  DEPOSIT_RECEIVED.
    """
    # Step 1 - Ownership check
    if contract.commercial_id != current_user.id:
        raise PermissionDeniedError(
            "You can only create events from your own contracts."
        )

    # Step 2 - Validate contract status
    if contract.status != ContractStatus.DEPOSIT_RECEIVED:
        raise ContractNotEligibleError(
            f"Cannot create event: Contract status is "
            f"{contract.status.value}, expected: DEPOSIT_RECEIVED."
        )

    # Step 3 - Build event
    event = Event()
    event.contract_id = contract.id
    event.title = title
    event.start_date = start_date
    event.end_date = end_date
    event.location_street = location_street
    event.location_zip = location_zip
    event.location_city = location_city
    event.location_country = location_country
    event.attendees = attendees
    event.notes = notes
    event.support_id = None

    session.add(event)
    session.commit()

    return event
