# agentic_platform/agentic_platform/main.py
from fastapi import FastAPI
from .api.api_router import api_router

app = FastAPI(
    title="Agentic Platform API",
    description="API for managing deployments, repositories, projects, and more",
    version="1.0.0"
)

app.include_router(api_router, prefix="/api/v1")

# Redirect root to docs
@app.get("/")
async def redirect_to_docs():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agentic_platform.main:app", host="0.0.0.0", port=5000)
