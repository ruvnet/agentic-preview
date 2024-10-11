import os
import subprocess
import asyncio
import logging
import tempfile
from fastapi import APIRouter, HTTPException, Depends, Body, File, UploadFile
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from ..crud import get_db, update_project_user_data, update_project_cost
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter()
code_bot_router = APIRouter()

def read_template(template_name):
    template_path = os.path.join("templates", template_name)
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template file not found: {template_path}")
    with open(template_path, "r") as file:
        return file.read()

class AiderConfig(BaseModel):
    chat_mode: str = Field("code", example="code")
    edit_format: str = Field("diff", example="diff")
    model: str = Field("claude-3-5-sonnet-20240620", example="claude-3-5-sonnet-20240620")
    prompt: Optional[str] = Field(None, example="Initial main.py with fastapi and dockerfile")
    files: List[str] = Field(default_factory=list, example=["main.py", "utils.py"])
    project_name: str = Field(..., example="sonnet")
    user_id: str = Field(..., example="test")
    file_list: Optional[List[str]] = Field(None, example=["auth_service.py", "api_gateway.py", "microservice_example.py"])
    message_file: Optional[str] = Field(None, example="/path/to/message_file.txt")

    @validator('files')
    def validate_files(cls, v):
        for file in v:
            if '..' in file or file.startswith('/'):
                raise ValueError(f"Invalid file path: {file}")
        return v

class SPARCConfig(BaseModel):
    project_name: str
    user_id: str
    template: str
    context: Dict[str, Any] = Field(default_factory=dict)

class ArchitectConfig(BaseModel):
    project_name: str
    user_id: str
    requirements: str

class CodeReviewConfig(BaseModel):
    project_name: str
    user_id: str
    files: List[str]

class BugFixConfig(BaseModel):
    project_name: str
    user_id: str
    bug_description: str
    files: List[str]

class FrameworkConfig(BaseModel):
    project_name: str
    user_id: str
    framework: str
    task: str
    details: str

class ApplicationConfig(BaseModel):
    project_name: str
    user_id: str
    app_type: str
    requirements: str

class LanguageConfig(BaseModel):
    project_name: str
    user_id: str
    language: str
    task: str
    files: List[str]

class CodeManagementConfig(BaseModel):
    project_name: str
    user_id: str
    task: str
    files: List[str]

def run_aider(config: AiderConfig, project_path: str):
    command = [
        "aider",
        "--chat-mode", config.chat_mode,
        "--edit-format", config.edit_format,
        "--model", config.model,
        "--yes",  # Non-interactive mode
        "--no-git"  # Run without git integration
    ]

    if config.message_file:
        command.extend(["--message-file", config.message_file])
    elif config.prompt:
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
    update_project_user_data(config.project_name, config.user_id, None, db)  # Pass None for repo_url and db

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

@code_bot_router.post("/sparc")
async def sparc_task(config: SPARCConfig, db: Session = Depends(get_db)):
    project_path = os.path.join("projects", f"{config.project_name}_{config.user_id}")
    os.makedirs(project_path, exist_ok=True)

    try:
        template_content = read_template(f"{config.template}.md")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Template '{config.template}' not found")

    # Replace placeholders in the template with context values
    for key, value in config.context.items():
        template_content = template_content.replace(f"{{{{ {key} }}}}", str(value))

    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
        temp_file.write(template_content)
        temp_file_path = temp_file.name

    aider_config = AiderConfig(
        chat_mode="sparc",
        edit_format="diff",
        model="claude-3-5-sonnet-20240620",
        prompt=None,
        files=[],
        project_name=config.project_name,
        user_id=config.user_id,
        message_file=temp_file_path
    )

    output, error = await asyncio.to_thread(run_aider, aider_config, project_path)
    processed_output = process_aider_output(output.split('\n'))

    os.unlink(temp_file_path)  # Remove the temporary file

    estimated_cost = len(template_content) * 0.00001  # Example cost calculation
    update_project_cost(db, config.project_name, config.user_id, estimated_cost)

    return {
        "project_name": config.project_name,
        "user_id": config.user_id,
        "sparc_output": processed_output,
        "estimated_cost": estimated_cost
    }

@code_bot_router.post("/architect")
async def architect_mode(config: ArchitectConfig, db: Session = Depends(get_db)):
    sparc_config = SPARCConfig(
        project_name=config.project_name,
        user_id=config.user_id,
        template="architect",
        context={
            "requirements": config.requirements
        }
    )
    return await sparc_task(sparc_config, db)

@code_bot_router.post("/code-review")
async def code_review(config: CodeReviewConfig, db: Session = Depends(get_db)):
    sparc_config = SPARCConfig(
        project_name=config.project_name,
        user_id=config.user_id,
        template="code_review",
        context={
            "files": ",".join(config.files)
        }
    )
    return await sparc_task(sparc_config, db)

@code_bot_router.post("/bug-fix")
async def bug_fix(config: BugFixConfig, db: Session = Depends(get_db)):
    sparc_config = SPARCConfig(
        project_name=config.project_name,
        user_id=config.user_id,
        template="bug_fix",
        context={
            "bug_description": config.bug_description,
            "files": ",".join(config.files)
        }
    )
    return await sparc_task(sparc_config, db)

@code_bot_router.post("/framework")
async def framework_task(config: FrameworkConfig, db: Session = Depends(get_db)):
    sparc_config = SPARCConfig(
        project_name=config.project_name,
        user_id=config.user_id,
        template="framework",
        context={
            "framework": config.framework,
            "task": config.task,
            "details": config.details
        }
    )
    return await sparc_task(sparc_config, db)

@code_bot_router.post("/application")
async def application_task(config: ApplicationConfig, db: Session = Depends(get_db)):
    sparc_config = SPARCConfig(
        project_name=config.project_name,
        user_id=config.user_id,
        template="application",
        context={
            "app_type": config.app_type,
            "requirements": config.requirements
        }
    )
    return await sparc_task(sparc_config, db)

@code_bot_router.post("/language")
async def language_task(config: LanguageConfig, db: Session = Depends(get_db)):
    sparc_config = SPARCConfig(
        project_name=config.project_name,
        user_id=config.user_id,
        template="language",
        context={
            "language": config.language,
            "task": config.task,
            "files": ",".join(config.files)
        }
    )
    return await sparc_task(sparc_config, db)

@code_bot_router.post("/code-management")
async def code_management_task(config: CodeManagementConfig, db: Session = Depends(get_db)):
    sparc_config = SPARCConfig(
        project_name=config.project_name,
        user_id=config.user_id,
        template="code_management",
        context={
            "task": config.task,
            "files": ",".join(config.files)
        }
    )
    return await sparc_task(sparc_config, db)

# Include the code_bot_router in the main router
router.include_router(code_bot_router, prefix="/code-bot", tags=["Code Bot Capabilities"])
