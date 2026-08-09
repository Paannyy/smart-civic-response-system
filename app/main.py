from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Smart Civic Response System API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}