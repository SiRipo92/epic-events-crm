from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config import settings

engine = create_engine(settings.database_url, echo=False)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# @contextmanager turns this generator function into a context manager.
# The Generator type hint tells the type checker what get_session() yields
# (Session), what it accepts via send() (None), and what it returns (None).
# Without this, IDEs lose track of the yielded type and warn incorrectly.


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Provide a transactional database session as a context manager.

    Yields a SQLAlchemy Session that automatically commits on clean exit
    and rolls back on any exception. The session is always closed in the
    finally block regardless of outcome.

    Usage:
        with get_session() as session:
            client = session.get(Client, client_id)

    Yields:
        Session: An active SQLAlchemy ORM session.

    Raises:
        Any exception raised inside the with block is re-raised after
        the session has been rolled back and closed.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
