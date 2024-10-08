#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Change to the directory where this script is located
cd "$(dirname "$0")"

echo "Creating directory structure..."

# Create the agentic_platform directory and subdirectories
mkdir -p agentic_platform/editor
mkdir -p agentic_platform/preview
mkdir -p agentic_platform/projects

echo "Creating __init__.py files..."

# Create __init__.py files to define packages
touch agentic_platform/__init__.py
touch agentic_platform/editor/__init__.py
touch agentic_platform/preview/__init__.py

echo "Creating agentic_platform/editor/main.py..."

# Write the agentic_editor main.py content to agentic_platform/editor/main.py
cat > agentic_platform/editor/main.py << 'EOF'
import subprocess
import json
import os
import asyncio
import logging
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Float, and_, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
import shutil

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    total_cost = Column(Float, default=0.0)
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
        if 'total_cost' not in existing_columns:
            conn.execute(text("ALTER TABLE projects ADD COLUMN total_cost FLOAT DEFAULT 0.0"))
        
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
    file_list: Optional[List[str]] = Field(None, example=["auth_service.py", "api_gateway.py", "microservice_example.py"])

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

def update_project_cost(db: Session, project_name: str, user_id: str, cost: float):
    project = db.query(Project).filter(Project.name == project_name, Project.user_id == user_id).first()
    if project:
        project.total_cost += cost
        project.last_updated = datetime.utcnow()
        db.commit()

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
    current_message = []

    for line in output_lines:
        if line.startswith("pip "):
            processed_output["commands"].append(line)
        else:
            current_message.append(line)

    if current_message:
        processed_output["messages"].append("\n".join(current_message))

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

@app.post("/architect")
async def architect_mode(project_name: str, user_id: str, requirements: str, db: Session = Depends(get_db)):
    project_path = os.path.join("projects", f"{project_name}_{user_id}")
    os.makedirs(project_path, exist_ok=True)

    prompt = f"""
    Act as a software architect. Design a high-level system architecture based on these requirements: {requirements}
    
    Please provide your response in the following JSON format:
    {{
        "overall_architecture": "Brief description of the overall architecture",
        "components": [
            "Component 1 description",
            "Component 2 description",
            ...
        ],
        "files": [
            {{
                "name": "filename1.py",
                "description": "Brief description of the file's purpose"
            }},
            {{
                "name": "filename2.py",
                "description": "Brief description of the file's purpose"
            }},
            ...
        ],
        "additional_notes": [
            "Note 1",
            "Note 2",
            ...
        ]
    }}

    Ensure that your response is a valid JSON object that can be parsed.
    """

    config = AiderConfig(
        chat_mode="architect",
        edit_format="diff",
        model="claude-3-5-sonnet-20240620",
        prompt=prompt,
        files=[],
        project_name=project_name,
        user_id=user_id
    )

    output, error = await asyncio.to_thread(run_aider, config, project_path)
    processed_output = process_aider_output(output.split('\n'))

    architecture_design = extract_json_from_output(processed_output["messages"])

    file_list = []
    architecture_summary = ""
    if architecture_design:
        file_list = [file["name"] for file in architecture_design.get("files", [])]
        architecture_summary = f"Overall: {architecture_design.get('overall_architecture', 'N/A')}\n"
        architecture_summary += f"Components: {', '.join(architecture_design.get('components', []))}\n"
        architecture_summary += f"Files: {', '.join(file_list)}\n"
        architecture_summary += f"Additional notes: {len(architecture_design.get('additional_notes', []))} note(s)"

    estimated_cost = len(requirements) * 0.00001  # Example cost calculation
    update_project_cost(db, project_name, user_id, estimated_cost)

    return {
        "project_name": project_name,
        "user_id": user_id,
        "architecture_design": architecture_design,
        "file_list": file_list,
        "architecture_summary": architecture_summary,
        "raw_output": processed_output["messages"],
        "estimated_cost": estimated_cost
    }

import re

