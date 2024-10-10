from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import os

DATABASE_URL = "sqlite:///./aider_projects.db"
SQLALCHEMY_DATABASE_URL = DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    from . import models
    Base.metadata.drop_all(bind=engine)  # This line drops all tables
    Base.metadata.create_all(bind=engine)
    
    # Add new columns if they don't exist
    with engine.connect() as conn:
        inspector = inspect(engine)
        if 'projects' not in inspector.get_table_names():
            models.Project.__table__.create(bind=engine)
        else:
            existing_columns = [col['name'] for col in inspector.get_columns('projects')]
            
            if 'created_at' not in existing_columns:
                conn.execute(text("ALTER TABLE projects ADD COLUMN created_at DATETIME"))
            
            if 'updated_at' not in existing_columns:
                conn.execute(text("ALTER TABLE projects ADD COLUMN updated_at DATETIME"))
            
            if 'total_cost' not in existing_columns:
                conn.execute(text("ALTER TABLE projects ADD COLUMN total_cost FLOAT DEFAULT 0.0"))
            
            if 'repo_url' not in existing_columns:
                conn.execute(text("ALTER TABLE projects ADD COLUMN repo_url TEXT"))
        
        # Check if users table exists, if not create it
        if 'users' not in inspector.get_table_names():
            models.User.__table__.create(bind=engine)
