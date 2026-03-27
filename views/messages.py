class Errors:
    """Display Error messages."""

    INVALID_CREDENTIALS = "[red]✗ Invalid credentials. Please try again.[/red]"
    ACCOUNT_DEACTIVATED = "[red]✗ Account deactivated. Contact management.[/red]"
    MUST_CHANGE_PASSWORD = (
        "[yellow]⚠ You must set a new password before continuing.[/yellow]"
    )
    PASSWORDS_DONT_MATCH = "[red]✗ Passwords do not match.[/red]"
    PASSWORD_SAME_AS_OLD = (
        "[red]✗ New password must differ from your initial password.[/red]"
    )
    CONTRACT_NOT_ELIGIBLE = (
        "[red]✗ Contract must have DEPOSIT_RECEIVED status to create an event.[/red]"
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


class Success:
    """Display Success messages."""

    LOGIN_OK = "[green]✓ Welcome back, {name}.[/green]"
    LOGGED_OUT = "[green]✓ Logged out successfully.[/green]"
    PASSWORD_CHANGED = "[green]✓ Password updated. You're now logged in.[/green]"
    COLLABORATOR_CREATED = (
        "[green]✓ Collaborator '{name}' created successfully.[/green]"
    )
    CLIENT_CREATED = (
        "[green]✓ Client '{name}' created and linked to your account.[/green]"
    )
    CONTRACT_SIGNED = (
        "[green]✓ Client signature recorded. Contract is now SIGNED.[/green]"
    )
    DEPOSIT_RECORDED = (
        "[green]✓ Deposit recorded. Support assignment is now unlocked.[/green]"
    )
    PAYMENT_RECORDED = (
        "[green]✓ Payment of {amount} recorded. Remaining: {remaining}[/green]"
    )
    CONTRACT_PAID = "[green]✓ Contract marked PAID_IN_FULL. Dossier closed.[/green]"
    SUPPORT_ASSIGNED = "[green]✓ Support assigned to event.[/green]"
    COLLABORATOR_DEACTIVATED = (
        "[green]✓ Collaborator deactivated. Session revoked.[/green]"
    )


class Warnings:
    """Display Warning messages."""

    SCHEDULING_CONFLICT = (
        "[yellow]⚠ {name} already has an event on {date}. "
        "Force assign anyway? [y/N][/yellow]"
    )
    CONTRACT_CANCELS_EVENT = (
        "[yellow]⚠ Cancelling this contract will also cancel its linked event.[/yellow]"
    )
