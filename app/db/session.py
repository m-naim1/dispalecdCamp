from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# 1. Create the SQLAlchemy Engine
# connect_args={"check_same_thread": False} is needed ONLY for SQLite.
# Remove it if you switch to PostgreSQL/MySQL.
engine = create_engine(
                    settings.SQLALCHEMY_DATABASE_URI,
                    connect_args={'check_same_thread': False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

