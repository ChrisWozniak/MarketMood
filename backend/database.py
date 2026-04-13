from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import text
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./digest.db")
engine = create_engine(DATABASE_URL, echo=False)

# Columns to add if missing: (table, column, sql_type, default)
_MIGRATIONS = [
    ("settings", "market_tickers",        "TEXT",    "'[]'"),
    ("settings", "local_city",            "TEXT",    "''"),
    ("settings", "local_state",           "TEXT",    "''"),
    ("settings", "local_country",         "TEXT",    "''"),
    ("settings", "local_locations",       "TEXT",    "'[]'"),
    ("settings", "world_countries",       "TEXT",    "'[]'"),
    ("settings", "articles_per_category", "INTEGER", "5"),
    ("settings", "language",              "TEXT",    "'en'"),
]


def _run_migrations():
    """Add any missing columns to existing tables (SQLite safe)."""
    with engine.connect() as conn:
        for table, column, col_type, default in _MIGRATIONS:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type} DEFAULT {default}"))
                conn.commit()
                print(f"[db] Migration: added {table}.{column}")
            except Exception:
                pass  # column already exists — ignore


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    _run_migrations()


def get_session():
    with Session(engine) as session:
        yield session
