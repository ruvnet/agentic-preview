from sqlalchemy.orm import Session
from . import models
from datetime import datetime, timedelta
import os
import shutil

def get_db():
    from .database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def update_project_user_data(project_name: str, user_id: str, repo_url: str, db: Session):
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        user = models.User(user_id=user_id)
        db.add(user)
        db.flush()  # This will assign an id to the user
    
    project = db.query(models.Project).filter(models.Project.name == project_name, models.Project.user_id == user.id).first()
    if not project:
        project = models.Project(name=project_name, user_id=user.id, repo_url=repo_url)
        db.add(project)
    else:
        project.updated_at = datetime.utcnow()
        project.repo_url = repo_url
    
    try:
        db.commit()
    except:
        db.rollback()
        raise

def remove_old_projects(db: Session, age: timedelta = None, user_id: str = None):
    query = db.query(models.Project)
    
    if age:
        cutoff_date = datetime.utcnow() - age
        query = query.filter(models.Project.last_updated < cutoff_date)
    
    if user_id:
        query = query.filter(models.Project.user_id == user_id)
    
    projects_to_remove = query.all()
    
    for project in projects_to_remove:
        project_path = os.path.join("projects", f"{project.name}_{project.user_id}")
        if os.path.exists(project_path):
            shutil.rmtree(project_path)
        db.delete(project)
    
    db.commit()
    
    return [{"name": p.name, "user_id": p.user_id, "last_updated": p.last_updated} for p in projects_to_remove]

def cleanup_projects(db: Session):
    projects_dir = "projects"
    if not os.path.exists(projects_dir):
        return []
    existing_projects = set(os.listdir(projects_dir))
    
    # Get all projects from the database
    db_projects = db.query(models.Project).all()
    
    removed_projects = []
    for project in db_projects:
        project_folder = f"{project.name}_{project.user_id}"
        if project_folder not in existing_projects:
            # Remove the project from the database
            db.delete(project)
            removed_projects.append({"name": project.name, "user_id": project.user_id})
    
    # Commit the changes
    db.commit()
    
    return removed_projects

def update_project_cost(db: Session, project_name: str, user_id: str, cost: float):
    project = db.query(models.Project).filter(models.Project.name == project_name, models.Project.user_id == user_id).first()
    if project:
        project.total_cost += cost
        project.last_updated = datetime.utcnow()
        db.commit()
