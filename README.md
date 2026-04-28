# 🏕️ Displaced Camp Manager API

A production-grade REST API for managing displaced families and individuals across humanitarian shelter centers. Built to handle real-world camp operations — family registration, member tracking, shelter assignments, and role-based staff access — with a clean layered architecture and a built-in admin dashboard.

> **Status:** Backend API complete · Frontend in development

---

## 📌 What This Project Does

Displaced families in humanitarian camps need to be registered, tracked, and managed across multiple shelter centers and blocks. This system provides:

- **Family registration** with full demographic data, shelter assignments, and residency status
- **Member tracking** per family, including vulnerability flags (disability, injury, pregnancy, chronic illness)
- **Dual authentication** — system staff log in with username/password; families identify themselves using their national ID and date of birth
- **Role-based access control** so each staff role only sees and modifies what they need
- **Admin dashboard** with live statistics — total families, block occupancy, vulnerability counts, and shelter center breakdowns
- **Soft delete** — families and records are archived, not permanently erased

---

## 🏗️ Architecture

```
app/
├── api/
│   └── v1/
│       ├── endpoints/      # Route handlers (auth, families, users)
│       └── deps.py         # FastAPI dependency injection (auth guards)
├── core/
│   ├── config.py           # Settings from environment variables
│   ├── security.py         # JWT signing, bcrypt hashing
│   └── errors.py           # Custom exception classes
├── models/                 # SQLAlchemy ORM models
├── schemas/                # Pydantic request/response schemas
├── services/               # Business logic layer
├── db/
│   └── session.py          # Database engine and session
└── admin.py                # starlette-admin dashboard + auth
templates/
└── index.html              # Custom admin dashboard template
alembic/                    # Database migrations
```

The project follows a strict **router → service → model** pattern. Endpoints never query the database directly — all business logic lives in the service layer, making it easy to test and extend.

---

## ⚙️ Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 (mapped_column style) |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Authentication | JWT (python-jose) + bcrypt (passlib) |
| Admin panel | starlette-admin |
| Database | SQLite (dev) · PostgreSQL-ready |
| Runtime | Python 3.11+ · uvicorn |
| Package manager | uv |

---

## 🔐 Authentication & Authorization

The system implements **two separate authentication flows** by design:

**System staff** (SUPERADMIN, MANAGER, BLOCK_HEAD) authenticate via:
```
POST /api/v1/auth/login
Body: username + password (OAuth2 form)
Returns: JWT Bearer token
```

**Families** authenticate using their existing registration data — no account needed:
```
POST /api/v1/auth/family-login
Body: national_id + date_of_birth
Returns: JWT Bearer token scoped to their family record
```

### Role Permission Matrix

| Operation | SUPERADMIN | MANAGER | BLOCK_HEAD |
|---|:---:|:---:|:---:|
| Read families & members | ✅ | ✅ | ✅ |
| Register / update family | ✅ | ✅ | ❌ |
| Archive / restore family | ✅ | ✅ | ❌ |
| Add / update members | ✅ | ✅ | ❌ |
| Manage system users | ✅ | ❌ | ❌ |
| Access admin panel | ✅ | ✅ | ❌ |

Authorization is enforced via a `require_role()` FastAPI dependency injected at the route level — no role checks scattered through business logic.

---

## 🗂️ Data Model

**Family** — the core entity. Tracks residency status, shelter assignment (center → block), housing type, shelter quality, phone numbers, and flags for female-headed and child-headed households.

**Member** — belongs to a family. Stores full name, gender, date of birth, marital status, relationship to family head, and vulnerability flags: `disabled`, `injured`, `pregnant`, `breastfeeding`, `has_chronic_disease`.

**Lookup tables** — `Governor`, `City`, `ShelterCenter`, `ShelterBlock`, `ShelterQuality`, `RelationshipToHead` — all referenced by FK from Family/Member.

**User** — system operators only. Families are never stored here. BLOCK_HEAD users carry a `block_id` FK to scope their access to one block.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Installation

```bash
git clone https://github.com/m-naim1/displacedCamp
cd displacedCamp

# Create virtual environment and install dependencies
uv sync

# Copy environment config
cp .env.example .env
# Edit .env and set SECRET_KEY to a strong random value:
# python -c "import secrets; print(secrets.token_hex(32))"
```

### Database setup

```bash
# Apply migrations
uv run alembic upgrade head

# The server auto-creates a superadmin on first run:
# username: admin  |  password: admin1234
# Change this password immediately after first login.
```

### Run the server

```bash
uv run uvicorn app.main:app --reload
```

| URL | Description |
|---|---|
| http://localhost:8000 | API root |
| http://localhost:8000/docs | Swagger UI (interactive API docs) |
| http://localhost:8000/redoc | ReDoc API docs |
| http://localhost:8000/admin | Admin dashboard |

### Example: login and make an authenticated request

```bash
# Get a token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin1234"

# Use the token
curl http://localhost:8000/api/v1/families/ \
  -H "Authorization: Bearer <your_token>"
```

