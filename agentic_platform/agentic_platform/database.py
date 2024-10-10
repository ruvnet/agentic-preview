from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
import os

DATABASE_URL = "sqlite:///./aider_projects.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    from . import models
    Base.metadata.create_all(bind=engine)
    
    # Add new columns if they don't exist
    with engine.connect() as conn:
        inspector = inspect(engine)
        existing_columns = [col['name'] for col in inspector.get_columns('projects')]
        if 'created_at' not in existing_columns:
            conn.execute(text("ALTER TABLE projects ADD COLUMN created_at DATETIME"))
        if 'last_updated' not in existing_columns:
            conn.execute(text("ALTER TABLE projects ADD COLUMN last_updated DATETIME"))
        if 'total_cost' not in existing_columns:
            conn.execute(text("ALTER TABLE projects ADD COLUMN total_cost FLOAT DEFAULT 0.0"))
