import os
from typing import Any
from dotenv import load_dotenv
import sentry_sdk

load_dotenv()

class Settings:
    """Application settings loaded from environment variables.

    All sensitive values (database credentials, secret keys) are
    read from .env — never hardcoded in source code.
    """
    database_url: str = os.getenv("DATABASE_URL", "")
    secret_key: str = os.getenv("SECRET_KEY", "")
    sentry_dsn: str = os.getenv("SENTRY_DSN", "")

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
    event: dict[str, Any],
    _hint: dict[str, Any]
) -> dict[str, Any] | None:
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
