from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.core.config import settings
import os

# Use in-memory SQLite for tests, file-based for production
database_url = settings.DATABASE_URL
if "pytest" in os.environ.get("_", "") or os.environ.get("PYTEST_CURRENT_TEST"):
    database_url = "sqlite:///:memory:"

# Ensure data directory exists for SQLite
if database_url.startswith("sqlite"):
    db_path = database_url.replace("sqlite:///", "").replace("sqlite://", "")
    if db_path and not db_path.startswith(":memory:"):
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)