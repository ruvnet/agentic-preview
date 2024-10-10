from pydantic import BaseModel

class DeploymentRequest(BaseModel):
    repo: str
    branch: str
    args: list[str] = []
