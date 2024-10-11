import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

def get_project_directory(project_id: str) -> Path:
    return BASE_DIR / 'projects' / str(project_id)

def is_fly_installed():
    return shutil.which("fly") is not None
import os
import shutil
from pathlib import Path

def get_project_directory(repo_id: str) -> Path:
    return Path(f"projects/{repo_id}")

def is_fly_installed() -> bool:
    return shutil.which("fly") is not None

async def execute_command(cmd, cwd=None):
    import asyncio
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise Exception(f"Command failed: {' '.join(cmd)}\nError: {stderr.decode()}")
    return stdout.decode()
