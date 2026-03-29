"""Entry point for the Epic Events CRM CLI application."""

from cli.app import app
from config import init_sentry, settings

settings.validate()
init_sentry()

if __name__ == "__main__":
    app()
