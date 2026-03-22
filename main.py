"""Entry point for the Epic Events CRM CLI application."""

from config import init_sentry
from cli.app import app

init_sentry()

if __name__ == "__main__":
    app()
