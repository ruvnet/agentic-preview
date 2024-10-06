import subprocess
import shlex
import sys
import json
import os
import logging
import asyncio
import time
import shutil
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, validator
from typing import List, Optional

app = FastAPI()

class AiderConfig(BaseModel):
    chat_mode: str = Field("code", example="code")
    edit_format: str = Field("diff", example="diff")
    model: str = Field("gpt-4", example="gpt-4")
    prompt: Optional[str] = Field(None, example="Initial setup")
    files: List[str] = Field(default_factory=list, example=["/test/main.py", "utils.py"])

    @validator('files')
    def validate_files(cls, v):
        for file in v:
            if '..' in file or file.startswith('/'):
                raise ValueError(f"Invalid file path: {file}")
        return v

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
        subprocess.run(
            [sys.executable, "-m", "venv", venv_path],
            check=True,
            stderr=subprocess.PIPE
        )
    except subprocess.CalledProcessError as e:
        error_message = (
            f"Failed to create virtual environment: {e}. "
            f"Command: {e.cmd}, Return code: {e.returncode}, "
            f"Output: {e.output}, Stderr: {e.stderr}"
        )
        logging.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)

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

@app.post("/run-aider")
async def execute_aider(config: AiderConfig):
    repo_path = os.environ.get('REPO_PATH', os.path.join(os.getcwd(), "my_repo"))
    venv_path = os.path.join(repo_path, "venv")

    # Check if the virtual environment exists
    if not os.path.exists(venv_path) or not os.path.exists(os.path.join(venv_path, "bin", "activate")):
        await asyncio.to_thread(create_venv, repo_path, venv_path)

    aider_process = await asyncio.to_thread(run_aider, config, venv_path, repo_path)
    return stream_aider_output(aider_process)

def cleanup_old_environments():
    repo_path = os.environ.get('REPO_PATH', os.path.join(os.getcwd(), "my_repo"))
    venv_path = os.path.join(repo_path, "venv")
    if os.path.exists(venv_path) and (time.time() - os.path.getmtime(venv_path)) > 86400:  # 24 hours
        shutil.rmtree(venv_path)
        logging.info(f"Removed old virtual environment: {venv_path}")

# Don't remove this line
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
