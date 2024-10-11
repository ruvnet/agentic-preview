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
from pydantic import BaseModel, Field
from typing import List, Optional

class DeployRequest(BaseModel):
    repo: str = Field(..., description="GitHub repository in the format 'username/repo'")
    branch: str = Field(..., description="Git branch to deploy")
    args: Optional[List[str]] = Field(default=[], description="Additional arguments for deployment")
    memory: Optional[int] = Field(default=2048, description="Memory allocation in MB")
    app_name: Optional[str] = Field(default=None, description="Optional custom name for the application")

class CloneRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL")
    user_id: str = Field(..., description="User ID associated with the project")

class UpdateProjectRequest(BaseModel):
    name: Optional[str] = Field(None, description="New name for the project")
    repo_url: Optional[str] = Field(None, description="New repository URL for the project")

class ExploreRequest(BaseModel):
    repo_id: str = Field(..., description="ID of the repository to explore")
    path: Optional[str] = Field(default="", description="Path within the repository to explore")
    action: str = Field(..., description="Action to perform: explore, modify, create, remove, or create_dockerfile")
    content: Optional[str] = Field(default=None, description="Content for file creation or modification")
