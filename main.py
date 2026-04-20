"""Entry point for the Epic Events CRM CLI application."""

from config import init_sentry, settings
from views.menus import run_app

settings.validate()
init_sentry()

if __name__ == "__main__":
    run_app()
