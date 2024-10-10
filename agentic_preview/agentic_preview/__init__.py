from contextlib import asynccontextmanager
from fastapi import FastAPI

async def cleanup_resources():
    # Add your cleanup logic here
    pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await cleanup_resources()

app = FastAPI(lifespan=lifespan)

from .routes import deploy, status, logs, apps

app.include_router(apps.router)

# This file marks the directory as a Python package and initializes the FastAPI app.
