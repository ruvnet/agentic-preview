from fastapi import FastAPI
from .editor.main import editor_router
from .preview.main import preview_router

app = FastAPI()

app.include_router(editor_router, prefix="/editor")
app.include_router(preview_router, prefix="/preview")
