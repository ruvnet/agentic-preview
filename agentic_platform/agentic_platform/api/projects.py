# agentic_platform/agentic_platform/api/projects.py
from fastapi import APIRouter, Depends, Query
from ..crud import get_db, cleanup_projects, remove_old_projects
from sqlalchemy.orm import Session
from typing import Optional

router = APIRouter()

@router.get("/")
async def list_projects(db: Session = Depends(get_db)):
    from ..models import Project
    projects = db.query(Project).all()
    return {"projects": [{"name": project.name, "user_id": project.user_id, "created_at": project.created_at, "updated_at": project.updated_at} for project in projects]}

@router.post("/cleanup")
async def cleanup(db: Session = Depends(get_db)):
    removed_projects = cleanup_projects(db)
    return {
        "message": f"Cleanup completed. Removed {len(removed_projects)} projects.",
        "removed_projects": removed_projects
    }

@router.post("/remove_projects")
async def remove_projects(
    days: Optional[int] = Query(None, description="Remove projects older than this many days"),
    hours: Optional[int] = Query(None, description="Remove projects older than this many hours"),
    minutes: Optional[int] = Query(None, description="Remove projects older than this many minutes"),
    user_id: Optional[str] = Query(None, description="Remove projects for this user"),
    db: Session = Depends(get_db)
):
    from datetime import timedelta
    age = None
    if days:
        age = timedelta(days=days)
    elif hours:
        age = timedelta(hours=hours)
    elif minutes:
        age = timedelta(minutes=minutes)
    
    removed_projects = remove_old_projects(db, age, user_id)
    
    return {
        "message": f"Removed {len(removed_projects)} projects.",
        "removed_projects": removed_projects
    }
