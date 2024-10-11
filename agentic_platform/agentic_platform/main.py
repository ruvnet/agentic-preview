# agentic_platform/agentic_platform/main.py

import os
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s:%(lineno)d %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS_DIR = os.path.join(BASE_DIR, 'projects')

logger.debug(f"Base directory: {BASE_DIR}")
logger.debug(f"Projects directory: {PROJECTS_DIR}")

if os.path.exists(PROJECTS_DIR):
    logger.debug("Contents of projects directory:")
    for item in os.listdir(PROJECTS_DIR):
        logger.debug(f" - {item}")
else:
    logger.debug("Projects directory does not exist")

from fastapi import FastAPI
from .api import aider, deploy, users, projects, architect, editor, cost_summary
from .database import init_db

# Ensure flyctl is in the PATH
os.environ['PATH'] = f"{os.path.expanduser('~')}/.fly/bin:" + os.environ.get('PATH', '')

# Initialize logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s:%(lineno)d %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

# Initialize database
init_db()

app = FastAPI()

# Include routers
app.include_router(aider.router)
app.include_router(deploy.router)
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(architect.router)
app.include_router(editor.router)
app.include_router(cost_summary.router)

# Redirect root to docs
@app.get("/")
async def redirect_to_docs():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agentic_platform.main:app", host="0.0.0.0", port=5000)
from fastapi import FastAPI
from .api.deploy.endpoints import router as deploy_router, tags_metadata

app = FastAPI(
    title="Agentic Platform API",
    description="API for managing deployments, repositories, and projects",
    version="1.0.0",
    openapi_tags=tags_metadata
)

app.include_router(deploy_router, prefix="/api/v1")
