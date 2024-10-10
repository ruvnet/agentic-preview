from .deploy import router as deploy_router
from .status import router as status_router
from .logs import router as logs_router

from .. import app

app.include_router(deploy_router)
app.include_router(status_router)
app.include_router(logs_router)