### Environment variables

```env
SECRET_KEY=your-secret-key-here        # Required — sign JWT tokens
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
SQLALCHEMY_DATABASE_URI=sqlite:///./camp_manager.db
```

---

## 📡 API Endpoints

### Auth
| Method | Endpoint | Description | Access |
|---|---|---|---|
| POST | `/api/v1/auth/login` | Staff login → JWT | Public |
| POST | `/api/v1/auth/family-login` | Family login by national ID + DOB | Public |
| GET | `/api/v1/auth/me` | Get current user profile | Authenticated |
| POST | `/api/v1/auth/register` | Create a new system user | SUPERADMIN |

### Families
| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/api/v1/families/` | List all families | Staff |
| POST | `/api/v1/families/` | Register a new family | MANAGER+ |
| GET | `/api/v1/families/{id}` | Get family details | Staff |
| PUT | `/api/v1/families/{id}` | Update family record | MANAGER+ |
| PATCH | `/api/v1/families/{id}/archive` | Soft-delete a family | MANAGER+ |
| PATCH | `/api/v1/families/{id}/restore` | Restore archived family | MANAGER+ |
| POST | `/api/v1/families/{id}/members` | Add member to family | MANAGER+ |
| PUT | `/api/v1/families/members/{id}` | Update member | MANAGER+ |
| DELETE | `/api/v1/families/members/{id}` | Remove member | MANAGER+ |

### Users
| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/api/v1/users/` | List system users | SUPERADMIN |
| GET | `/api/v1/users/{id}` | Get user details | SUPERADMIN |
| PATCH | `/api/v1/users/{id}` | Update user | SUPERADMIN |
| DELETE | `/api/v1/users/{id}` | Deactivate user | SUPERADMIN |

---

## 🛠️ Skills Demonstrated

- **REST API design** — resource-oriented endpoints, correct HTTP methods and status codes, consistent error responses
- **FastAPI** — dependency injection, OAuth2 password bearer, background tasks, Pydantic v2 schemas
- **SQLAlchemy 2.0** — typed `Mapped` columns, relationships with `foreign_keys`, validators with `@validates`, soft delete patterns
- **Authentication** — JWT with HS256, bcrypt password hashing, token expiry, two separate auth strategies in one API
- **Authorization** — role-based access control via reusable dependency factory, scope-limited tokens
- **Database migrations** — Alembic `--autogenerate` workflow, environment-aware migration scripts
- **Domain modeling** — real-world humanitarian data including national ID validation, residency status, shelter hierarchy, vulnerability tracking
- **Admin dashboard** — starlette-admin with custom `AuthProvider`, overridden index view, live database statistics
- **Error handling** — custom exception classes (`NotFoundError`, `ConflictError`) mapped to correct HTTP responses
- **Project structure** — layered architecture separating concerns (routes, services, models, schemas)

---

## 🔮 Roadmap

### Frontend (Next)
- [ ] React + TypeScript frontend
- [ ] Family registration form with validation
- [ ] Interactive camp map showing block occupancy
- [ ] Family self-service portal (view own record using national ID + DOB)
- [ ] Role-aware navigation — staff see different views than families

### API Enhancements
- [ ] PostgreSQL support for production deployments
- [ ] Audit log — track who changed what and when
- [ ] Pagination and advanced filtering on family list
- [ ] Export families to Excel / CSV
- [ ] Search by member name, national ID, or phone number
- [ ] Statistics endpoint for dashboard data
- [ ] Health check endpoint with database connectivity test

### Infrastructure
- [ ] Docker + docker-compose setup
- [ ] GitHub Actions CI pipeline (lint, test, migrate)
- [ ] pytest test suite covering auth, RBAC, and family CRUD
- [ ] `.env` validation on startup
- [ ] Rate limiting on auth endpoints

---

## 📁 Project Structure

```
displacedCamp/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── auth.py
│   │       │   ├── families.py
│   │       │   └── users.py
│   │       ├── deps.py
│   │       └── router.py
│   ├── core/
│   │   ├── config.py
│   │   ├── errors.py
│   │   └── security.py
│   ├── db/
│   │   └── session.py
│   ├── models/
│   │   ├── enums.py
│   │   ├── family.py
│   │   ├── lookups.py
│   │   └── user.py
│   ├── schemas/
│   │   ├── family.py
│   │   └── user.py
│   ├── services/
│   │   ├── family_service.py
│   │   └── user_service.py
│   ├── admin.py
│   └── main.py
├── alembic/
│   └── versions/
├── templates/
│   └── index.html
├── .env.example
├── .gitignore
├── alembic.ini
├── pyproject.toml
└── README.md
```

---

## 👤 Author

**Mohammed Naim**
Backend Developer · Python · FastAPI · SQLAlchemy

[GitHub](https://github.com/m-naim1)

---

*Built as a portfolio project demonstrating production-grade API development with Python. This system is designed around a real humanitarian need — tracking and supporting displaced families in camp settings.*