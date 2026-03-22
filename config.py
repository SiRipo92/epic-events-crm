import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    database_url: str = os.getenv("DATABASE_URL", "")
    secret_key: str = os.getenv("SECRET_KEY", "")
    sentry_dsn: str = os.getenv("SENTRY_DSN", "")

settings = Settings()
