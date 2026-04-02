"""
Integration test fixtures for Epic Events CRM.

These fixtures create and tear down a real PostgreSQL test database
for each test session. All Sprint 2 service functions are tested
against actual DB queries.
"""

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base
from models.client import Client
from models.collaborator import Collaborator
from models.contract import Contract, ContractStatus
from models.event import Event
from models.role import Role
from services.contract_service import (
    record_client_signature,
    record_deposit_received,
    submit_for_signature,
)


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


@pytest.fixture(scope="function")
def seeded_client(seeded_db, db_session):
    """Write a real client row linked to the seeded commercial collaborator."""
    commercial = seeded_db["commercial"]

    client = Client()
    client.first_name = "Marie"
    client.last_name = "Curie"
    client.email = "marie.curie@epicevents.com"
    client.commercial_id = commercial.id
    db_session.add(client)
    db_session.flush()

    return client


@pytest.fixture(scope="function")
def seeded_contract(seeded_db, seeded_client, db_session):
    """Write a real DRAFT contract linked to seeded client and commercial."""
    contract = Contract()
    contract.client_id = seeded_client.id
    contract.commercial_id = seeded_db["commercial"].id
    contract.total_amount = Decimal("5000.00")
    contract.remaining_amount = Decimal("5000.00")
    contract.status = ContractStatus.DRAFT
    db_session.add(contract)
    db_session.flush()

    return contract


@pytest.fixture(scope="function")
def seeded_deposit_contract(seeded_db, seeded_contract, db_session):
    """Advance seeded_contract to DEPOSIT_RECEIVED using real service calls."""
    manager = seeded_db["management"]

    submit_for_signature(
        session=db_session, current_user=manager, contract=seeded_contract
    )
    record_client_signature(
        session=db_session, current_user=manager, contract=seeded_contract
    )
    record_deposit_received(
        session=db_session, current_user=manager, contract=seeded_contract
    )

    return seeded_contract


@pytest.fixture(scope="function")
def seeded_event(seeded_db, seeded_deposit_contract, db_session):
    """Write a real event row linked to the seeded deposit contract."""
    event = Event()
    event.contract_id = seeded_deposit_contract.id
    event.title = "Annual Gala"
    event.start_date = datetime(2026, 9, 1, 9, 0)
    event.end_date = datetime(2026, 9, 1, 17, 0)
    event.location_street = "34 rue de la Paix"
    event.location_city = "Paris"
    event.location_zip = "75001"
    event.location_country = "France"
    event.support_id = None
    event.is_cancelled = False
    db_session.add(event)
    db_session.flush()

    return event
