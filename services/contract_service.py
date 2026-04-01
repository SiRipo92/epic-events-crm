"""
Contract service.

Handles all contract management operations — creation, editing,
status transitions, and retrieval. All write operations require
Management role.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from exceptions import (
    ClientNotFoundError,
    ContractNotEditableError,
    InvalidStatusTransitionError,
    PaymentExceedsBalanceError,
)
from models.client import Client
from models.collaborator import Collaborator
from models.contract import Contract, ContractStatus
from models.event import Event
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


@require_role("MANAGEMENT")
def record_deposit_received(
    session: Session,
    current_user: Collaborator,  # noqa: ARG001
    contract: Contract,
) -> Contract:
    """Transition contract from SIGNED to DEPOSIT_RECEIVED.

    Args:
        session: SQLAlchemy database session.
        current_user: The authenticated Management collaborator.
        contract: The Contract instance to transition.

    Returns:
        Contract: The updated contract instance.

    Raises:
        PermissionDeniedError: If current_user is not Management.
        InvalidStatusTransitionError: If contract is not SIGNED.
    """
    # Step 1 — Validate state
    if contract.status != ContractStatus.SIGNED:
        raise InvalidStatusTransitionError(
            f"Cannot record deposit: contract status is "
            f"{contract.status.value}, expected SIGNED."
        )

    # Step 2 — Apply state change
    contract.deposit_received = True
    contract.status = ContractStatus.DEPOSIT_RECEIVED

    # Step 3 — Persist
    session.commit()
    return contract


@require_role("MANAGEMENT")
def record_payment(
    session: Session,
    current_user: Collaborator,  # noqa: ARG001 — consumed by @require_role
    contract: Contract,
    amount_paid: Decimal,
) -> Contract:
    """Record a payment against a contract and reduce the remaining balance.

    Args:
        session: SQLAlchemy database session.
        current_user: The authenticated Management collaborator.
        contract: The Contract instance to record payment against.
        amount_paid: The payment amount to deduct from remaining_amount.

    Returns:
        Contract: The updated contract instance.

    Raises:
        PermissionDeniedError: If current_user is not Management.
        InvalidStatusTransitionError: If contract is not DEPOSIT_RECEIVED.
        PaymentExceedsBalanceError: If payment would reduce balance below zero.
    """
    # Step 1 — validate status
    if contract.status != ContractStatus.DEPOSIT_RECEIVED:
        raise InvalidStatusTransitionError(
            f"Cannot record payment: contract status is "
            f"{contract.status.value}, expected DEPOSIT_RECEIVED."
        )

    # Step 2 — validate payment amount
    new_balance = contract.remaining_amount - amount_paid
    if new_balance < 0:
        raise PaymentExceedsBalanceError(
            f"Payment of {amount_paid} exceeds remaining balance "
            f"of {contract.remaining_amount}."
        )

    # Step 3 — apply payment
    contract.remaining_amount = new_balance

    # Step 4 — auto-transition to PAID_IN_FULL if balance is zero
    if new_balance == 0:
        contract.status = ContractStatus.PAID_IN_FULL

    session.commit()
    return contract


@require_role("MANAGEMENT")
def cancel_contract(
    session: Session,
    current_user: Collaborator,  # noqa: ARG001 — consumed by @require_role
    contract: Contract,
) -> Contract:
    """Cancel a contract from any non-terminal state.

    Args:
        session: SQLAlchemy database session.
        current_user: The authenticated Management collaborator.
        contract: The Contract instance to cancel.

    Returns:
        Contract: The updated contract instance.

    Raises:
        PermissionDeniedError: If current_user is not Management.
        InvalidStatusTransitionError: If contract is already CANCELLED
                                      or PAID_IN_FULL.
    """
    # Step 1 — check contract is cancellable
    if contract.status in (ContractStatus.CANCELLED, ContractStatus.PAID_IN_FULL):
        raise InvalidStatusTransitionError(
            f"Cannot cancel contract: status is already " f"{contract.status.value}."
        )

    # Step 2 — cancel linked event if one exists
    if contract.event is not None:
        contract.event.is_cancelled = True

    # Step 3 — cancel contract
    contract.status = ContractStatus.CANCELLED

    session.commit()
    return contract


@require_role("MANAGEMENT", "COMMERCIAL", "SUPPORT")
def get_contracts_for_user(
    session: Session,
    current_user: Collaborator,
) -> list[Contract]:
    """Return contracts scoped to the current user's role.

    Args:
        session: SQLAlchemy database session.
        current_user: The authenticated collaborator.

    Returns:
        list[Contract]: Contracts visible to the current user.

    Raises:
        PermissionDeniedError: If current_user has no valid role.
    """
    if current_user.role.name == "MANAGEMENT":
        return list(session.scalars(select(Contract)).all())

    if current_user.role.name == "COMMERCIAL":
        return list(
            session.scalars(
                select(Contract).where(Contract.commercial_id == current_user.id)
            ).all()
        )

        # SUPPORT — contracts linked to their assigned events
    return list(
        session.scalars(
            select(Contract)
            .join(Event, Event.contract_id == Contract.id)
            .where(Event.support_id == current_user.id)
        ).all()
    )
