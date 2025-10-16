"""
Database setup using SQLModel and SQLite
"""

from typing import Iterator
from sqlmodel import SQLModel, create_engine, Session
import os


DB_PATH = os.getenv("COMPLIANCE_DB_PATH", "compliance.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# check_same_thread False to allow usage in async context (FastAPI)
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    # Lightweight migration: add missing columns if the DB was created before schema updates
    with engine.connect() as conn:
        try:
            cols = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info('source')").fetchall()]
            if 'due_days' not in cols:
                conn.exec_driver_sql("ALTER TABLE source ADD COLUMN due_days INTEGER")
        except Exception:
            # If anything goes wrong, skip silently to avoid startup failure
            pass


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


