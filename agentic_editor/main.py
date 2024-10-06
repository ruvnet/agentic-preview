import subprocess
import shlex
import sys
import json
import os
import sqlite3
import venv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from typing import List, Optional

# Set up SQLite database
DATABASE_NAME = "projects.db"

def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            user_id TEXT,
            path TEXT,
            venv_path TEXT,
            UNIQUE(name, user_id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()  # Call this at the start of your application

app = FastAPI()

class AiderConfig(BaseModel):
    chat_mode: str = Field("code", example="code")
    edit_format: str = Field("diff", example="diff")
    model: str = Field("gpt-4", example="gpt-4")
    prompt: Optional[str] = Field(None, example="Initial setup")
    files: List[str] = Field(default_factory=list, example=["/test/main.py", "utils.py"])
    user_id: str = Field(..., example="user123")
    project_name: Optional[str] = Field(None, example="my_project")

class ProjectCreate(BaseModel):
    name: str
    user_id: str

def create_venv(repo_path, venv_path):
    # Remove existing directories if they exist
    if os.path.exists(repo_path):
        subprocess.run(["rm", "-rf", repo_path], check=True)
    if os.path.exists(venv_path):
        subprocess.run(["rm", "-rf", venv_path], check=True)

    # Create the necessary directories
    os.makedirs(repo_path, exist_ok=True)
    os.makedirs(venv_path, exist_ok=True)
    try:
        venv.create(venv_path, with_pip=True)
    except Exception as e:
        error_message = f"Failed to create virtual environment: {e}"
        raise HTTPException(status_code=500, detail=error_message)

def create_project(project: ProjectCreate):
    projects_dir = "projects"
    project_path = os.path.join(projects_dir, project.user_id, project.name)
    venv_path = os.path.join(project_path, "venv")

    if not os.path.exists(project_path):
        os.makedirs(project_path, exist_ok=True)
        venv.create(venv_path, with_pip=True)
        
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO projects (name, user_id, path, venv_path) VALUES (?, ?, ?, ?)",
                           (project.name, project.user_id, project_path, venv_path))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            raise HTTPException(status_code=400, detail=f"Project '{project.name}' already exists for this user")
        finally:
            conn.close()
        
        return {"message": f"Project '{project.name}' created successfully for user {project.user_id}"}
    else:
        raise HTTPException(status_code=400, detail=f"Project '{project.name}' already exists for this user")

def get_project(project_name: str, user_id: str):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects WHERE name = ? AND user_id = ?", (project_name, user_id))
    project = cursor.fetchone()
    conn.close()
    if project:
        return {"id": project[0], "name": project[1], "user_id": project[2], "path": project[3], "venv_path": project[4]}
    return None

def run_aider(config: AiderConfig, venv_path: str, repo_path: str):
    venv_bin_path = os.path.join(venv_path, "bin")
    venv_python = os.path.join(venv_bin_path, "python")
    venv_pip = os.path.join(venv_bin_path, "pip")

    # Install aider in the virtual environment
    try:
        subprocess.run(
            [venv_pip, "install", "aider-chat"],
            check=True,
            stderr=subprocess.PIPE
        )
    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to install aider-chat: {e}"
        )

    command = [
        venv_python, "-m", "aider",
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

    env['OPENAI_API_KEY'] = str(api_key)

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        cwd=repo_path,
        env=env
    )
    return process

def stream_aider_output(process):
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            yield json.dumps({
                "type": "streamContent",
                "content": output.strip()
            }) + "\n"

    rc = process.poll()
    if rc != 0:
        stderr = process.stderr.read()
        yield json.dumps({
            "type": "error",
            "content": f"Aider process exited with code {rc}. Stderr: {stderr.strip()}"
        }) + "\n"

@app.get("/")
async def redirect_to_docs():
    return RedirectResponse(url="/docs")

@app.post("/projects")
async def create_new_project(project: ProjectCreate):
    return create_project(project)

@app.get("/projects/{user_id}")
async def list_projects(user_id: str):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM projects WHERE user_id = ?", (user_id,))
    projects = [row[0] for row in cursor.fetchall()]
    conn.close()
    return {"projects": projects}

@app.post("/run-aider")
async def execute_aider(config: AiderConfig):
    if config.project_name:
        project = get_project(config.project_name, config.user_id)
        if not project:
            raise HTTPException(status_code=400, detail=f"Project '{config.project_name}' does not exist for user {config.user_id}")
        repo_path = project["path"]
        venv_path = project["venv_path"]
    else:
        repo_path = os.path.join(os.getcwd(), "my_repo", config.user_id)
        venv_path = os.path.join(repo_path, "venv")

    # Check if the virtual environment exists
    if not os.path.exists(venv_path) or not os.path.exists(os.path.join(venv_path, "bin", "activate")):
        create_venv(repo_path, venv_path)

    aider_process = run_aider(config, venv_path, repo_path)
    return stream_aider_output(aider_process)

# Don't remove this line
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
