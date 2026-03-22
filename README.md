# 🎪 Epic Events CRM

> A secure command-line CRM for managing clients, contracts, and events across three operational departments: Management, Commercial, and Support.

Built with Python · PostgreSQL · SQLAlchemy · Click · Rich · Sentry

---

## Table of Contents

- [Project Overview](#project-overview)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Environment Setup](#environment-setup)
- [Database Setup](#database-setup)
- [Running the App](#running-the-app)
- [Usage & Commands](#usage--commands)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Security](#security)
- [Contributing](#contributing)

---

## Project Overview

Epic Events is an event management company (parties, professional meetings, outdoor events).  
This CRM replaces disconnected Excel sheets with a unified CLI platform that enforces **role-based access** and logs all errors to **Sentry**.

**Three departments, three roles:**

| Role | Key Abilities |
|---|---|
| **Management** | Full control over collaborators and all contracts; assign support to events |
| **Commercial** | Create and manage own clients; create events for signed contracts |
| **Support** | View and update events assigned to them |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Database | PostgreSQL 17 |
| ORM | SQLAlchemy 2.x |
| Migrations | Alembic |
| CLI framework | Click 8.x |
| Terminal output | Rich |
| Password hashing | bcrypt |
| Session tokens | PyJWT |
| Error monitoring | Sentry SDK |
| Config | python-dotenv |
| Testing | pytest + pytest-cov |

---

## Prerequisites

- Python 3.9 or higher (3.11 recommended)
- PostgreSQL 17 installed and running locally
- pgAdmin 4 (bundled with the PostgreSQL installer)
- `pip` and `venv`

---

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/your-org/epic-events-crm.git
cd epic-events-crm

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate       # macOS / Linux
venv\Scripts\activate          # Windows

# 3. Install production dependencies
pip install -r requirements.txt

# 4. Install dev dependencies (testing and seeding)
pip install -r requirements-dev.txt
```

---

## Environment Setup

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

**`.env.example`** (committed to Git — keys only, no values):

```env
DATABASE_URL=
SECRET_KEY=
SENTRY_DSN=
```

**Your `.env`** (never committed — fill in your actual values):

```env
DATABASE_URL=postgresql://epic_events_user:your_password@localhost/epic_events_db
SECRET_KEY=your_generated_secret_key
SENTRY_DSN=
```

To generate a secure `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

> ⚠️ **Never commit your `.env` file.** It is listed in `.gitignore`. Only `.env.example` is committed.

---

## Database Setup

### 1. Create the app user and database

Open pgAdmin → select your server → **Tools → Query Tool**, then run:

```sql
-- Non-privileged app user
CREATE USER epic_events_user WITH PASSWORD 'your_password';

-- Database owned by the app user
CREATE DATABASE epic_events_db OWNER epic_events_user;

-- Least-privilege grants
GRANT CONNECT ON DATABASE epic_events_db TO epic_events_user;
GRANT USAGE ON SCHEMA public TO epic_events_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO epic_events_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO epic_events_user;

-- Future tables created by Alembic inherit these grants automatically
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO epic_events_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO epic_events_user;
```

### 2. Run Alembic migrations

```bash
alembic upgrade head
```

### 3. Verify connection (optional sanity check)

```bash
python -c "
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    print('Connection successful:', conn.execute(text('SELECT 1')).fetchone())
"
```

---

## Running the App

```bash
# Show all available commands
python main.py --help

# Log in before running any other command
python main.py auth login
```

---

## Usage & Commands

### Authentication

```bash
python main.py auth login           # Start a session (stores JWT to ~/.epic_events/session)
python main.py auth logout          # End session (deletes token file)
```

### Clients

```bash
python main.py clients list                         # Read-only: all roles
python main.py clients create                       # Commercial only
python main.py clients update --id <ID>             # Commercial (own clients only)
```

### Contracts

```bash
python main.py contracts list                       # Read-only: all roles
python main.py contracts list --unsigned            # Filter unsigned contracts
python main.py contracts list --unpaid              # Filter unpaid contracts
python main.py contracts create --client-id <ID>    # Management only
python main.py contracts update --id <ID>           # Management + Commercial (own clients)
python main.py contracts sign --id <ID>             # Management only
```

### Events

```bash
python main.py events list                                          # Read-only: all roles
python main.py events list --mine                                   # Support: own events only
python main.py events list --no-support                             # Management: unassigned events
python main.py events create --contract-id <ID>                     # Commercial (signed contracts only)
python main.py events update --id <ID>                              # Support (own events only)
python main.py events assign-support --id <ID> --support-id <SID>  # Management only
```

### Collaborators (Management only)

```bash
python main.py collaborators list
python main.py collaborators create
python main.py collaborators update --id <ID>
python main.py collaborators delete --id <ID>
```

---

## Testing

The test suite is structured in three layers:

| Layer | Location | What it tests |
|---|---|---|
| **Unit** | `tests/unit/` | Pure logic — model methods and decorators, no DB |
| **Integration** | `tests/integration/` | Services talking to a real in-memory test DB |
| **Functional** | `tests/functional/` | Full CLI stack via Click's `CliRunner` |

```bash
# Run the full test suite
pytest

# Run with coverage report
pytest --cov=. --cov-report=term-missing

# Run a specific layer only
pytest tests/unit/
pytest tests/integration/
pytest tests/functional/

# Run a specific file
pytest tests/integration/test_client_service.py -v
```

**Coverage target: ≥ 80%**

> Tests use an in-memory SQLite database — no PostgreSQL instance required to run the test suite.

---

## Project Structure

```
epic_events_crm/
│
├── main.py                        # Thin entry point — calls cli.app()
│
├── models/                        # SQLAlchemy ORM class definitions only
│   ├── __init__.py                # Re-exports all models
│   ├── base.py                    # DeclarativeBase only — no engine, no session
│   ├── collaborator.py
│   ├── client.py
│   ├── contract.py
│   └── event.py
│
├── db/                            # DB infrastructure (separate from models)
│   ├── __init__.py
│   └── session.py                 # Engine, SessionLocal factory, get_session()
│
├── services/                      # Business logic layer
│   ├── __init__.py
│   ├── auth_service.py            # Login, JWT token, get_current_user()
│   ├── collaborator_service.py
│   ├── client_service.py
│   ├── contract_service.py
│   └── event_service.py
│
├── cli/                           # Click layer — thin, no business logic
│   ├── __init__.py
│   ├── app.py                     # Root Click group, registers all sub-groups
│   └── commands/
│       ├── __init__.py
│       ├── auth.py
│       ├── collaborators.py
│       ├── clients.py
│       ├── contracts.py
│       └── events.py
│
├── views/                         # Rich-formatted output, one file per domain
│   ├── __init__.py
│   ├── collaborators.py
│   ├── clients.py
│   ├── contracts.py
│   └── events.py
│
├── permissions/                   # Role-based access control
│   ├── __init__.py
│   ├── roles.py                   # RoleEnum: MANAGEMENT, COMMERCIAL, SUPPORT
│   └── decorators.py              # @require_role(*roles)
│
├── exceptions.py                  # All custom domain exceptions
├── config.py                      # Loads .env, exposes Settings object
│
├── migrations/
│   ├── env.py                     # Alembic env — imports Base.metadata
│   ├── script.py.mako
│   └── versions/                  # Auto-generated migration scripts (committed)
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Shared fixtures: db_session, role users, sample data
│   ├── unit/                      # Pure logic — no DB required
│   │   ├── __init__.py
│   │   ├── test_models.py         # verify_password(), is_fully_paid(), has_support(), etc.
│   │   └── test_decorators.py     # @require_role behaviour
│   ├── integration/               # Real in-memory test DB
│   │   ├── __init__.py
│   │   ├── test_auth_service.py
│   │   ├── test_client_service.py
│   │   ├── test_contract_service.py
│   │   └── test_event_service.py
│   └── functional/                # Full CLI stack via CliRunner
│       ├── __init__.py
│       └── test_commands.py
│
├── .github/
│   ├── workflows/
│   │   └── ci.yml                 # Runs pytest on every push and pull request
│   └── ISSUE_TEMPLATE/
│       ├── epic.yml
│       ├── user_story.yml
│       └── bug_report.yml
│
├── .env.example                   # Key names only — safe to commit
├── .gitignore
├── alembic.ini
├── requirements.txt               # click, rich, sqlalchemy, psycopg2-binary,
│                                  # bcrypt, pyjwt, sentry-sdk, python-dotenv, alembic
├── requirements-dev.txt           # pytest, pytest-cov, Faker, coverage
│                                  # bcrypt, pyjwt, sentry-sdk, python-dotenv, alembic
├── pytest.ini                     # Sets testing folder and reports location, etc.
└── README.md
```

---

## Security

- **SQL injection** — all DB queries go through SQLAlchemy ORM, parameterised queries only
- **Password storage** — bcrypt with cost factor 12, timing-safe comparison via `checkpw()`
- **Session tokens** — JWT signed with `SECRET_KEY`, expires after 8 hours, stored at `~/.epic_events/session` (outside the project — cannot be accidentally committed), `chmod 600`
- **Role enforcement** — `@require_role` decorator on every CLI command; ownership checks at service layer
- **Least privilege DB user** — app connects as `epic_events_user` with SELECT/INSERT/UPDATE/DELETE only
- **Secrets** — all credentials in `.env` (gitignored); `.env.example` committed with empty values
- **Error monitoring** — Sentry captures all unhandled exceptions with PII scrubbing via `before_send`

---

## Contributing

1. Create a branch from `main`: `feature/US-XX-short-description` or `fix/short-description`
2. Write tests first (TDD) — unit tests for logic, integration tests for services
3. Ensure `pytest --cov=. --cov-fail-under=80` passes
4. Open a pull request referencing the related GitHub Issue: `Closes #XX`
5. CI will run automatically — the PR cannot be merged if tests fail

---

*Epic Events CRM — Confidential internal tool*