def extract_json_from_output(messages):
    for message in messages:
        try:
            # Use regex to find JSON-like structure
            json_match = re.search(r'\{.*\}', message, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                logger.debug(f"Extracted JSON string: {json_str}")
                return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON: {e}")
            logger.debug(f"Problematic message: {message}")
    logger.warning("No valid JSON found in the output")
    return None  # Return None if no valid JSON is found

@app.post("/editor")
async def editor_mode(project_name: str, user_id: str, file_path: str, edit_instruction: str, db: Session = Depends(get_db)):
    project_path = os.path.join("projects", f"{project_name}_{user_id}")
    full_file_path = os.path.join(project_path, file_path)

    if not os.path.exists(full_file_path):
        raise HTTPException(status_code=404, detail="File not found")

    config = AiderConfig(
        chat_mode="edit",
        edit_format="diff",
        model="claude-3-5-sonnet-20240620",
        prompt=f"Edit the file {file_path} according to these instructions: {edit_instruction}",
        files=[file_path],
        project_name=project_name,
        user_id=user_id
    )

    output, error = await asyncio.to_thread(run_aider, config, project_path)
    processed_output = process_aider_output(output.split('\n'))

    estimated_cost = len(edit_instruction) * 0.00002  # Example cost calculation
    update_project_cost(db, project_name, user_id, estimated_cost)

    return {
        "project_name": project_name,
        "user_id": user_id,
        "file_path": file_path,
        "changes": processed_output,
        "estimated_cost": estimated_cost
    }

@app.get("/cost-summary")
async def get_cost_summary(project_name: Optional[str] = None, user_id: Optional[str] = None, db: Session = Depends(get_db)):
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

# Don't remove this line
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
EOF

echo "Creating agentic_platform/preview/main.py..."

# Write the actual content to agentic_platform/preview/main.py
cat > agentic_platform/preview/main.py << 'EOF'
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
EOF

echo "Creating agentic_platform/main.py..."

# Write the combined main.py to agentic_platform/main.py
cat > agentic_platform/main.py << 'EOF'
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from agentic_platform.editor.main import app as editor_app
from agentic_platform.preview.main import app as preview_app

app = FastAPI()

# Mount the editor and preview apps
app.mount("/editor", editor_app)
app.mount("/preview", preview_app)
EOF

echo "Creating agentic_platform/README.md..."

# Write the actual content to agentic_platform/README.md
cat > agentic_platform/README.md << 'EOF'
# Agentic Platform

Agentic Platform is a unified FastAPI backend service that combines the functionalities of Agentic Preview and Agentic Editor.

## Features

- Deploy GitHub repositories to Fly.io
- Asynchronous operations for improved performance
- Configurable runtime limit for deployments
- Cleans up resources after usage
- RESTful API for executing Aider commands
- Virtual Environment Management
- Configurable Execution
- Supports custom deployment arguments
- Automatically generates `fly.toml` configuration if not present
- Provides deployment status and logs
- Simple API endpoints for deploying and managing applications

## Installation

This project uses Poetry for dependency management. Follow these steps to set up the project:

1. Ensure you have Python 3.8 or higher installed on your system.

2. Install Poetry if you haven't already:
   ```
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. Clone the repository:
   ```
   git clone <repository-url>
   cd agentic_platform
   ```

4. Install the project dependencies:
   ```
   poetry install
   ```

## Running the Application

To run the application, follow these steps:

1. Activate the Poetry virtual environment:
   ```
   poetry shell
   ```

2. Start the application:
   ```
   poetry run uvicorn main:app --host 0.0.0.0 --port 8000
   ```

3. The application should now be running. Check the console output for the local address and port where the service is available.

## Usage

### Deploying an Application

To deploy an application, send a POST request to the `/preview/deploy` endpoint with the following JSON body:

```json
{
  "repo": "username/repository",
  "branch": "main",
  "args": ["--build-arg", "ENV=production"]
}
```

### Running Aider

To execute the Aider tool, send a POST request to the `/editor/run-aider` endpoint with the appropriate JSON payload.

#### Request Body

- `chat_mode`: Mode for Aider chat (default: "code").
- `edit_format`: Format for edits (default: "diff").
- `model`: Model to use (default: "gpt-4").
- `prompt`: Optional prompt message.
- `files`: List of files to include.

#### Example Request

```json
{
  "chat_mode": "code",
  "edit_format": "diff",
  "model": "gpt-4",
  "prompt": "Initial setup",
  "files": ["main.py", "utils.py"]
}
```

#### Example Response

The response will stream the output from the Aider tool, providing real-time feedback on the execution process.

### Checking Deployment Status

To check the status of a deployment, send a GET request to the `/status/{app_name}` endpoint, where `{app_name}` is the name of the deployed application.

### Streaming Logs

To stream logs for a deployed application, send a GET request to the `/logs/{app_name}` endpoint, where `{app_name}` is the name of the deployed application.

## License

MIT License
EOF

echo "Creating agentic_platform/pyproject.toml..."

# Write the pyproject.toml file for Poetry configuration
cat > agentic_platform/pyproject.toml << 'EOF'
[tool.poetry]
name = "agentic_platform"
version = "0.1.0"
description = "Agentic Platform is a unified FastAPI backend service."
authors = ["Your Name <you@example.com>"]
license = "MIT"
readme = "README.md"
packages = [{include = "agentic_platform"}]

[tool.poetry.dependencies]
python = "^3.8"
fastapi = "^0.70.0"
uvicorn = "^0.15.0"

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
EOF

echo "Generating agentic_platform/requirements.txt..."

# Generate requirements.txt from Poetry
cd agentic_platform
poetry export -f requirements.txt --output requirements.txt --without-hashes

echo "Installation script completed successfully."
echo "You can now navigate to the 'agentic_platform' directory and start the application."
