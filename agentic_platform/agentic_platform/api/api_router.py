from fastapi import APIRouter
from .deploy.endpoints import router as deploy_router
from .aider import router as aider_router, code_bot_router
from .architect import router as architect_router
from .cost_summary import router as cost_summary_router
from .projects import router as projects_router
from .user import router as user_router

api_router = APIRouter()

api_router.include_router(deploy_router, prefix="/deploy", tags=["Deployment"])
api_router.include_router(aider_router, prefix="/aider", tags=["Aider"])
api_router.include_router(code_bot_router, prefix="/aider/code-bot", tags=["Code Bot Capabilities"])
api_router.include_router(architect_router, prefix="/architect", tags=["Architect"])
api_router.include_router(cost_summary_router, prefix="/cost", tags=["Cost Summary"])
api_router.include_router(projects_router, prefix="/projects", tags=["Projects"])
api_router.include_router(user_router, prefix="/user", tags=["User"])
