"""
Integration test fixtures for Epic Events CRM.

These fixtures create and tear down a real PostgreSQL test database
for each test session. All Sprint 2 service functions are tested
against actual DB queries.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base
from models.collaborator import Collaborator
from models.role import Role


@pytest.fixture(scope="session")
def engine():
    """Create a test database engine for the session."""
    from sqlalchemy import text

    from config import settings

    test_url = settings.database_url.replace("/epic_events_crm", "/epic_events_test")
    engine = create_engine(test_url)

    with engine.connect() as conn:
        # Drop existing enum and tables cleanly before each test session
        conn.execute(text("DROP TYPE IF EXISTS contractstatus CASCADE"))
        conn.commit()

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

    with engine.connect() as conn:
        conn.execute(text("DROP TYPE IF EXISTS contractstatus CASCADE"))
        conn.commit()


@pytest.fixture(scope="function")
def db_session(engine):
    """Provide a transactional session that rolls back after each test.

    Each test runs in its own transaction that is rolled back on teardown,
    leaving the database clean for the next test.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection)
    session = session_factory()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def seeded_db(db_session):
    """Seed the test database with roles and one collaborator per role.

    Provides:
        - Three roles: MANAGEMENT, COMMERCIAL, SUPPORT
        - One active collaborator per role
    """
    # Roles
    management_role = Role(id=1, name="MANAGEMENT")
    commercial_role = Role(id=2, name="COMMERCIAL")
    support_role = Role(id=3, name="SUPPORT")
    db_session.add_all([management_role, commercial_role, support_role])
    db_session.flush()

    # Collaborators
    manager = Collaborator()
    manager.employee_number = "EMP-001"
    manager.first_name = "Alice"
    manager.last_name = "Martin"
    manager.email = "alice.martin@epicevents.com"
    manager.role_id = 1
    manager.is_active = True
    manager.must_change_password = False
    manager.set_password("password123")

    commercial = Collaborator()
    commercial.employee_number = "EMP-002"
    commercial.first_name = "Bob"
    commercial.last_name = "Dupont"
    commercial.email = "bob.dupont@epicevents.com"
    commercial.role_id = 2
    commercial.is_active = True
    commercial.must_change_password = False
    commercial.set_password("password123")

    support = Collaborator()
    support.employee_number = "EMP-003"
    support.first_name = "Clara"
    support.last_name = "Petit"
    support.email = "clara.petit@epicevents.com"
    support.role_id = 3
    support.is_active = True
    support.must_change_password = False
    support.set_password("password123")

    db_session.add_all([manager, commercial, support])
    db_session.flush()

    return {
        "management": manager,
        "commercial": commercial,
        "support": support,
        "roles": {
            "management": management_role,
            "commercial": commercial_role,
            "support": support_role,
        },
    }
