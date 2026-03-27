# Epic Events CRM

> A secure command-line CRM for managing clients, contracts, and events
> across three operational departments: Management, Commercial, and Support.

Built with Python · PostgreSQL · SQLAlchemy · Typer · Rich · bcrypt · PyJWT · Sentry

---

## Table of Contents

- [Project Overview](#project-overview)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Environment Setup](#environment-setup)
- [Database Setup](#database-setup)
- [Running the App](#running-the-app)
- [Navigation](#navigation)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Security](#security)
- [Contributing](#contributing)

---

## Project Overview

Epic Events is an event management company (parties, professional meetings,
outdoor events). This CRM replaces disconnected Excel sheets with a unified
CLI platform that enforces **role-based access** and logs all errors to
**Sentry**.

**Three departments, three roles:**

| Role | Key Abilities |
|---|---|
| Management | Full control over collaborators and all contracts; assign support to events |
| Commercial | Create and manage own clients; create events for deposit-received contracts |
| Support | View and update events assigned to them |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Database | PostgreSQL 17 |
| ORM | SQLAlchemy 2.x |
| Migrations | Alembic |
| CLI framework | Typer |
| Terminal output | Rich |
| Password hashing | bcrypt (cost factor 12) |
| Session tokens | PyJWT (8h expiry) |
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
git clone https://github.com/SiRipo92/epic-events-crm.git
cd epic-events-crm

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate       # macOS / Linux
.venv\Scripts\activate          # Windows

# 3. Install production dependencies
pip install -r requirements.txt

# 4. Install dev dependencies (testing, linting, seed data)
pip install -r requirements-dev.txt
```

---

## Environment Setup

Copy the example file and fill in your values:
```bash
cp .env.example .env
```

`.env.example` (committed to Git — keys only, no values):
```env
DATABASE_URL=
SECRET_KEY=
SENTRY_DSN=
```

Your `.env` (never committed — fill in your actual values):
```env
DATABASE_URL=postgresql://epic_events_user:your_password@localhost/epic_events_db
SECRET_KEY=your_generated_secret_key
SENTRY_DSN=
```

To generate a secure `SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

> Never commit your `.env` file. It is listed in `.gitignore`.
> Only `.env.example` is committed.

---

## Database Setup

### 1. Create the app user and database

Open pgAdmin → select your server → Tools → Query Tool, then run:
```sql
CREATE USER epic_events_user WITH PASSWORD 'your_password';
CREATE DATABASE epic_events_db OWNER epic_events_user;

GRANT CONNECT ON DATABASE epic_events_db TO epic_events_user;
GRANT USAGE ON SCHEMA public TO epic_events_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO epic_events_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO epic_events_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO epic_events_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO epic_events_user;
```

### 2. Run Alembic migrations
```bash
alembic upgrade head
```

This creates all tables and seeds the three roles (MANAGEMENT, COMMERCIAL,
SUPPORT) automatically.

### 3. Verify connection
```bash
python -c "
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    print('Connected:', conn.execute(text('SELECT 1')).fetchone())
"
```

---

## Running the App
```bash
python main.py
```

That is the only command you need. The app detects your session state and
routes automatically:

- Valid session exists → main menu shown immediately
- No session or expired token → login prompt shown, then menu
- First login → password change screen shown before menu

No subcommands are required from the user.

---

## Navigation

The app is menu-driven. After login, you see a role-scoped menu:

**Management**
```
[1] Clients
[2] Contracts
[3] Events
[4] Collaborators
[0] Logout
```

**Commercial**
```
[1] My Clients
[2] My Contracts
[3] Create Event
[0] Logout
```

**Support**
```
[1] My Events
[0] Logout
```

Each menu option leads to a sub-menu with the actions available to that role.
All navigation is number-based — no commands to memorise.

---

## Testing

The test suite is structured in three layers:

| Layer | Location | What it tests |
|---|---|---|
| Unit | `tests/unit/` | Model methods and decorators — no DB required |
| Integration | `tests/integration/` | Services against a real test DB |
| Functional | `tests/functional/` | Full CLI stack via Typer's test runner |
```bash
# Run unit tests only (default — no DB required)
pytest

# Run with coverage report
pytest --cov=. --cov-report=term-missing

# Run a specific layer
pytest tests/unit/
pytest tests/integration/
pytest tests/functional/

# Run a specific file
pytest tests/unit/models/test_collaborator.py -v

# Lint and format
make format    # isort + black
make lint      # flake8
make check     # both
```

Coverage target: 80% minimum.

---

## Project Structure
```
epic-events-crm/
│
├── main.py                        # Entry point — calls run_app()
│
├── models/
│   ├── __init__.py                # Re-exports all models
│   ├── base.py                    # DeclarativeBase only
│   ├── role.py                    # Role table (MANAGEMENT/COMMERCIAL/SUPPORT)
│   ├── collaborator.py            # Collaborator ORM class
│   ├── client.py
│   ├── contract.py
│   └── event.py
│
├── db/
│   ├── __init__.py
│   └── session.py                 # Engine, SessionLocal, get_session()
│
├── services/                      # Business logic — all DB writes happen here
│   ├── __init__.py
│   ├── auth_service.py
│   ├── collaborator_service.py
│   ├── client_service.py
│   ├── contract_service.py
│   └── event_service.py
│
├── cli/
│   ├── __init__.py
│   ├── app.py                     # Typer app — powers test suite and logout command
│   └── commands/
│       ├── auth.py
│       ├── collaborators.py
│       ├── clients.py
│       ├── contracts.py
│       └── events.py
│
├── views/                         # Rich output only — no business logic
│   ├── __init__.py
│   ├── menus.py                   # Role-scoped menu loop
│   ├── tables.py                  # Rich table renderers
│   ├── messages.py                # All user-facing strings centralised
│   ├── collaborators.py
│   ├── clients.py
│   ├── contracts.py
│   └── events.py
│
├── permissions/
│   ├── __init__.py
│   ├── roles.py
│   └── decorators.py              # @require_role(*roles)
│
├── exceptions.py                  # All custom domain exceptions
├── config.py                      # Loads .env, exposes Settings object
│
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/                  # Migration scripts — committed to Git
│
├── tests/
│   ├── conftest.py                # Shared fixtures
│   ├── unit/
│   │   ├── models/
│   │   │   ├── test_client.py
│   │   │   ├── test_collaborator.py
│   │   │   ├── test_contract.py
│   │   │   ├── test_event.py
│   │   │   └── test_role.py
│   │   └── test_decorators.py
│   ├── integration/
│   └── functional/
│
├── .github/
│   ├── workflows/ci.yml
│   └── ISSUE_TEMPLATE/
│       ├── epic.yml
│       ├── user_story.yml
│       └── bug_report.yml
│
├── .env.example
├── .gitignore
├── alembic.ini
├── pyproject.toml                 # black + isort + coverage config
├── setup.cfg                      # flake8 config
├── pytest.ini                     # pytest config
├── Makefile                       # format / lint / test shortcuts
├── requirements.txt               # Production dependencies
├── requirements-dev.txt           # Dev dependencies
└── README.md
```

---

## Security

- **SQL injection** — all queries go through SQLAlchemy ORM, parameterised only
- **Password storage** — bcrypt cost factor 12, timing-safe via `checkpw()`
- **Session tokens** — JWT signed with `SECRET_KEY`, expires after 8 hours,
  stored at `~/.epic_events/session` (outside the project), `chmod 600`
- **Role enforcement** — `@require_role` decorator on every service function;
  ownership checks enforced at the service layer
- **Least privilege** — DB user holds SELECT/INSERT/UPDATE/DELETE only,
  no CREATEDB or SUPERUSER
- **Secrets** — all credentials in `.env` (gitignored); `.env.example`
  committed with empty values
- **Error monitoring** — Sentry captures all unhandled exceptions with
  PII scrubbing via `before_send`

---

## Contributing

1. Branch from `develop`: `feature/US-XX-short-description`
2. Write tests first (TDD) — unit tests for logic, integration for services
3. Ensure `pytest --cov-fail-under=80` passes
4. Run `make check` before pushing
5. Open a pull request targeting `develop`, referencing the GitHub Issue: `Closes #XX`
6. CI runs automatically — the PR cannot be merged if linting or tests fail

---

*Epic Events CRM — Confidential internal tool*