"""Entry point for the Epic Events CRM CLI application."""

from cli.app import app
from config import settings, init_sentry

settings.validate()
init_sentry()

if __name__ == "__main__":
    app()
