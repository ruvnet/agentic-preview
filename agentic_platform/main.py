import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from agentic_platform.editor.main import editor_router
from agentic_platform.preview.main import preview_router

app = FastAPI()

app.include_router(editor_router, prefix="/editor")
app.include_router(preview_router, prefix="/preview")
