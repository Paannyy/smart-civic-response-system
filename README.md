# Smart Civic Response System

A production-grade, full-stack civic issue reporting and resolution platform engineered with FastAPI, PostgreSQL, React 19, SQLAlchemy 2.0, and Docker.

---

## 1. System Architecture

```text
                                  +-----------------------------+
                                  |    React 19 + Vite Frontend |
                                  |   (Nginx / Port 3000 / SPA) |
                                  +--------------+--------------+
                                                 |
                                         REST API (JSON / JWT)
                                                 |
                                                 v
                                  +-----------------------------+
                                  |       FastAPI Backend       |
                                  |   (Uvicorn / Port 8000)     |
                                  +--------------+--------------+
                                         |              |
                    +--------------------+              +--------------------+
                    |                                                        |
                    v                                                        v
     +-----------------------------+                          +-----------------------------+
     |     PostgreSQL Database     |                          |   Attachment Storage Engine |
     |   (Port 5432 / Persistent)  |                          |  (Local FS / S3 Abstraction)|
     +-----------------------------+                          +-----------------------------+
```

### Backend Components
- **Framework:** FastAPI (Python 3.11) with Uvicorn ASGI server
- **Database & ORM:** PostgreSQL 16 with SQLAlchemy 2.0 (bidirectional typed relationships)
- **Migrations:** Alembic
- **Security:** JWT (HMAC-SHA256), Argon2 password hashing, HTTP Security Headers, and CORS origin restriction
- **Abuse Prevention:** Sliding-window in-memory rate limiter on authentication endpoints
- **Observability:** Structured access logging with `X-Request-ID` propagation and unified 500 error sanitization
- **Health Probes:** Distinct `/health` (liveness) and `/ready` (database dependency readiness)
- **Notifications & Email:** In-database activity alerts with SMTP email dispatch abstraction
- **Evidence Storage:** Dual-driver `AttachmentStorage` supporting local filesystem and S3/MinIO cloud storage
- **Test Suite:** Pytest (68 test cases with in-memory SQLite isolation)

### Frontend Components
- **Framework:** React 19 + Vite
- **Design System:** Responsive, modern CSS design system
- **State Management:** Native React hooks with centralized API service client
- **Production Server:** Multi-stage Docker build with Nginx Alpine static serving and SPA routing

---

## 2. Key Modules & Production Features

### Role-Based Access Control (RBAC)
- **Citizen:** Submit civic issues, upload supporting evidence (photos/PDFs), monitor progress, and review transparent status timeline.
- **Authority:** View workload-assigned complaints for matching municipal department, update lifecycle stages (`assigned` → `in_progress` → `resolved`), and inspect full audit trails.
- **Administrator:** System-wide complaint oversight, manual assignment override, user activation/deactivation, and real-time civic analytics.

### Workload-Aware Automatic Assignment
Routes newly submitted complaints to active authorities within the matching department who have the lowest active load (`assigned` + `in_progress`), using deterministic tie-breaking.

### Rate Limiting & Abuse Protection
Protects `/auth/login` and `/auth/register` against brute-force attacks via sliding-window rate limiting (configurable via `RATE_LIMIT_AUTH_PER_MINUTE`, default 15 req/min). Returns HTTP 429 Too Many Requests when limits are exceeded.

### Security Headers & Sanitized Logging
- Injects standard production headers on all responses: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `X-XSS-Protection: 1; mode=block`, and `Content-Security-Policy`.
- `RequestIDAndLoggingMiddleware` assigns/propagates `X-Request-ID` and logs request duration without logging passwords, tokens, or authorization headers.
- Global exception handler catches unexpected errors, logs full tracebacks with request IDs, and returns a clean HTTP 500 response without leaking internal server details.

### Liveness vs Readiness Probes
- `GET /health`: Liveness probe confirming the application process is running.
- `GET /ready`: Readiness probe verifying live database connectivity via `SELECT 1`.

