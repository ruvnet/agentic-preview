#!/bin/bash

# Install script for agentic_platform

# Create the directory structure
mkdir -p agentic_platform/agentic_platform/api
mkdir -p agentic_platform/agentic_platform/utils
mkdir -p agentic_platform/projects  # Directory for project files

# Create __init__.py files
touch agentic_platform/agentic_platform/__init__.py
touch agentic_platform/agentic_platform/api/__init__.py
touch agentic_platform/agentic_platform/utils/__init__.py

# Create README.md
cat << EOF > agentic_platform/README.md
# Agentic Platform

This is the Agentic Platform project combining agentic_editor and agentic_preview.

## Installation

Run \`./install.sh\` to set up the project.

## Running the Application

Navigate to the \`agentic_platform\` directory and run:

\`\`\`bash
poetry run python -m agentic_platform.main
\`\`\`

EOF

# Create requirements.txt
cat << EOF > agentic_platform/requirements.txt
fastapi
uvicorn[standard]
sqlalchemy
pydantic
EOF

# Create pyproject.toml
cat << EOF > agentic_platform/pyproject.toml
[tool.poetry]
name = "agentic_platform"
version = "0.1.0"
description = "Agentic Platform combining agentic_editor and agentic_preview"
authors = ["Your Name <your.email@example.com>"]
license = "MIT"

[tool.poetry.dependencies]
python = "^3.8"
fastapi = "^0.70.0"
uvicorn = "^0.15.0"
sqlalchemy = "^1.4.22"
pydantic = "^1.8.2"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
EOF

# Create agentic_platform/agentic_platform/main.py
cat << EOF > agentic_platform/agentic_platform/main.py
import logging
from fastapi import FastAPI
from .api import aider, deploy, users, projects, architect, editor, cost_summary
from .database import init_db

# Initialize logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s:%(lineno)d %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

# Initialize database
init_db()

app = FastAPI()

# Include routers
app.include_router(aider.router)
app.include_router(deploy.router)
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(architect.router)
app.include_router(editor.router)
app.include_router(cost_summary.router)

# Redirect root to docs
@app.get("/")
async def redirect_to_docs():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agentic_platform.main:app", host="0.0.0.0", port=5000)
EOF

# Create agentic_platform/agentic_platform/database.py
cat << EOF > agentic_platform/agentic_platform/database.py
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
EOF

# Create agentic_platform/agentic_platform/models.py
cat << EOF > agentic_platform/agentic_platform/models.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)
    projects = relationship("Project", back_populates="user")

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    user_id = Column(String, ForeignKey("users.user_id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    total_cost = Column(Float, default=0.0)
    user = relationship("User", back_populates="projects")
EOF

# Create agentic_platform/agentic_platform/crud.py
cat << EOF > agentic_platform/agentic_platform/crud.py
from sqlalchemy.orm import Session
from . import models
from datetime import datetime, timedelta
import os
import shutil

def get_db():
    from .database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def update_project_user_data(project_name: str, user_id: str, db: Session):
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        user = models.User(user_id=user_id)
        db.add(user)
    
    project = db.query(models.Project).filter(models.Project.name == project_name, models.Project.user_id == user_id).first()
    if not project:
        project = models.Project(name=project_name, user_id=user_id)
        db.add(project)
    else:
        project.last_updated = datetime.utcnow()
    
    try:
        db.commit()
    except:
        db.rollback()

def remove_old_projects(db: Session, age: timedelta = None, user_id: str = None):
    query = db.query(models.Project)
    
    if age:
        cutoff_date = datetime.utcnow() - age
        query = query.filter(models.Project.last_updated < cutoff_date)
    
    if user_id:
        query = query.filter(models.Project.user_id == user_id)
    
    projects_to_remove = query.all()
    
    for project in projects_to_remove:
        project_path = os.path.join("projects", f"{project.name}_{project.user_id}")
        if os.path.exists(project_path):
            shutil.rmtree(project_path)
        db.delete(project)
    
    db.commit()
    
    return [{"name": p.name, "user_id": p.user_id, "last_updated": p.last_updated} for p in projects_to_remove]

def cleanup_projects(db: Session):
    projects_dir = "projects"
    if not os.path.exists(projects_dir):
        return []
    existing_projects = set(os.listdir(projects_dir))
    
    # Get all projects from the database
    db_projects = db.query(models.Project).all()
    
    removed_projects = []
    for project in db_projects:
        project_folder = f"{project.name}_{project.user_id}"
        if project_folder not in existing_projects:
            # Remove the project from the database
            db.delete(project)
            removed_projects.append({"name": project.name, "user_id": project.user_id})
    
    # Commit the changes
    db.commit()
    
    return removed_projects

def update_project_cost(db: Session, project_name: str, user_id: str, cost: float):
    project = db.query(models.Project).filter(models.Project.name == project_name, models.Project.user_id == user_id).first()
    if project:
        project.total_cost += cost
        project.last_updated = datetime.utcnow()
        db.commit()
EOF

# Create agentic_platform/agentic_platform/api/aider.py
cat << EOF > agentic_platform/agentic_platform/api/aider.py
import os
import subprocess
import asyncio
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from ..crud import get_db, update_project_user_data, update_project_cost
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter()

class AiderConfig(BaseModel):
    chat_mode: str = Field("code", example="code")
    edit_format: str = Field("diff", example="diff")
    model: str = Field("claude-3-5-sonnet-20240620", example="claude-3-5-sonnet-20240620")
    prompt: Optional[str] = Field(None, example="Initial main.py with fastapi and dockerfile")
    files: List[str] = Field(default_factory=list, example=["main.py", "utils.py"])
    project_name: str = Field(..., example="sonnet")
    user_id: str = Field(..., example="test")
    file_list: Optional[List[str]] = Field(None, example=["auth_service.py", "api_gateway.py", "microservice_example.py"])

    @validator('files')
    def validate_files(cls, v):
        for file in v:
            if '..' in file or file.startswith('/'):
                raise ValueError(f"Invalid file path: {file}")
        return v

def run_aider(config: AiderConfig, project_path: str):
    command = [
        "aider",
        "--chat-mode", config.chat_mode,
        "--edit-format", config.edit_format,
        "--model", config.model,
        "--yes",  # Non-interactive mode
        "--no-git"  # Run without git integration
    ]

    if config.prompt:
        command.extend(["--message", config.prompt])

    command.extend(config.files)

    env = os.environ.copy()
    api_key = env.get('OPENAI_API_KEY')

    if api_key is None:
        logger.error("OPENAI_API_KEY is not set in the environment.")
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not set in the environment."
        )

    try:
        logger.info(f"Running Aider command: {' '.join(command)}")
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            cwd=project_path,
            env=env
        )
        
        output, error = process.communicate()
        
        if process.returncode != 0:
            logger.error(f"Aider command failed with return code {process.returncode}")
            logger.error(f"Error output: {error}")
            raise HTTPException(
                status_code=500,
                detail=f"Aider command failed: {error}"
            )
        
        logger.info("Aider command completed successfully")
        return output, error
    except Exception as e:
        logger.exception("An error occurred while running Aider")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while running Aider: {str(e)}"
        )

def process_aider_output(output_lines):
    processed_output = {
        "summary": [],
        "file_changes": {},
        "commands": [],
        "messages": []
    }
    current_message = []

    for line in output_lines:
        if line.startswith("pip "):
            processed_output["commands"].append(line)
        else:
            current_message.append(line)

    if current_message:
        processed_output["messages"].append("\n".join(current_message))

    return processed_output

@router.post("/run-aider")
async def execute_aider(config: AiderConfig, db: Session = Depends(get_db)):
    project_path = os.path.join("projects", f"{config.project_name}_{config.user_id}")
    
    # Create project directory if it doesn't exist
    os.makedirs(project_path, exist_ok=True)

    # Ensure all files exist in the project directory
    for file in config.files:
        file_path = os.path.join(project_path, file)
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                f.write('')  # Create an empty file

    # Update project and user data
    update_project_user_data(config.project_name, config.user_id, db)

    output, error = await asyncio.to_thread(run_aider, config, project_path)
    
    processed_output = process_aider_output(output.split('\n'))

    # Estimate cost (you may need to adjust this based on actual usage)
    estimated_cost = len(config.prompt or '') * 0.00001  # Example cost calculation
    update_project_cost(db, config.project_name, config.user_id, estimated_cost)

    return {
        "project_name": config.project_name,
        "user_id": config.user_id,
        "aider_output": processed_output,
        "estimated_cost": estimated_cost
    }
EOF

# Create agentic_platform/agentic_platform/api/deploy.py
cat << EOF > agentic_platform/agentic_platform/api/deploy.py
# [Include the entire code from the deploy endpoints in agentic_preview main.py]
EOF

# Similarly, create other api modules with their respective code
# For brevity, only the file creation commands are shown here; include the full code in your script

# Create users.py
cat << EOF > agentic_platform/agentic_platform/api/users.py
from fastapi import APIRouter, Depends
from ..crud import get_db
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("/users")
async def list_users(db: Session = Depends(get_db)):
    from ..models import User
    users = db.query(User).all()
    return {"users": {user.user_id: [{"name": project.name, "created_at": project.created_at, "last_updated": project.last_updated} for project in user.projects] for user in users}}
EOF

# Create projects.py
cat << EOF > agentic_platform/agentic_platform/api/projects.py
from fastapi import APIRouter, Depends, Query
from ..crud import get_db, cleanup_projects, remove_old_projects
from sqlalchemy.orm import Session
from typing import Optional

router = APIRouter()

@router.get("/projects")
async def list_projects(db: Session = Depends(get_db)):
    from ..models import Project
    projects = db.query(Project).all()
    return {"projects": [{"name": project.name, "user_id": project.user_id, "created_at": project.created_at, "last_updated": project.last_updated} for project in projects]}

@router.post("/cleanup")
async def cleanup(db: Session = Depends(get_db)):
    removed_projects = cleanup_projects(db)
    return {
        "message": f"Cleanup completed. Removed {len(removed_projects)} projects.",
        "removed_projects": removed_projects
    }

@router.post("/remove_projects")
async def remove_projects(
    days: Optional[int] = Query(None, description="Remove projects older than this many days"),
    hours: Optional[int] = Query(None, description="Remove projects older than this many hours"),
    minutes: Optional[int] = Query(None, description="Remove projects older than this many minutes"),
    user_id: Optional[str] = Query(None, description="Remove projects for this user"),
    db: Session = Depends(get_db)
):
    from datetime import timedelta
    age = None
    if days:
        age = timedelta(days=days)
    elif hours:
        age = timedelta(hours=hours)
    elif minutes:
        age = timedelta(minutes=minutes)
    
    removed_projects = remove_old_projects(db, age, user_id)
    
    return {
        "message": f"Removed {len(removed_projects)} projects.",
        "removed_projects": removed_projects
    }
EOF

# Create architect.py
cat << EOF > agentic_platform/agentic_platform/api/architect.py
# [Include the entire code for the architect endpoint from agentic_editor main.py]
EOF

# Create editor.py
cat << EOF > agentic_platform/agentic_platform/api/editor.py
# [Include the entire code for the editor endpoint from agentic_editor main.py]
EOF

# Create cost_summary.py
cat << EOF > agentic_platform/agentic_platform/api/cost_summary.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from ..crud import get_db

router = APIRouter()

@router.get("/cost-summary")
async def get_cost_summary(project_name: Optional[str] = None, user_id: Optional[str] = None, db: Session = Depends(get_db)):
    from ..models import Project
    query = db.query(Project)
    if project_name:
        query = query.filter(Project.name == project_name)
    if user_id:
        query = query.filter(Project.user_id == user_id)
    
    projects = query.all()
    
    summary = {
        "total_cost": sum(project.total_cost for project in projects),
        "projects": [
            {
                "name": project.name,
                "user_id": project.user_id,
                "cost": project.total_cost,
                "last_updated": project.last_updated
            }
            for project in projects
        ]
    }
    
    return summary
EOF

# Create deploy.py (include the full code from agentic_preview main.py)
cat << EOF > agentic_platform/agentic_platform/api/deploy.py
# [Include the entire code for the deploy endpoints from agentic_preview main.py]
EOF

# Install dependencies using poetry
cd agentic_platform
poetry install

echo "Installation complete. Run the application using 'poetry run python -m agentic_platform.main'"
