import subprocess
import json
import os
import asyncio
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, and_, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
import shutil

# Database setup
DATABASE_URL = "sqlite:///./aider_projects.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

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
    user = relationship("User", back_populates="projects")

def init_db():
    Base.metadata.create_all(bind=engine)
    
    # Add new columns if they don't exist
    with engine.connect() as conn:
        inspector = inspect(engine)
        existing_columns = [col['name'] for col in inspector.get_columns('projects')]
        if 'created_at' not in existing_columns:
            conn.execute(text("ALTER TABLE projects ADD COLUMN created_at DATETIME"))
        if 'last_updated' not in existing_columns:
            conn.execute(text("ALTER TABLE projects ADD COLUMN last_updated DATETIME"))
    
init_db()

app = FastAPI()

class AiderConfig(BaseModel):
    chat_mode: str = Field("code", example="code")
    edit_format: str = Field("diff", example="diff")
    model: str = Field("claude-3-5-sonnet-20240620", example="claude-3-5-sonnet-20240620")
    prompt: Optional[str] = Field(None, example="Initial main.py with fastapi and dockerfile")
    files: List[str] = Field(default_factory=list, example=["main.py", "utils.py"])
    project_name: str = Field(..., example="sonnet")
    user_id: str = Field(..., example="test")

    @validator('files')
    def validate_files(cls, v):
        for file in v:
            if '..' in file or file.startswith('/'):
                raise ValueError(f"Invalid file path: {file}")
        return v

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def update_project_user_data(project_name: str, user_id: str, db: Session):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        user = User(user_id=user_id)
        db.add(user)
    
    project = db.query(Project).filter(Project.name == project_name, Project.user_id == user_id).first()
    if not project:
        project = Project(name=project_name, user_id=user_id)
        db.add(project)
    else:
        project.last_updated = datetime.utcnow()
    
    try:
        db.commit()
    except IntegrityError:
        db.rollback()

def remove_old_projects(db: Session, age: Optional[timedelta] = None, user_id: Optional[str] = None):
    query = db.query(Project)
    
    if age:
        cutoff_date = datetime.utcnow() - age
        query = query.filter(Project.last_updated < cutoff_date)
    
    if user_id:
        query = query.filter(Project.user_id == user_id)
    
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
    existing_projects = set(os.listdir(projects_dir))
    
    # Get all projects from the database
    db_projects = db.query(Project).all()
    
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
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not set in the environment."
        )

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        cwd=project_path,
        env=env
    )
    return process

def stream_aider_output(process):
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            yield output.strip()

    rc = process.poll()
    if rc != 0:
        stderr = process.stderr.read()
        yield f"Aider process exited with code {rc}. Stderr: {stderr.strip()}"

def process_aider_output(output_lines):
    processed_output = {
        "summary": [],
        "file_changes": {},
        "commands": [],
        "messages": []
    }
    current_file = None

    for line in output_lines:
        if line.startswith("Applied edit to "):
            file = line.split("Applied edit to ")[-1]
            processed_output["summary"].append(f"Modified file: {file}")
            current_file = file
            processed_output["file_changes"][current_file] = []
        elif line.startswith(("+++", "---")) and current_file:
            processed_output["file_changes"][current_file].append(line)
        elif line.startswith(("docker ", "pip ", "python ")):
            processed_output["commands"].append(line)
        else:
            processed_output["messages"].append(line)

    return processed_output

@app.get("/")
async def redirect_to_docs():
    return RedirectResponse(url="/docs")

@app.post("/run-aider")
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

    aider_process = await asyncio.to_thread(run_aider, config, project_path)
    
    # Collect and process the output
    output_lines = []
    for line in stream_aider_output(aider_process):
        output_lines.append(line)

    processed_output = process_aider_output(output_lines)

    return {
        "project_name": config.project_name,
        "user_id": config.user_id,
        "aider_output": processed_output
    }

@app.get("/projects")
async def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).all()
    return {"projects": [{"name": project.name, "user_id": project.user_id, "created_at": project.created_at, "last_updated": project.last_updated} for project in projects]}

@app.get("/users")
async def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return {"users": {user.user_id: [{"name": project.name, "created_at": project.created_at, "last_updated": project.last_updated} for project in user.projects] for user in users}}

@app.post("/cleanup")
async def cleanup(db: Session = Depends(get_db)):
    removed_projects = cleanup_projects(db)
    return {
        "message": f"Cleanup completed. Removed {len(removed_projects)} projects.",
        "removed_projects": removed_projects
    }

@app.post("/remove_projects")
async def remove_projects(
    days: Optional[int] = Query(None, description="Remove projects older than this many days"),
    hours: Optional[int] = Query(None, description="Remove projects older than this many hours"),
    minutes: Optional[int] = Query(None, description="Remove projects older than this many minutes"),
    user_id: Optional[str] = Query(None, description="Remove projects for this user"),
    db: Session = Depends(get_db)
):
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

# Don't remove this line
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
