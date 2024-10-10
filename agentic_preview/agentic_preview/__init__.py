from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await cleanup_resources()

app = FastAPI(lifespan=lifespan)

from .routes import deploy, status, logs

# This file marks the directory as a Python package and initializes the FastAPI app.
