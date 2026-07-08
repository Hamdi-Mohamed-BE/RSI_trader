import os
from pathlib import Path
from sqlmodel import SQLModel, create_engine, Session

from app.core.config import settings

# Parse the database URL to make sure parent folder exists
if settings.DATABASE_URL.startswith("sqlite:///"):
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

# Create SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
    echo=False
)

def init_db():
    """Initializes the database, creating all tables if they do not exist."""
    # Import models here to ensure they are registered with SQLModel.metadata
    from app.db import models
    SQLModel.metadata.create_all(engine)

def get_db():
    """Dependency for database session context."""
    with Session(engine) as session:
        yield session
