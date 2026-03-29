"""
Application configuration for Epic Events CRM.

Loads environment variables from .env via python-dotenv and exposes
a Settings object used throughout the application. Sentry is
initialised here if a DSN is configured.

Call settings.validate() once at application startup to verify all
required variables are present before the app runs.
"""

import os
from pathlib import Path
from typing import Any

import sentry_sdk
from dotenv import load_dotenv
from sentry_sdk.types import Event as SentryEvent

load_dotenv()


class Settings:
    """Application settings loaded from environment variables.

    All sensitive values (database credentials, secret keys) are
    read from .env — never hardcoded in source code.

    Raises:
        EnvironmentError: If any required environment variable is
                          missing or empty at startup.
    """

    def __init__(self):
        """Load and validate settings from environment variables."""
        self.database_url = os.getenv("DATABASE_URL", "")
        self.secret_key = os.getenv("SECRET_KEY", "")
        self.sentry_dsn = os.getenv("SENTRY_DSN", "")
        self.session_file = Path.home() / ".epic-events" / "session"
        self.jwt_expiry_hours = 8

    def validate(self) -> None:
        """Validate that all required settings are present.

        Called once at application startup from main.py.
        Never called during tests.

        Raises:
            EnvironmentError: If any required variable is missing or empty.
        """
        self._require("DATABASE_URL", self.database_url)
        self._require("SECRET_KEY", self.secret_key)

    @staticmethod
    def _require(key: str, value: str) -> None:
        """Raise EnvironmentError if a required value is empty.

        Args:
            key: The environment variable name (for the error message).
            value: The loaded value to check.

        Raises:
            EnvironmentError: If the value is missing or empty.
        """
        if not value.strip():
            raise EnvironmentError(
                f"Missing required environment variable: {key}\n"
                f"Check your .env file or CI secrets."
            )


settings = Settings()


def init_sentry() -> None:
    """Initialise Sentry SDK if a DSN is configured.

    Called once at application startup from main.py.
    Silently skipped in development and testing if SENTRY_DSN is empty.
    """
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            traces_sample_rate=0.0,
            before_send=_scrub_pii,
        )


def _scrub_pii(event: SentryEvent, _hint: dict[str, Any]) -> SentryEvent | None:
    """Remove personally identifiable information before sending to Sentry.

    Scrubs request data from exception context to comply with RGPD.

    Args:
        event: The Sentry event dict.
        _hint: Additional context from the SDK (unused).

    Returns:
        dict | None: The scrubbed event, or None to discard entirely.
    """
    if "request" in event:
        event["request"].pop("data", None)
    return event
