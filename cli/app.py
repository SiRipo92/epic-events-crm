"""
Typer application entry point for Epic Events CRM.
"""

from __future__ import annotations

import typer

app = typer.Typer(
    help="Epic Events CRM — Command Line Interface.",
    invoke_without_command=True,
)

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Launch Epic Events CRM interactive interface."""
    if ctx.invoked_subcommand is None:
        from views.menus import run_app
        run_app()


if __name__ == "__main__":
    app()
