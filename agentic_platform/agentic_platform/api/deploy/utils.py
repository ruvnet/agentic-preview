import os
import shutil
import asyncio
from pathlib import Path
from typing import List, Optional
import logging

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

def get_project_directory(project_id: str) -> Path:
    return BASE_DIR / 'projects' / str(project_id)

def is_fly_installed():
    return shutil.which("fly") is not None

async def execute_command(cmd: List[str], cwd: Optional[str] = None):
    logger = logging.getLogger(__name__)
    logger.debug(f"Executing command: {' '.join(cmd)} in directory: {cwd}")
    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    logger.debug(f"Command stdout: {stdout.decode()}")
    logger.debug(f"Command stderr: {stderr.decode()}")

    if process.returncode != 0:
        error_message = f"Command {' '.join(cmd)} failed with error code {process.returncode}\nstdout:\n{stdout.decode()}\nstderr:\n{stderr.decode()}"
        logger.error(error_message)
        raise Exception(error_message)

    return stdout.decode()
