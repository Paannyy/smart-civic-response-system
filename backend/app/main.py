from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.complaints import router as complaints_router
from app.api.admin import router as admin_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(complaints_router)
app.include_router(admin_router)


@app.get("/")
def root():
    return {"message": "Smart Civic Response System API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}