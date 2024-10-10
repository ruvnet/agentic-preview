# agentic_platform/agentic_platform/api/users.py
from fastapi import APIRouter, Depends
from ..crud import get_db
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("/users")
async def list_users(db: Session = Depends(get_db)):
    from ..models import User
    users = db.query(User).all()
    return {"users": {user.user_id: [{"name": project.name, "created_at": project.created_at, "last_updated": project.last_updated} for project in user.projects] for user in users}}
