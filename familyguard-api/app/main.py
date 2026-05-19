from fastapi import FastAPI
from app.database import engine
from app import models
from app.routers import auth, devices, pairing, location, dashboard, messages, sos


app = FastAPI(title="FamilyGuard API", version="0.1.0")
app.include_router(auth.router)
app.include_router(devices.router)
app.include_router(messages.router)
app.include_router(pairing.router)
app.include_router(location.router)
app.include_router(dashboard.router)
app.include_router(sos.router)
@app.get("/health")
def health():
    return {"status": "ok"}