import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, Column, String, DateTime, Float
from sqlalchemy.orm import sessionmaker
from agentic_platform.agentic_platform.models import Base, Project
from agentic_platform.agentic_platform.database import DATABASE_URL as SQLALCHEMY_DATABASE_URL

# Create a new engine instance
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Create a SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def update_database():
    # Create a new session
    db = SessionLocal()

    try:
        from sqlalchemy import text, inspect

        # Check if the 'projects' table exists
        inspector = inspect(engine)
        if 'projects' in inspector.get_table_names():
            # Check if 'repo_url' column exists
            columns = [col['name'] for col in inspector.get_columns('projects')]
            if 'repo_url' not in columns:
                # Add 'repo_url' column to existing table
                db.execute(text("ALTER TABLE projects ADD COLUMN repo_url STRING"))
                print("Added repo_url column to projects table")
            else:
                print("repo_url column already exists")
            
            # Check and update other columns
            if 'id' not in columns or inspector.get_columns('projects')[0]['type'] != String:
                db.execute(text("ALTER TABLE projects RENAME TO projects_old"))
                Base.metadata.create_all(bind=engine)
                db.execute(text("INSERT INTO projects (id, name, user_id, repo_url, created_at, updated_at, total_cost) SELECT CAST(id AS TEXT), name, user_id, repo_url, created_at, updated_at, total_cost FROM projects_old"))
                db.execute(text("DROP TABLE projects_old"))
                print("Updated projects table schema")
        else:
            # If the table doesn't exist, create it with all columns
            Base.metadata.create_all(bind=engine)
            print("Created projects table")

        # Commit the transaction
        db.commit()
        print("Database updated successfully")
    except Exception as e:
        print(f"An error occurred: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_database()
