import logging
import traceback
from fastapi import Depends, FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.admin import router as admin_router
from app.api.attachments import router as attachments_router
from app.api.auth import router as auth_router
from app.api.complaints import router as complaints_router
from app.api.notifications import router as notifications_router
from app.core.middleware import (
    RequestIDAndLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from app.db.database import settings
from app.db.dependencies import get_db

logger = logging.getLogger("smart_civic.error")

app = FastAPI(
    title="Smart Civic Response System API",
    version="1.0.0",
)

# Custom middlewares
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDAndLoggingMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        f"[{request_id}] Unhandled Exception: {exc.__class__.__name__}: {str(exc)}\n"
        f"{traceback.format_exc()}"
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred.",
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )


app.include_router(auth_router)
app.include_router(complaints_router)
app.include_router(admin_router)
app.include_router(notifications_router)
app.include_router(attachments_router)


@app.get("/")
def root():
    return {"message": "Smart Civic Response System API"}


@app.get("/health")
def liveness_check():
    """Liveness probe: confirms application process is running."""
    return {
        "status": "healthy",
        "database": "connected",
    }



@app.get("/ready")
def readiness_check(
    response: Response,
    db: Session = Depends(get_db),
):
    """Readiness probe: confirms database and core dependencies are reachable."""
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "database": "connected",
        }
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unready",
            "database": "disconnected",
        }