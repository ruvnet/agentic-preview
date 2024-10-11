from fastapi import APIRouter, HTTPException, Body, Query, Depends, status
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from .models import DeployRequest, CloneRequest, UpdateProjectRequest, ExploreRequest
from .utils import execute_command
from .services import (
    deploy_app, stop_instance, explore_directory, modify_file,
    create_file, remove_file, create_dockerfile, stop_app, stream_aider_output
)
from .utils import get_project_directory, is_fly_installed
from ...crud import get_db
from ...models import Project
import logging
import json
import traceback
import asyncio
from datetime import datetime
import uuid
import os
import shutil

router = APIRouter()
logger = logging.getLogger(__name__)

deployments = {}
cloned_repos = {}

@router.post("/deploy", response_model=Dict[str, str])
async def deploy(deploy_request: DeployRequest = Body(...)):
    app_name: Optional[str] = None
    repo_dir: Optional[str] = None
    try:
        repo = deploy_request.repo
        branch = deploy_request.branch
        args = deploy_request.args or []
        memory = deploy_request.memory or 2048

        logger.info(f"Deploying repository: {repo}, branch: {branch}, args: {args}, memory: {memory}MB")

        # Clone the repository
        repo_name = repo.split('/')[-1]
        timestamp = int(datetime.utcnow().timestamp())
        unique_id = uuid.uuid4().hex
        repo_dir = f"/tmp/{repo_name}-{unique_id}"
        clone_url = f"https://github.com/{repo}.git"

        # Fetch branch information to verify branch existence
        branches_output = await execute_command(['git', 'ls-remote', '--heads', clone_url])
        logger.debug(f"Branches output: {branches_output}")
        if f'refs/heads/{branch}' not in branches_output:
            if 'refs/heads/main' in branches_output:
                logger.warning(f"Branch '{branch}' not found. Defaulting to 'main'.")
                branch = 'main'
            elif 'refs/heads/master' in branches_output:
                logger.warning(f"Branch '{branch}' not found. Defaulting to 'master'.")
                branch = 'master'
            else:
                logger.error(f"Branch '{branch}' not found in repository '{repo}'.")
                raise HTTPException(status_code=400, detail=f"Branch '{branch}' not found in repository '{repo}'.")

        # Clone the repository
        await execute_command(['git', 'clone', '-b', branch, clone_url, repo_dir])

        # Check if Dockerfile exists; if not, return an error
        dockerfile_path = os.path.join(repo_dir, 'Dockerfile')
        if not os.path.exists(dockerfile_path):
            error_msg = f"Dockerfile not found in repository '{repo}'. A Dockerfile is required for deployment."
            logger.error(error_msg)
            # Clean up the cloned repository
            shutil.rmtree(repo_dir, ignore_errors=True)
            logger.info(f"Cleaned up repository directory: {repo_dir}")
            raise HTTPException(status_code=400, detail=error_msg)

        # Generate a unique app name
        app_name = f"preview-{repo_name.lower()}-{branch.lower() if branch else 'default'}-{timestamp}"
        logger.info(f"Generated app name: {app_name}")

        # Start the deployment in the background
        deployment_task = asyncio.create_task(deploy_app(repo, branch, args, app_name, repo_dir, memory))

        # Store the deployment status
        deployments[app_name] = {
            "status": "Deploying",
            "preview_url": None,
            "message": "Deployment started.",
            "timestamp": datetime.utcnow().isoformat()
        }

        return {
            "app_name": app_name,
            "message": "Deployment started.",
            "status_url": f"/status/{app_name}"
        }

    except HTTPException as http_exc:
        logger.error(f"HTTP exception occurred: {http_exc.detail}")
        # Clean up in case of HTTPException
        if repo_dir and os.path.exists(repo_dir):
            shutil.rmtree(repo_dir, ignore_errors=True)
            logger.info(f"Cleaned up repository directory: {repo_dir}")
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error occurred: {e}")
        # Clean up in case of general Exception
        if repo_dir and os.path.exists(repo_dir):
            shutil.rmtree(repo_dir, ignore_errors=True)
            logger.info(f"Cleaned up repository directory: {repo_dir}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{app_name}", response_model=Dict[str, Any])
async def check_status(app_name: str):
    try:
        logger.info(f"Checking status for app: {app_name}")
        if app_name in deployments:
            return deployments[app_name]
        else:
            logger.warning(f"No deployment found for app: {app_name}")
            raise HTTPException(status_code=404, detail=f"No deployment found for app: {app_name}")
    except Exception as e:
        logger.error(f"Error checking app status: {e}")
        raise HTTPException(status_code=500, detail=f"Error checking app status: {str(e)}")

