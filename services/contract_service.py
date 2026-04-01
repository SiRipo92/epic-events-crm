"""
Contract service.

Handles all contract management operations — creation, editing,
status transitions, and retrieval. All write operations require
Management role.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from exceptions import (
    ClientNotFoundError,
    ContractNotEditableError,
    InvalidStatusTransitionError,
)
from models.client import Client
from models.collaborator import Collaborator
from models.contract import Contract, ContractStatus
from permissions.decorators import require_role

# ── Public Interface ─────────────────────────────────────────────────────────────────


@require_role("MANAGEMENT")
def create_contract(
    session: Session,
    current_user: Collaborator,  # noqa: ARG001 — consumed by @require_role
    client_id: int,
    commercial_id: int,
    total_amount: Decimal,
) -> Contract:
    """Create a new contract linked to an existing client.

    Args:
        session: SQLAlchemy database session.
        current_user: The authenticated Management collaborator.
        client_id: FK reference to the Client.
        commercial_id: FK reference to the Commercial collaborator.
        total_amount: The full agreed contract value.

    Returns:
        Contract: The newly created contract instance.

    Raises:
        PermissionDeniedError: If current_user is not Management.
        ClientNotFoundError: If client does not exist.
    """
    # Step 1 — validate client exists
    client = session.get(Client, client_id)
    if not client:
        raise ClientNotFoundError(f"No client found with ID {client_id}.")

    # Step 2 — build contract
    contract = Contract()
    contract.client_id = client_id
    contract.commercial_id = commercial_id
    contract.total_amount = total_amount
    contract.remaining_amount = total_amount
    contract.status = ContractStatus.DRAFT

    session.add(contract)
    session.commit()

    return contract


@require_role("MANAGEMENT")
def edit_contract(
    session: Session,
    current_user: Collaborator,  # noqa: ARG001 — consumed by @require_role
    contract: Contract,
    total_amount: Decimal | None = None,
    client_id: int | None = None,
    commercial_id: int | None = None,
) -> Contract:
    """Edit a contract in DRAFT status.

    Args:
        session: SQLAlchemy database session.
        current_user: The authenticated Management collaborator.
        contract: The Contract instance to edit.
        total_amount: New total amount, or None to leave unchanged.
        client_id: New client FK, or None to leave unchanged.
        commercial_id: New commercial FK, or None to leave unchanged.

    Returns:
        Contract: The updated contract instance.

    Raises:
        PermissionDeniedError: If current_user is not Management.
        ContractNotEditableError: If contract status is not DRAFT.
    """
    # Step 1 — check contract is editable
    if contract.status != ContractStatus.DRAFT:
        raise ContractNotEditableError("Only DRAFT contracts can be edited.")

    # Step 2 — apply updates
    if total_amount is not None:
        contract.total_amount = total_amount

    if client_id is not None:
        contract.client_id = client_id

    if commercial_id is not None:
        contract.commercial_id = commercial_id

    session.commit()
    return contract


@require_role("MANAGEMENT")
def submit_for_signature(
    session: Session,
    current_user: Collaborator,  # noqa: ARG001 — consumed by @require_role
    contract: Contract,
) -> Contract:
    """Transition contract from DRAFT to PENDING.

    Args:
        session: SQLAlchemy database session.
        current_user: The authenticated Management collaborator.
        contract: The Contract instance to transition.

    Returns:
        Contract: The updated contract instance.

    Raises:
        PermissionDeniedError: If current_user is not Management.
        InvalidStatusTransitionError: If contract is not in DRAFT status.
    """
    if contract.status != ContractStatus.DRAFT:
        raise InvalidStatusTransitionError(
            f"Cannot submit for signature: contract status is "
            f"{contract.status.value}, expected DRAFT."
        )

    contract.status = ContractStatus.PENDING
    session.commit()
    return contract

@require_role("MANAGEMENT")
def record_client_signature(
    session: Session,
    current_user: Collaborator,  # noqa: ARG001 — consumed by @require_role
    contract: Contract,
) -> Contract:
    """Transition contract from PENDING to SIGNED.

    Args:
        session: SQLAlchemy database session.
        current_user: The authenticated Management collaborator.
        contract: The Contract instance to transition.

    Returns:
        Contract: The updated contract instance.

    Raises:
        PermissionDeniedError: If current_user is not Management.
        InvalidStatusTransitionError: If contract is not PENDING.
    """
    if contract.status != ContractStatus.PENDING:
        raise InvalidStatusTransitionError(
            f"Cannot record signature: contract status is "
            f"{contract.status.value}, expected PENDING."
        )

    contract.status = ContractStatus.SIGNED
    session.commit()
    return contract
