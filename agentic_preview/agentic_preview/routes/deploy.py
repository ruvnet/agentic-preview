from fastapi import APIRouter, Body
from pydantic import BaseModel, Field
from typing import List, Optional

router = APIRouter()

class DeploymentRequest(BaseModel):
    repo: str = Field(..., description="GitHub repository in the format 'username/repo'")
    branch: str = Field(..., description="Git branch to deploy")
    args: Optional[List[str]] = Field(default=[], description="Additional arguments for deployment")
    memory: Optional[int] = Field(default=2048, description="Memory allocation in MB")
    app_name: Optional[str] = Field(default=None, description="Optional custom name for the application")

    class Config:
        schema_extra = {
            "example": {
                "repo": "ruvnet/agentic_preview",
                "branch": "main",
                "args": ["--build-arg", "ENV=production"],
                "memory": 2048,
                "app_name": "my-app"
            }
        }

@router.post("/deploy", 
             summary="Deploy an application",
             description="Clone a GitHub repository and deploy it to the platform")
async def deploy_app(deployment: DeploymentRequest = Body(...)):
    # Your existing deployment logic here
    return {"message": "Deployment request received", "deployment": deployment}

@router.get("/status/{app_name}", 
            summary="Check deployment status",
            description="Get the current status of a deployed application")
async def check_status(app_name: str):
    # Implement status checking logic here
    return {"status": "pending", "app_name": app_name}

@router.get("/logs/{app_name}", 
            summary="Stream application logs",
            description="Stream real-time logs from a deployed application")
async def stream_logs(app_name: str):
    # Implement log streaming logic here
    return {"message": f"Streaming logs for {app_name}"}

# Add other route handlers as needed
