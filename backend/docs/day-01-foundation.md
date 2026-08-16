# Day 1 — Backend Foundation

## 1. Project Goal

Smart Civic Response System is a backend application for managing civic complaints.

The backend will support:
- Citizens
- Authorities
- Admins
- Complaint registration
- Complaint tracking
- Assignment
- Comments
- Complaint history
- Authentication
- Role-based access control

---

# 2. FastAPI

FastAPI is the Python web framework we are using to build REST APIs.

It provides:
- API routing
- Request handling
- Data validation
- Dependency injection
- Automatic OpenAPI documentation
- Swagger UI

Our application is created using:

    app = FastAPI()

---

# 3. Uvicorn

Uvicorn is an ASGI server.

It runs our FastAPI application and accepts HTTP requests.

Command:

    uvicorn app.main:app --reload

Meaning:

- app.main → app/main.py
- :app → FastAPI object named app
- --reload → restart the server when code changes

---

# 4. REST API

REST is an architectural style commonly used for web APIs.

Our API uses HTTP methods such as:

GET
POST
PUT
PATCH
DELETE

Examples:

GET /complaints
POST /complaints
GET /complaints/{id}

---

# 5. HTTP Status Codes

Important status codes:

200 → Successful request
201 → Resource created
400 → Bad request
401 → Authentication required/invalid authentication
403 → Forbidden
404 → Resource not found
500 → Internal server error

---

# 6. ORM

ORM means Object Relational Mapping.

It maps Python classes/objects to relational database tables.

Conceptually:

Python class
    ↓
SQLAlchemy ORM
    ↓
PostgreSQL table

---

# 7. SQLAlchemy

SQLAlchemy is the database toolkit and ORM used by our application.

Architecture:

FastAPI
    ↓
SQLAlchemy
    ↓
PostgreSQL

It provides:
- Database connectivity
- ORM models
- Sessions
- Querying
- Transactions

---

# 8. SQLAlchemy Engine

The Engine is the core database connectivity object.

It knows how to communicate with the configured database and manages database connections.

Conceptually:

Application
    ↓
SQLAlchemy Engine
    ↓
PostgreSQL

---

# 9. SQLAlchemy Session

A Session provides a unit of work for interacting with the database.

It can be used to:
- Query
- Insert
- Update
- Delete
- Commit
- Roll back

Typical lifecycle:

Request
    ↓
Create Session
    ↓
Database operations
    ↓
Commit/Rollback
    ↓
Close Session

---

# 10. Database Dependency

We created get_db() to provide a database session to API endpoints.

The session is created for the request and closed after the request.

Conceptually:

Request
    ↓
get_db()
    ↓
Session
    ↓
API operation
    ↓
Session closes

---

# 11. PostgreSQL

PostgreSQL is our relational database.

Database:

smart_civic_db

Current state after Day 1:

smart_civic_db
    └── No application tables yet

Tables will be created through SQLAlchemy models and Alembic migrations.

---

# 12. Database Connection URL

Our application uses a database URL containing:

- Database type
- Username
- Password
- Host
- Port
- Database name

Example structure:

postgresql://username:password@localhost:5432/database_name

Our actual password is stored in .env and is not committed to Git.

---

# 13. Environment Variables

Sensitive configuration is stored in:

.env

Examples:

DATABASE_URL
SECRET_KEY

.env must not be committed to GitHub.

It is included in .gitignore.

---

# 14. Alembic

Alembic is the database migration tool used with SQLAlchemy.

It allows us to track database schema changes.

Conceptually:

SQLAlchemy Model
    ↓
Alembic Migration
    ↓
PostgreSQL Schema

We have initialized Alembic, but we have not created a migration yet because we don't have application models.

---

# 15. Project Architecture

Current architecture:

Client
   ↓
FastAPI
   ↓
Database Dependency
   ↓
SQLAlchemy Session
   ↓
SQLAlchemy Engine
   ↓
PostgreSQL
   ↓
smart_civic_db

---

# 16. Git

Git is used for version control.

Our first commit:

chore: initialize backend infrastructure

The .env and .venv directories are ignored.

The repository should never contain:
- Database passwords
- Secret keys
- Virtual environment files