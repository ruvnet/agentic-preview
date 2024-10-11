import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

def get_project_directory(project_id: str) -> Path:
    return BASE_DIR / 'projects' / str(project_id)

def is_fly_installed():
    return shutil.which("fly") is not None
