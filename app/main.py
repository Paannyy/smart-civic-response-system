from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.complaints import router as complaints_router


app = FastAPI()

app.include_router(auth_router)
app.include_router(complaints_router)


@app.get("/")
def root():
    return {"message": "Smart Civic Response System API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}