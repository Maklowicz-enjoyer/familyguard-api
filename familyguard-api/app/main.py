from fastapi import FastAPI
from app.database import engine
from app import models
from app.routers import auth

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="FamilyGuard API", version="0.1.0")
app.include_router(auth.router)

@app.get("/health")
def health():
    return {"status": "ok"}