### Notifications & Email Dispatch Architecture
- **In-Database Alerts:** Tracks events on complaint creation, assignment, status update, and resolution.
- **Email Service (`EmailService`):** Supports SMTP configuration (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_TLS`).
- *Graceful Fallback:* If SMTP is unconfigured, database notifications function normally without errors or transaction interruptions.

### Pluggable Evidence Attachment Storage
- **Supported Formats:** JPG, JPEG, PNG, PDF (<= 5 MB).
- **Security:** UUID4 filename hashing, path traversal guards, and complaint RBAC download authorization.
- **Drivers:** `LocalStorageProvider` (development) and `S3StorageProvider` (AWS S3 / MinIO cloud deployment).

---

## 3. Environment Configuration

### Backend Configuration (`backend/.env`)

```env
# Application & Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/smart_civic
SECRET_KEY=replace_with_a_secure_random_key_min_32_characters
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000
ENVIRONMENT=development

# Abuse Protection
RATE_LIMIT_ENABLED=true
RATE_LIMIT_AUTH_PER_MINUTE=15

# Attachment Storage (local or s3)
ATTACHMENT_STORAGE=local
UPLOAD_DIR=uploads
S3_ENDPOINT_URL=
S3_BUCKET=
S3_REGION=us-east-1
S3_ACCESS_KEY=
S3_SECRET_KEY=

# Email / SMTP Configuration (Optional)
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM=notifications@smartcivic.local
SMTP_TLS=true
```

### Frontend Configuration (`frontend/.env`)

```env
VITE_API_URL=http://localhost:8000
```

---

## 4. Running with Docker (Recommended)

### Prerequisites
- Docker Engine / Docker Desktop (v20.10+)
- Docker Compose (v2.0+)

### Quickstart

1. **Start Complete Stack:**
   ```bash
   docker compose up --build
   ```

2. **Access Application:**
   - **Frontend UI:** [http://localhost:3000](http://localhost:3000)
   - **Backend API:** [http://localhost:8000](http://localhost:8000)
   - **API Documentation (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Liveness Check:** [http://localhost:8000/health](http://localhost:8000/health)
   - **Readiness Check:** [http://localhost:8000/ready](http://localhost:8000/ready)

3. **Run Database Migrations:**
   ```bash
   docker compose exec backend alembic upgrade head
   ```

4. **Stop Stack:**
   ```bash
   docker compose down
   ```

---

## 5. Local Development Setup (Manual)

### 1. Backend Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Run migrations:
```powershell
alembic upgrade head
```

Start the API server:
```powershell
uvicorn app.main:app --reload
```

### 2. Frontend Setup

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Frontend runs at `http://localhost:5173`.

---

## 6. Testing & Quality Verification

### Run Backend Tests (68 Tests)
```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -v
```

### Run Frontend Linting & Production Build
```powershell
cd frontend
npm run lint
npm run build
```

### Validate Docker Compose Configuration
```powershell
docker compose config
```

### Code Cleanliness
```powershell
git diff --check
```

---

## 7. Production Deployment Considerations

| Area | Development Mode | Production Mode |
| :--- | :--- | :--- |
| **Database** | Local PostgreSQL or in-memory SQLite | Managed PostgreSQL (RDS / Cloud SQL) with connection pooling |
| **Evidence Storage** | Local directory (`uploads/`) | AWS S3 or MinIO object bucket (`ATTACHMENT_STORAGE=s3`) |
| **Email Delivery** | Local logging (SMTP disabled) | Production SMTP relay (SendGrid, Mailgun, AWS SES) |
| **Rate Limiting** | In-memory sliding window | In-memory or Redis-backed distributed rate limiter |
| **Containers** | Local Docker Compose | Kubernetes / Docker Swarm with non-root containers |
| **SSL/TLS** | HTTP localhost | HTTPS with automated certificate renewal (Let's Encrypt / ALB) |
