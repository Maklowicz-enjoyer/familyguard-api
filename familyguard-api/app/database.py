# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import os

def read_secret(secret_name: str) -> str:
   
    secret_path = f"/run/secrets/{secret_name}"
    if os.path.exists(secret_path):
        with open(secret_path, "r") as f:
            return f.read().strip()
    # Fallback tylko dla lokalnego dev bez Docker Secrets
    env_val = os.getenv(secret_name.upper().replace("-", "_"))
    if env_val:
        return env_val
    raise RuntimeError(f"Secret '{secret_name}' not found")

DB_USER = os.getenv("DB_USER", "appuser")
DB_NAME = os.getenv("DB_NAME", "parental_app")
DB_HOST = os.getenv("DB_HOST", "pg_primary")
DB_PASSWORD = read_secret("db-pass")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    """Dependency injection dla FastAPI — tworzy i zamyka sesję."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()