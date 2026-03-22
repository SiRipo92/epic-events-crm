"""
Application configuration for Epic Events CRM.

Loads environment variables from .env via python-dotenv and exposes
a Settings object used throughout the application. Sentry is
initialised here if a DSN is configured.

Raises EnvironmentError at startup if any required variable is missing,
preventing silent failures from misconfigured environments.
"""

import os
from typing import Any
from dotenv import load_dotenv
import sentry_sdk
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
        self.database_url = self._require("DATABASE_URL")
        self.secret_key = self._require("SECRET_KEY")
        self.sentry_dsn = os.getenv("SENTRY_DSN", "")

    @staticmethod
    def _require(key: str) -> str:
        """Read a required environment variable.

        Args:
            key: The environment variable name.

        Returns:
            str: The variable value if present and non-empty.

        Raises:
            EnvironmentError: If the variable is missing or empty.
        """
        value = os.getenv(key, "").strip()
        if not value:
            raise EnvironmentError(
                f"Missing required environment variable: {key}\n"
                f"Check your .env file or CI secrets."
            )
        return value


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


def _scrub_pii(
    event: SentryEvent,
    _hint: dict[str, Any]
) -> SentryEvent | None:
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
