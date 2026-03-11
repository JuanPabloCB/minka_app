from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Engine (psycopg3)
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)

# DB session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)
