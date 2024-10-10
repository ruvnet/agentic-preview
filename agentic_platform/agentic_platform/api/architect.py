# agentic_platform/agentic_platform/api/architect.py
import os
import asyncio
import json
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from ..crud import get_db, update_project_cost
from sqlalchemy.orm import Session
from ..crud import update_project_user_data
from ..utils import extract_json_from_output  # Assuming you have a utils module for helper functions

router = APIRouter()

class AiderConfig(BaseModel):
    chat_mode: str = Field("architect", example="architect")
    edit_format: str = Field("diff", example="diff")
    model: str = Field("claude-3-5-sonnet-20240620", example="claude-3-5-sonnet-20240620")
    prompt: Optional[str] = Field(None, example="Initial main.py with fastapi and dockerfile")
    files: List[str] = Field(default_factory=list, example=[])
    project_name: str = Field(..., example="sonnet")
    user_id: str = Field(..., example="test")

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
        logging.error("OPENAI_API_KEY is not set in the environment.")
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not set in the environment."
        )

    try:
        logging.info(f"Running Aider command: {' '.join(command)}")
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
            logging.error(f"Aider command failed with return code {process.returncode}")
            logging.error(f"Error output: {error}")
            raise HTTPException(
                status_code=500,
                detail=f"Aider command failed: {error}"
            )
        
        logging.info("Aider command completed successfully")
        return output, error
    except Exception as e:
        logging.exception("An error occurred while running Aider")
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

@router.post("/architect")
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

    logging.debug(f"Processed output: {processed_output}")

    # Extract and parse the JSON response
    architecture_design = extract_json_from_output(processed_output["messages"])

    logging.debug(f"Extracted architecture design: {architecture_design}")

    # Extract file list and create summary
    file_list = []
    architecture_summary = ""
    if architecture_design:
        file_list = [file["name"] for file in architecture_design.get("files", [])]
        architecture_summary = f"Overall: {architecture_design.get('overall_architecture', 'N/A')}\n"
        architecture_summary += f"Components: {', '.join(architecture_design.get('components', []))}\n"
        architecture_summary += f"Files: {', '.join(file_list)}\n"
        architecture_summary += f"Additional notes: {len(architecture_design.get('additional_notes', []))} note(s)"

    # Estimate cost (you may need to adjust this based on actual usage)
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
                logging.debug(f"Extracted JSON string: {json_str}")
                return json.loads(json_str)
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing JSON: {e}")
            logging