@router.get("/logs/{app_name}", response_class=StreamingResponse)
async def stream_logs(app_name: str):
    if app_name not in deployments:
        logger.warning(f"No deployment found for app: {app_name}")
        raise HTTPException(status_code=404, detail=f"No deployment found for app: {app_name}")

    async def log_streamer():
        try:
            process = await asyncio.create_subprocess_exec(
                'flyctl', 'logs', '--app', app_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                log_entry = line.decode('utf-8').strip()

                formatted_response = {
                    "choices": [
                        {
                            "delta": {
                                "content": log_entry + "\n"
                            },
                            "finish_reason": None,
                            "index": 0
                        }
                    ]
                }

                yield f"data: {json.dumps(formatted_response)}\n\n"
        except Exception as e:
            logger.error(f"Error streaming logs for app {app_name}: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(log_streamer(), media_type="text/event-stream")

@router.get("/apps", response_model=Dict[str, str])
async def list_apps():
    try:
        logger.info("Listing all apps")
        apps_output = await execute_command(['flyctl', 'apps', 'list'])
        return {"apps": apps_output}
    except Exception as e:
        logger.error(f"Error listing apps: {e}")
        return {"detail": f"Error listing apps: {str(e)}. Make sure flyctl is installed and you're authenticated with Fly.io."}

@router.post("/clone", response_model=Dict[str, str])
async def clone_repo(request: CloneRequest = Body(...)):
    try:
        # Create a new project in the database
        db = next(get_db())
        project_name = request.repo_url.split('/')[-1]
        new_project = Project(
            name=project_name,
            user_id=request.user_id,
            repo_url=request.repo_url
        )
        db.add(new_project)
        db.commit()
        db.refresh(new_project)

        repo_id = new_project.id
        project_dir = get_project_directory(repo_id)

        clone_url = f"https://github.com/{request.repo_url}.git"

        project_dir.parent.mkdir(parents=True, exist_ok=True)

        process = await asyncio.create_subprocess_exec(
            "git", "clone", clone_url, str(project_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_message = f"Clone failed: {stderr.decode()}"
            logger.error(error_message)
            db.delete(new_project)
            db.commit()
            raise HTTPException(status_code=400, detail=error_message)

        cloned_repos[repo_id] = str(project_dir)

        logger.info(f"Repository cloned successfully with ID: {repo_id}")
        return {"repo_id": repo_id, "message": "Repository cloned successfully and project created"}
    except Exception as e:
        logger.error(f"Error cloning repository: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/repos", response_model=List[Dict[str, Any]])
async def list_repos(db: Session = Depends(get_db)):
    try:
        projects = db.query(Project).all()
        return [
            {
                "repo_id": str(project.id),
                "path": f"projects/{project.id}"
            }
            for project in projects
        ]
    except Exception as e:
        logger.error(f"Error listing repositories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/explore", response_model=Dict[str, Any])
async def explore_repo(request: ExploreRequest = Body(...)):
    if request.repo_id not in cloned_repos:
        logger.warning(f"Repository not found for ID: {request.repo_id}")
        raise HTTPException(status_code=404, detail="Repository not found")

    repo_path = cloned_repos[request.repo_id]
    full_path = os.path.join(repo_path, request.path or "")

    if request.action == "explore":
        return await explore_directory(full_path)
    elif request.action == "modify":
        return await modify_file(full_path, request.content)
    elif request.action == "create":
        return await create_file(full_path, request.content)
    elif request.action == "remove":
        return await remove_file(full_path)
    elif request.action == "create_dockerfile":
        return await create_dockerfile(repo_path)
    else:
        logger.error(f"Invalid action: {request.action}")
        raise HTTPException(status_code=400, detail="Invalid action")

@router.get("/projects", response_model=Dict[str, Any])
async def list_projects(db: Session = Depends(get_db)):
    try:
        projects = db.query(Project).all()
        project_list = [
            {
                "id": project.id,
                "name": project.name,
                "user_id": project.user_id,
                "repo_url": project.repo_url,
                "created_at": project.created_at,
                "updated_at": project.updated_at,
                "repo_id": project.id,
                "path": f"projects/{project.id}"
            }
            for project in projects
        ]

        return {
            "projects": project_list,
            "repositories": [
                {
                    "repo_id": project["repo_id"],
                    "path": project["path"]
                }
                for project in project_list
            ]
        }
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/projects/{project_id}", response_model=Dict[str, str])
async def update_project(
    project_id: str,
    request: UpdateProjectRequest,
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if request.name:
        project.name = request.name
    if request.repo_url:
        project.repo_url = request.repo_url
    
    project.last_updated = datetime.utcnow()
    db.commit()
    
    return {"message": "Project updated successfully"}

@router.delete("/projects/{project_id}", response_model=Dict[str, str])
async def delete_project(
    project_id: str,
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_dir = os.path.join("projects", project_id)
    if os.path.exists(project_dir):
        shutil.rmtree(project_dir)
    
    db.delete(project)
    db.commit()
    
    return {"message": "Project deleted successfully"}

@router.post("/stop-app/{app_name}", response_model=Dict[str, Any])
async def stop_application(app_name: str, signal: str = "SIGINT", timeout: int = 30, wait_timeout: int = 300):
    try:
        result = await stop_app(app_name, signal, timeout, wait_timeout)
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error stopping app {app_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error stopping app: {str(e)}")

@router.post("/docker", response_model=Dict[str, Any])
async def create_dockerfile_endpoint(repo_id: str = Body(..., embed=True), db: Session = Depends(get_db)):
    debug_info = {}
    try:
        project = db.query(Project).filter(Project.id == repo_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        debug_info["project_id"] = project.id
        debug_info["project_name"] = project.name
        
        current_dir = os.path.abspath(os.getcwd())
        debug_info["current_dir"] = current_dir
        
        project_dir = get_project_directory(project.id)
        debug_info["project_dir"] = str(project_dir)
        
        if not project_dir.exists():
            error_message = f"Project directory not found: {project_dir}"
            debug_info["error"] = error_message
            logger.error(error_message)
            raise HTTPException(status_code=404, detail=error_message)
        
        project_contents = os.listdir(project_dir)
        debug_info["project_contents"] = project_contents
        
        dockerfile_path = project_dir / "Dockerfile"
        if dockerfile_path.exists():
            return {"message": "Dockerfile already exists", "debug_info": debug_info}
        
        aider_command = [
            "aider",
            "--yes-always",
            f"--file={project_dir}",
            "--message=Review the files and folder structure in this project. The project contents are: " + 
            ", ".join(project_contents) + 
            ". Identify the main application, its dependencies, and any specific requirements. " +
            "If a requirements.txt file exists, use it to determine dependencies. " +
            "If you can't find enough information to create a complete Dockerfile, " +
            "create a basic Dockerfile with placeholders and comments explaining what additional information is needed. " +
            "Then, create a Dockerfile that can build and run this application. " +
            "The Dockerfile should be optimized for production use and follow best practices. " +
            "Include comments in the Dockerfile to explain each step."
        ]
        debug_info["aider_command"] = " ".join(aider_command)
        
        process = await asyncio.create_subprocess_exec(
            *aider_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        debug_info["aider_stdout"] = stdout.decode()
        debug_info["aider_stderr"] = stderr.decode()
        
        if dockerfile_path.exists():
            dockerfile_content = dockerfile_path.read_text()
            return {
                "message": "Dockerfile created successfully",
                "content": dockerfile_content,
                "debug_info": debug_info
            }
        else:
            return {
                "message": "Dockerfile creation needs more information",
                "aider_output": debug_info["aider_stdout"],
                "debug_info": debug_info
            }
    
    except HTTPException as http_exc:
        logger.error(f"HTTP exception occurred: {http_exc.detail}")
        debug_info["error"] = http_exc.detail
        debug_info["traceback"] = traceback.format_exc()
        return JSONResponse(
            status_code=http_exc.status_code,
            content={"detail": http_exc.detail, "debug_info": debug_info}
        )
    
    except Exception as e:
        logger.error(f"Error creating Dockerfile: {e}")
        debug_info["error"] = str(e)
        debug_info["traceback"] = traceback.format_exc()
        return JSONResponse(
            status_code=500,
            content={"detail": str(e), "debug_info": debug_info}
        )

@router.on_event("shutdown")
async def cleanup():
    for app_name in list(deployments.keys()):
        try:
            await execute_command(['flyctl', 'apps', 'destroy', app_name, '--yes'])
            logger.info(f"Destroyed app: {app_name}")
            del deployments[app_name]
        except Exception as e:
            logger.error(f"Error destroying app during cleanup: {e}")

    for repo_id, repo_path in cloned_repos.items():
        logger.info(f"Repository preserved: {repo_id} at {repo_path}")

    cloned_repos.clear()
