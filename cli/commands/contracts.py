"""
Contract management CLI commands.

Handles all contract-related menu interactions scoped by role.
No business logic lives here — handlers call service functions
and pass results to view functions.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import questionary
from rich.console import Console

from exceptions import (
    ClientNotFoundError,
    ContractNotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from models.client import Client
from models.collaborator import Collaborator
from models.contract import Contract, ContractStatus
from models.event import Event
from services.contract_service import (
    cancel_contract,
    create_contract,
    edit_contract,
    get_contract_by_id,
    get_contracts_for_user,
    record_client_signature,
    record_deposit_received,
    record_payment,
    submit_for_signature,
)
from views.messages import Errors, Info, Prompts, Success, Warnings
from views.screens import render_contract_detail
from views.tables import render_contracts_table

console = Console()


# ── Main menu ─────────────────────────────────────────────────────────────────


def contracts_menu(session, current_user: Collaborator) -> None:
    """Render the contracts sub-menu scoped by role."""
    role = current_user.role.name

    if role == "MANAGEMENT":
        options = [
            "List Contracts",
            "Create Contract",
            "Select Contract",
            Info.BACK,
        ]
    else:
        options = [
            "List Contracts",
            "Select Contract",
            Info.BACK,
        ]

    while True:
        choice = questionary.select(
            "Contracts — select an option:",
            choices=options,
        ).ask()

        if choice is None or choice == Info.BACK:
            return

        if choice == "List Contracts":
            _handle_list_contracts(session, current_user)
        elif choice == "Create Contract":
            _handle_create_contract(session, current_user)
        elif choice == "Select Contract":
            _handle_select_contract(session, current_user)


# ── Selection and context menu ────────────────────────────────────────────────


def _select_contract_from_table(session, current_user: Collaborator) -> Contract | None:
    """Show table and prompt for ID. Returns contract or None."""
    contracts = get_contracts_for_user(session=session, current_user=current_user)
    if not contracts:
        console.print(Info.NO_CONTRACTS)
        return None

    console.print(render_contracts_table(contracts))
    contract_id = questionary.text("Enter contract ID:").ask()

    if not contract_id:
        return None

    try:
        return get_contract_by_id(
            session=session,
            current_user=current_user,
            contract_id=int(contract_id),
        )
    except (ContractNotFoundError, ValueError):
        console.print(Errors.NOT_FOUND)
        return None


def _handle_select_contract(session, current_user: Collaborator) -> None:
    """Select a contract and show context menu."""
    contract = _select_contract_from_table(session, current_user)
    if not contract:
        return
    _contract_context_menu(session, current_user, contract)


def _contract_context_menu(
    session, current_user: Collaborator, contract: Contract
) -> None:
    """Context menu for a selected contract — actions scoped by role and status."""
    role = current_user.role.name

    while True:
        render_contract_detail(contract)

        actions = _build_context_actions(role, contract, current_user)

        choice = questionary.select(
            f"Contract #{contract.id} — select an action:",
            choices=actions,
        ).ask()

        if choice is None or choice == Info.BACK:
            return

        result = _dispatch_contract_action(choice, session, current_user, contract)

        if result == "exit":
            return


def _build_context_actions(
    role: str, contract: Contract, current_user: Collaborator
) -> list[str]:
    """Build context menu actions based on role and contract status."""
    status = contract.status

    if role == "MANAGEMENT":
        if status == ContractStatus.DRAFT:
            return ["Edit", "Submit for Signature", "Cancel", Info.BACK]
        if status == ContractStatus.PENDING:
            return ["Record Signature", "Cancel", Info.BACK]
        if status == ContractStatus.SIGNED:
            return ["Record Deposit", "Cancel", Info.BACK]
        if status == ContractStatus.DEPOSIT_RECEIVED:
            return ["Record Payment", Info.BACK]

    if role == "COMMERCIAL":
        if contract.commercial_id == current_user.id:
            if status in (ContractStatus.DRAFT, ContractStatus.PENDING):
                return ["Edit", Info.BACK]

    return [Info.BACK]


def _dispatch_contract_action(
    choice: str, session, current_user: Collaborator, contract: Contract
) -> str | None:
    """Dispatch the selected action. Returns 'exit' to close context menu."""
    if choice == "Edit":
        _handle_edit_contract(session, current_user, contract)
    elif choice == "Submit for Signature":
        _handle_submit(session, current_user, contract)
    elif choice == "Record Signature":
        _handle_record_signature(session, current_user, contract)
    elif choice == "Record Deposit":
        _handle_record_deposit(session, current_user, contract)
    elif choice == "Record Payment":
        _handle_record_payment(session, current_user, contract)
    elif choice == "Cancel":
        cancelled = _handle_cancel_contract(session, current_user, contract)
        if cancelled:
            return "exit"
    return None


# ── Handlers ──────────────────────────────────────────────────────────────────


def _handle_list_contracts(session, current_user: Collaborator) -> None:
    """List contracts scoped by role with optional filter."""
    role = current_user.role.name

    if role == "COMMERCIAL":
        filter_by = questionary.select(
            "Filter by:",
            choices=["None", "Client name", "Unsigned only", "Not fully paid"],
        ).ask()
    else:
        filter_by = questionary.select(
            "Filter by:",
            choices=["None", "Status", "Client name"],
        ).ask()

    try:
        contracts = get_contracts_for_user(
            session=session, current_user=current_user
        )

        if filter_by == "Status":
            status_choice = questionary.select(
                "Select status:",
                choices=[s.value.upper() for s in ContractStatus],
            ).ask()
            contracts = [
                c for c in contracts
                if c.status.value.upper() == status_choice
            ]
        elif filter_by == "Client name":
            name = questionary.text("Enter client name:").ask()
            if name:
                contracts = [
                    c for c in contracts
                    if c.client and name.lower()
                    in c.client.full_name.lower()
                ]
        elif filter_by == "Unsigned only":
            contracts = [
                c for c in contracts
                if c.status in (
                    ContractStatus.DRAFT,
                    ContractStatus.PENDING,
                )
            ]
        elif filter_by == "Not fully paid":
            contracts = [
                c for c in contracts
                if c.remaining_amount > 0
                and c.status != ContractStatus.CANCELLED
            ]

        if not contracts:
            console.print(Info.NO_CONTRACTS)
            return
        console.print(render_contracts_table(contracts))
    except PermissionDeniedError:
        console.print(Errors.PERMISSION_DENIED)


def _handle_create_contract(session, current_user: Collaborator) -> None:
    """Prompt for contract details and create."""
    clients = session.query(Client).all()
    if not clients:
        console.print("[red]✗ No clients exist yet. Create a client first.[/red]")
        return

    client_choices = []
    for c in clients:
        contract_count = len(c.contracts)
        client_choices.append(
            f"{c.id} — {c.full_name} ({c.company_name or 'No company'})"
            f" — {contract_count} contract(s)"
        )
    client_choices.append(Info.BACK)

    client_choice = questionary.select(
        "Select client:", choices=client_choices
    ).ask()

    if not client_choice or client_choice == Info.BACK:
        return

    client_id = int(client_choice.split(" — ")[0])
    client = next(c for c in clients if c.id == client_id)

    total_str = questionary.text("Total amount (€):").ask()
    try:
        total_amount = Decimal(total_str)
    except InvalidOperation:
        console.print("[red]✗ Invalid amount.[/red]")
        return

    try:
        contract = create_contract(
            session=session,
            current_user=current_user,
            client_id=client_id,
            commercial_id=client.commercial_id,
            total_amount=total_amount,
        )
        console.print(Success.CONTRACT_CREATED.format(id=contract.id))
    except PermissionDeniedError:
        console.print(Errors.PERMISSION_DENIED)
    except (ClientNotFoundError, ValueError) as e:
        console.print(f"[red]✗ {e}[/red]")


def _handle_edit_contract(
    session, current_user: Collaborator, contract: Contract
) -> None:
    """Prompt for updated contract fields and save."""
    try:
        total_str = questionary.text(
            "Total amount (€):",
            default=str(contract.total_amount),
        ).ask()
        try:
            total_amount = Decimal(total_str)
        except InvalidOperation:
            console.print("[red]✗ Invalid amount.[/red]")
            return

        edit_contract(
            session=session,
            current_user=current_user,
            contract=contract,
            total_amount=total_amount,
        )
        console.print(Success.CONTRACT_UPDATED.format(id=contract.id))
    except PermissionDeniedError:
        console.print(Errors.PERMISSION_DENIED)
    except ValidationError as e:
        console.print(f"[red]✗ {e}[/red]")


def _handle_submit(session, current_user: Collaborator, contract: Contract) -> None:
    """Submit contract for signature."""
    try:
        submit_for_signature(
            session=session,
            current_user=current_user,
            contract=contract,
        )
        console.print(Success.CONTRACT_SUBMITTED.format(id=contract.id))
    except PermissionDeniedError:
        console.print(Errors.PERMISSION_DENIED)


def _handle_record_signature(
    session, current_user: Collaborator, contract: Contract
) -> None:
    """Record client signature."""
    try:
        record_client_signature(
            session=session,
            current_user=current_user,
            contract=contract,
        )
        console.print(Success.CONTRACT_SIGNED)
    except PermissionDeniedError:
        console.print(Errors.PERMISSION_DENIED)


def _handle_record_deposit(
    session, current_user: Collaborator, contract: Contract
) -> None:
    """Record deposit received."""
    try:
        record_deposit_received(
            session=session,
            current_user=current_user,
            contract=contract,
        )
        console.print(Success.DEPOSIT_RECORDED)
    except PermissionDeniedError:
        console.print(Errors.PERMISSION_DENIED)


def _handle_record_payment(
    session, current_user: Collaborator, contract: Contract
) -> None:
    """Record payment against remaining balance."""
    # Warn if linked event has not passed
    event = (
        session.query(Event)
        .filter(
            Event.contract_id == contract.id,
            Event.is_cancelled.is_(False),
        )
        .first()
    )

    if event and not event.is_past:
        console.print(Warnings.PAYMENT_DUE)
        confirmed = questionary.confirm("Record payment anyway?").ask()
        if not confirmed:
            return

    amount_str = questionary.text(
        f"Amount to record (€) — remaining: " f"{contract.remaining_amount:.2f} €:"
    ).ask()

    try:
        amount = Decimal(amount_str)
    except InvalidOperation:
        console.print("[red]✗ Invalid amount.[/red]")
        return

    try:
        record_payment(
            session=session,
            current_user=current_user,
            contract=contract,
            amount_paid=amount,
        )
        if contract.status == ContractStatus.PAID_IN_FULL:
            console.print(Success.CONTRACT_PAID)
        else:
            console.print(
                Success.PAYMENT_RECORDED.format(
                    amount=f"{amount:.2f} €",
                    remaining=f"{contract.remaining_amount:.2f} €",
                )
            )
    except PermissionDeniedError:
        console.print(Errors.PERMISSION_DENIED)
    except ValidationError as e:
        console.print(f"[red]✗ {e}[/red]")


def _handle_cancel_contract(
    session, current_user: Collaborator, contract: Contract
) -> bool:
    """Confirm and cancel contract. Returns True on success."""
    event = (
        session.query(Event)
        .filter(
            Event.contract_id == contract.id,
            Event.is_cancelled.is_(False),
        )
        .first()
    )

    if event:
        console.print(Warnings.CONTRACT_CANCELS_EVENT)

    confirmed = questionary.confirm(Prompts.CONFIRM_CANCEL).ask()
    if not confirmed:
        return False

    try:
        cancel_contract(
            session=session,
            current_user=current_user,
            contract=contract,
        )
        console.print(Success.CONTRACT_CANCELLED)
        return True
    except PermissionDeniedError:
        console.print(Errors.PERMISSION_DENIED)
        return False
