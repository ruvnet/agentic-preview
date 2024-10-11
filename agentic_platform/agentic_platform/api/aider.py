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

# Remove any existing router.include_router() calls if present

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
