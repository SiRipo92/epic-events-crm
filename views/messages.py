"""
Centralised message strings for the Epic Events CRM CLI.

All user-facing strings live here — never hardcoded in menu
or command files.
"""


class Errors:
    """Display Error messages."""

    INVALID_CREDENTIALS = "[red]✗ Invalid credentials. Please try again.[/red]"
    ACCOUNT_DEACTIVATED = "[red]✗ Account deactivated. Contact management.[/red]"
    MUST_CHANGE_PASSWORD = (
        "[yellow]⚠ You must set a new password before continuing.[/yellow]"
    )
    PASSWORDS_DONT_MATCH = "[red]✗ Passwords do not match.[/red]"
    PASSWORD_SAME_AS_OLD = (
        "[red]✗ New password must differ from your current password.[/red]"
    )
    WEAK_PASSWORD = (
        "[red]✗ Password must be at least 8 characters and contain "
        "an uppercase letter, a lowercase letter, and a digit.[/red]"
    )
    CONTRACT_NOT_ELIGIBLE = (
        "[red]✗ Contract must have DEPOSIT_RECEIVED status to create an event.[/red]"
    )
    CONTRACT_NOT_EDITABLE = "[red]✗ Only DRAFT contracts can be edited.[/red]"
    INVALID_STATUS_TRANSITION = "[red]✗ This status transition is not allowed.[/red]"
    PAYMENT_EXCEEDS_BALANCE = (
        "[red]✗ Payment amount exceeds the remaining balance.[/red]"
    )
    INVALID_ASSIGNMENT = (
        "[red]✗ Only Support collaborators can be assigned to events.[/red]"
    )
    REASSIGNMENT_REQUIRED = (
        "[red]✗ All active dossiers must be reassigned before deactivation.[/red]"
    )
    PERMISSION_DENIED = (
        "[red]✗ You do not have permission to perform this action.[/red]"
    )
    INVALID_CHOICE = (
        "[yellow]⚠ Invalid choice. Please select a number from the menu.[/yellow]"
    )
    NOT_FOUND = "[red]✗ Record not found or outside your access scope.[/red]"
    DUPLICATE_EMAIL = "[red]✗ This email address is already in use.[/red]"
    INVALID_EMAIL = "[red]✗ Invalid email address format.[/red]"
    INVALID_LOCATION = "[red]✗ Location requires street, city and zip code.[/red]"
    INVALID_DATES = "[red]✗ Start date must be before end date.[/red]"
    UNEXPECTED = "[red]✗ An unexpected error occurred. Please try again.[/red]"


class Success:
    """Display Success messages."""

    LOGIN_OK = "[green]✓ Welcome back, {name}.[/green]"
    LOGGED_OUT = "[green]✓ Logged out successfully.[/green]"
    PASSWORD_CHANGED = "[green]✓ Password updated. You're now logged in.[/green]"
    COLLABORATOR_CREATED = (
        "[green]✓ Collaborator '{name}' ({number}) created successfully.[/green]"
    )
    COLLABORATOR_UPDATED = (
        "[green]✓ Collaborator '{name}' updated successfully.[/green]"
    )
    COLLABORATOR_DEACTIVATED = (
        "[green]✓ Collaborator deactivated. Session revoked.[/green]"
    )
    CLIENT_CREATED = (
        "[green]✓ Client '{name}' created and linked to your account.[/green]"
    )
    CLIENT_UPDATED = "[green]✓ Client '{name}' updated successfully.[/green]"
    CONTRACT_CREATED = "[green]✓ Contract #{id} created successfully.[/green]"
    CONTRACT_UPDATED = "[green]✓ Contract #{id} updated successfully.[/green]"
    CONTRACT_SUBMITTED = "[green]✓ Contract #{id} submitted for signature.[/green]"
    CONTRACT_SIGNED = (
        "[green]✓ Client signature recorded. Contract is now SIGNED.[/green]"
    )
    DEPOSIT_RECORDED = (
        "[green]✓ Deposit recorded. Support assignment is now unlocked.[/green]"
    )
    PAYMENT_RECORDED = (
        "[green]✓ Payment of {amount} recorded. Remaining: {remaining}[/green]"
    )
    CONTRACT_PAID = "[green]✓ Contract marked PAID IN FULL. Dossier closed.[/green]"
    CONTRACT_CANCELLED = "[green]✓ Contract cancelled successfully.[/green]"
    EVENT_CREATED = "[green]✓ Event '{title}' created successfully.[/green]"
    EVENT_UPDATED = "[green]✓ Event '{title}' updated successfully.[/green]"
    SUPPORT_ASSIGNED = "[green]✓ Support assigned to event.[/green]"


class Warnings:
    """Display Warning messages."""

    SCHEDULING_CONFLICT = (
        "[yellow]⚠ {name} already has an event on {date}. "
        "Force assign anyway? [y/N][/yellow]"
    )
    CONTRACT_CANCELS_EVENT = (
        "[yellow]⚠ Cancelling this contract will also cancel "
        "its linked event.[/yellow]"
    )
    PAYMENT_DUE = "[yellow]⚠ This event has passed — final payment may be due.[/yellow]"


class Info:
    """Informational display messages."""

    NO_CLIENTS = "[dim]No clients found.[/dim]"
    NO_CONTRACTS = "[dim]No contracts found.[/dim]"
    NO_EVENTS = "[dim]No events found.[/dim]"
    NO_COLLABORATORS = "[dim]No collaborators found.[/dim]"
    UNASSIGNED = "[dim]Unassigned[/dim]"
    BACK = "← Back"
    LOGOUT = "→ Logout"


class Prompts:
    """Input prompt strings."""

    EMAIL = "Email address"
    CURRENT_PASSWORD = "Current password"
    NEW_PASSWORD = "New password"
    CONFIRM_PASSWORD = "Confirm new password"
    CONFIRM_ACTION = "Are you sure? [y/N]"
    FORCE_ASSIGN = "Assign anyway despite scheduling conflict? [y/N]"
    CONFIRM_CANCEL = (
        "Cancelling this contract will also cancel its linked event. Confirm? [y/N]"
    )
    CONFIRM_DEACTIVATE = "Confirm deactivation? [y/N]"
    SELECT_CLIENT = "Select a client"
    SELECT_CONTRACT = "Select a contract"
    SELECT_EVENT = "Select an event"
    SELECT_COLLABORATOR = "Select a collaborator"
    SELECT_SUPPORT = "Select a support member"
