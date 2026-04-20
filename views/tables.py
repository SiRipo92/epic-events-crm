"""
Rich table renderers for the Epic Events CRM CLI.

Each function receives a list of ORM instances and returns a
formatted Rich Table ready to print. No business logic lives here —
tables receive data and render it.
"""

from __future__ import annotations

from rich import box
from rich.console import Console
from rich.table import Table

from models.client import Client
from models.collaborator import Collaborator
from models.contract import Contract, ContractStatus
from models.event import Event

console = Console()

# ── Status colour map ─────────────────────────────────────────────────────────

CONTRACT_STATUS_STYLE = {
    ContractStatus.DRAFT: "dim",
    ContractStatus.PENDING: "yellow",
    ContractStatus.SIGNED: "cyan",
    ContractStatus.DEPOSIT_RECEIVED: "green",
    ContractStatus.PAID_IN_FULL: "bold green",
    ContractStatus.CANCELLED: "red",
}

# ── Collaborator tables ───────────────────────────────────────────────────────


def render_collaborators_table(collaborators: list[Collaborator]) -> Table:
    """Render a Rich table of collaborators.

    Args:
        collaborators: List of Collaborator instances to display.

    Returns:
        Table: Formatted Rich table.
    """
    table = Table(
        title="Collaborators",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("ID", style="dim", width=4)
    table.add_column("Employee No.", style="cyan")
    table.add_column("Name")
    table.add_column("Email")
    table.add_column("Role", style="magenta")
    table.add_column("Active", justify="center")

    for c in collaborators:
        table.add_row(
            str(c.id),
            c.employee_number,
            c.full_name,
            c.email,
            c.role.name if c.role else "—",
            "[green]✓[/green]" if c.is_active else "[red]✗[/red]",
        )

    return table


# ── Client tables ─────────────────────────────────────────────────────────────


def render_clients_table(clients: list[Client]) -> Table:
    """Render a Rich table of clients."""
    table = Table(
        title="Clients",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("ID", style="dim", width=4)
    table.add_column("Name")
    table.add_column("Company")
    table.add_column("Email")
    table.add_column("Phone")
    table.add_column("Commercial ID", justify="center")

    for c in clients:
        table.add_row(
            str(c.id),
            c.full_name,
            c.company_name or "—",
            c.email,
            c.phone or "—",
            str(c.commercial_id),
        )

    return table


# ── Contract tables ───────────────────────────────────────────────────────────


def render_contracts_table(contracts: list[Contract]) -> Table:
    """Render a Rich table of contracts colour-coded by status.

    Args:
        contracts: List of Contract instances to display.

    Returns:
        Table: Formatted Rich table.
    """
    table = Table(
        title="Contracts",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("ID", style="dim", width=4)
    table.add_column("Client")
    table.add_column("Total", justify="right")
    table.add_column("Remaining", justify="right")
    table.add_column("Status")
    table.add_column("Deposit", justify="center")

    for c in contracts:
        status_style = CONTRACT_STATUS_STYLE.get(c.status, "")
        client_name = c.client.full_name if c.client else "—"
        table.add_row(
            str(c.id),
            client_name,
            f"{c.total_amount:.2f} €",
            f"{c.remaining_amount:.2f} €",
            f"[{status_style}]{c.status.value.upper()}[/{status_style}]",
            "[green]✓[/green]" if c.deposit_received else "[dim]✗[/dim]",
        )

    return table


# ── Event tables ──────────────────────────────────────────────────────────────


def render_events_table(events: list[Event]) -> Table:
    """Render a Rich table of events.

    Args:
        events: List of Event instances to display.

    Returns:
        Table: Formatted Rich table.
    """
    table = Table(
        title="Events",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Title")
    table.add_column("Start")
    table.add_column("End")
    table.add_column("Location")
    table.add_column("Attendees", justify="center")
    table.add_column("Support", justify="center")
    table.add_column("Status", justify="center")

    for i, e in enumerate(events, start=1):
        support = (
            f"[green]ID:{e.support_id}[/green]"
            if e.support_id
            else "[dim]Unassigned[/dim]"
        )
        status = (
            "[red]Cancelled[/red]"
            if e.is_cancelled
            else "[yellow]⚠ Past[/yellow]" if e.is_past else "[green]Upcoming[/green]"
        )
        table.add_row(
            str(i),
            e.title,
            e.start_date.strftime("%d/%m/%Y %H:%M"),
            e.end_date.strftime("%d/%m/%Y %H:%M"),
            e.location or "—",
            str(e.attendees),
            support,
            status,
        )

    return table
