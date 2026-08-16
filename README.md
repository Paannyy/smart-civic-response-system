# Smart Civic Response System

## Overview

A full-stack civic issue reporting system. Citizens can create and track complaints; authorities manage assigned work; administrators manage users and oversee complaints.

## Project Structure

```text
smart-civic-response-system/
├── backend/       # FastAPI application, tests, Alembic migrations
├── frontend/      # React/Vite application
├── .gitignore
├── README.md
└── start-dev.ps1
```

## Setup

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Configure `DATABASE_URL` in `backend/.env` before starting the API.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Run `./start-dev.ps1` from the repository root to start both development servers.

## Validation

```powershell
# from backend/
.\.venv\Scripts\python.exe -m pytest -q

# from frontend/
npm run lint
npm run build
```
