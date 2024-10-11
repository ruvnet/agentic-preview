from pydantic import BaseModel, Field
from typing import List, Optional

class DeployRequest(BaseModel):
    repo: str
    branch: str
    args: Optional[List[str]] = []
    memory: Optional[int] = 2048
    app_name: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "repo": "ruvnet/agentic_preview",
                "branch": "main",
                "args": ["--build-arg", "ENV=production"],
                "memory": 2048,
                "app_name": "my-app"
            }
        }

class CloneRequest(BaseModel):
    repo_url: str
    user_id: str

class UpdateProjectRequest(BaseModel):
    name: Optional[str] = None
    repo_url: Optional[str] = None

class ExploreRequest(BaseModel):
    repo_id: str
    action: str
    path: Optional[str] = ""
    content: Optional[str] = ""
