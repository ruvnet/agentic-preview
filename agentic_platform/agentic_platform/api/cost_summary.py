# agentic_platform/agentic_platform/api/cost_summary.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from ..crud import get_db

router = APIRouter()

@router.get("/cost-summary")
async def get_cost_summary(project_name: Optional[str] = None, user_id: Optional[str] = None, db: Session = Depends(get_db)):
    from ..models import Project
    query = db.query(Project)
    if project_name:
        query = query.filter(Project.name == project_name)
    if user_id:
        query = query.filter(Project.user_id == user_id)
    
    projects = query.all()
    
    summary = {
        "total_cost": sum(project.total_cost for project in projects),
        "projects": [
            {
                "name": project.name,
                "user_id": project.user_id,
                "cost": project.total_cost,
                "last_updated": project.last_updated
            }
            for project in projects
        ]
    }
    
    return summary
