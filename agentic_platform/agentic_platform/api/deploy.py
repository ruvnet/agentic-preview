# agentic_platform/agentic_platform/api/deploy.py
import os
import asyncio
import json
import shutil
from datetime import datetime
from typing import List, Optional, Dict, Any, Union

from fastapi import APIRouter, HTTPException, Body, Path, Query, Depends
from pydantic import BaseModel
from fastapi.responses import RedirectResponse, StreamingResponse, JSONResponse
import logging
import uuid
from sqlalchemy.orm import Session
from ..crud import get_db, update_project_user_data
from ..models import Project
from typing import List, Dict, Any
from typing import Optional
from sqlalchemy.orm import Session
from ..crud import get_db
from ..models import Project
import os
import asyncio
import traceback

def get_project_directory(project_id: str) -> str:
    return os.path.join("projects", project_id)

router = APIRouter()

# Configurable runtime limit in seconds
RUN_TIME_LIMIT = 200  # Adjust as needed

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s:%(lineno)d %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

deployments = {}  # key: app_name, value: deployment info
cloned_repos = {}  # key: repo_id, value: repo_path

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
        schema_extra = {
            "description": "Request model for deploying an application",
            "properties": {
                "repo": {"description": "GitHub repository in the format 'username/repo'"},
                "branch": {"description": "Git branch to deploy"},
                "args": {"description": "Additional arguments for deployment"},
                "memory": {"description": "Memory allocation in MB"},
                "app_name": {"description": "Optional custom name for the application"}
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

async def execute_command(cmd: List[str], cwd: Optional[str] = None):
    """Asynchronously execute a shell command."""
    logger.debug(f"Executing command: {' '.join(cmd)} in directory: {cwd}")
    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    logger.debug(f"Command stdout: {stdout.decode()}")
    logger.debug(f"Command stderr: {stderr.decode()}")

    if process.returncode != 0:
        error_message = f"Command {' '.join(cmd)} failed with error code {process.returncode}\nstdout:\n{stdout.decode()}\nstderr:\n{stderr.decode()}"
        logger.error(error_message)
        raise Exception(error_message)

    return stdout.decode()

async def stop_instance(app_name: str):
    """Stops the Fly.io instance after RUN_TIME_LIMIT seconds."""
    await asyncio.sleep(RUN_TIME_LIMIT)
    try:
        logger.info(f"Stopping app {app_name} after {RUN_TIME_LIMIT} seconds.")
        await execute_command(['flyctl', 'apps', 'destroy', app_name, '--yes'])
        logger.info(f"[{datetime.utcnow()}] App {app_name} has been stopped.")
    except Exception as e:
        logger.error(f"Error stopping app {app_name}: {e}")

async def deploy_app(repo: str, branch: str, args: List[str], app_name: str, repo_dir: str, memory: int):
    try:
        # Check if Dockerfile exists; if not, return an error
        dockerfile_path = os.path.join(repo_dir, 'Dockerfile')
        if not os.path.exists(dockerfile_path):
            error_msg = f"Dockerfile not found in {repo_dir}. A Dockerfile is required for deployment."
            logger.error(error_msg)
            raise Exception(error_msg)
        else:
            logger.info("Using existing Dockerfile.")

        # Check if fly.toml exists, generate one if not
        fly_toml_path = os.path.join(repo_dir, 'fly.toml')
        if not os.path.exists(fly_toml_path):
            logger.info("Creating fly.toml configuration.")
            fly_toml_content = f"""
app = "{app_name}"

[build]
  dockerfile = "Dockerfile"

[env]
  PORT = "8080"

[vm]
  memory_mb = {memory}

[[services]]
  http_checks = []
  internal_port = 8080
  processes = ["app"]
  protocol = "tcp"

  [services.concurrency]
    hard_limit = 25
    soft_limit = 20

  [[services.ports]]
    handlers = ["http"]
    port = 80

  [[services.ports]]
    handlers = ["tls", "http"]
    port = 443

  [[services.tcp_checks]]
    grace_period = "1s"
    interval = "15s"
    restart_limit = 0
    timeout = "2s"
"""
            with open(fly_toml_path, 'w') as fly_toml_file:
                fly_toml_file.write(fly_toml_content)
        else:
            logger.info("Using existing fly.toml.")

        # Create the app on Fly.io
        await execute_command(['flyctl', 'apps', 'create', app_name], cwd=repo_dir)

        # Deploy the app using flyctl deploy
        deploy_cmd = ['flyctl', 'deploy', '--remote-only', '--config', 'fly.toml', '--app', app_name]
        deploy_cmd.extend(args)
        await execute_command(deploy_cmd, cwd=repo_dir)

        # Get the app URL using 'flyctl status'
        app_status_json = await execute_command(['flyctl', 'status', '--json', '--app', app_name])
        app_status = json.loads(app_status_json)

        # Extract the hostname
        hostname = app_status.get('Hostname', f"{app_name}.fly.dev")
        logger.info(f"Preview URL: {hostname}")

        # Schedule the instance to stop after RUN_TIME_LIMIT seconds
        asyncio.create_task(stop_instance(app_name))

        # Update deployment status
        deployments[app_name] = {
            "status": "Deployed",
            "preview_url": f"https://{hostname}",
            "message": "Deployment successful.",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error during deployment: {e}")
        # Update deployment status
        deployments[app_name] = {
            "status": "Failed",
            "preview_url": None,
            "message": f"Deployment failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }
        # Capture the traceback for debugging
        import traceback
        traceback_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
        logger.error(f"Stack trace: {traceback_str}")
        # Clean up the app on Fly.io
        try:
            await execute_command(['flyctl', 'apps', 'destroy', app_name, '--yes'])
        except Exception as destroy_exc:
            logger.error(f"Error destroying app after failed deployment: {destroy_exc}")
        raise e
    finally:
        # Ensure cleanup happens regardless of success or failure
        if repo_dir and os.path.exists(repo_dir):
            shutil.rmtree(repo_dir, ignore_errors=True)
            logger.info(f"Cleaned up repository directory: {repo_dir}")

@router.post("/deploy", response_model=Dict[str, str], 
             summary="Deploy an application",
             description="Clone a GitHub repository, deploy it to Fly.io, and return deployment status")
async def deploy(deploy_request: DeployRequest = Body(
    ...,
    example={
        "repo": "ruvnet/agentic_preview",
        "branch": "main",
        "args": ["--build-arg", "ENV=production"],
        "memory": 2048,
        "app_name": "my-app"
    }
)):
    app_name: Optional[str] = None
    repo_dir: Optional[str] = None  # Initialize repo_dir
    try:
        repo = deploy_request.repo
        branch = deploy_request.branch
        args = deploy_request.args or []
        memory = deploy_request.memory or 2048  # Default to 2048 MB if not specified

        logger.info(f"Deploying repository: {repo}, branch: {branch}, args: {args}, memory: {memory}MB")

        # Clone the repository
        repo_name = repo.split('/')[-1]
        timestamp = int(datetime.utcnow().timestamp())
        unique_id = uuid.uuid4().hex  # Generate a unique identifier
        repo_dir = f"/tmp/{repo_name}-{unique_id}"
        clone_url = f"https://github.com/{repo}.git"

        # Fetch branch information to verify branch existence
        branches_output = await execute_command(['git', 'ls-remote', '--heads', clone_url])
        logger.debug(f"Branches output: {branches_output}")
        if f'refs/heads/{branch}' not in branches_output:
            if 'refs/heads/main' in branches_output:
                logger.warning(f"Branch '{branch}' not found. Defaulting to 'main'.")
                branch = 'main'  # Default to 'main' if specified branch not found and 'main' exists
            elif 'refs/heads/master' in branches_output:
                logger.warning(f"Branch '{branch}' not found. Defaulting to 'master'.")
                branch = 'master'  # Default to 'master' if 'main' is not found but 'master' exists
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
        asyncio.create_task(deploy_app(repo, branch, args, app_name, repo_dir, memory))

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

@router.get("/status/{app_name}", 
            response_model=Dict[str, Any],
            summary="Check deployment status",
            description="Get the current status of a deployed application")
async def check_status(
    app_name: str = Path(..., description="Name of the deployed application")
):
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

@router.get("/logs/{app_name}", 
            response_class=StreamingResponse,
            summary="Stream application logs",
            description="Stream real-time logs from a deployed application")
async def stream_logs(
    app_name: str = Path(..., example="my-app", description="Name of the application to stream logs from")
):
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

                # Format the log entry to match the GitHub Copilot LLM API response
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

                # Yield the formatted response as a JSON string
                yield f"data: {json.dumps(formatted_response)}\n\n"
        except Exception as e:
            logger.error(f"Error streaming logs for app {app_name}: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(log_streamer(), media_type="text/event-stream")

@router.get("/apps", 
            response_model=Dict[str, str],
            summary="List all applications",
            description="List all applications deployed on Fly.io")
async def list_apps():
    try:
        logger.info("Listing all apps")
        apps_output = await execute_command(['flyctl', 'apps', 'list'])
        return {"apps": apps_output}
    except Exception as e:
        logger.error(f"Error listing apps: {e}")
        return {"detail": f"Error listing apps: {str(e)}. Make sure flyctl is installed and you're authenticated with Fly.io."}

# New endpoints for cloning and exploring repositories
@router.post("/clone", 
             response_model=Dict[str, str],
             summary="Clone a repository",
             description="Clone a GitHub repository and create a new project")
async def clone_repo(request: CloneRequest = Body(
    ...,
    example={"repo_url": "username/repo", "user_id": "user123"},
    description="GitHub repository URL to clone and user ID"
)):
    repo_id = str(uuid.uuid4())
    projects_dir = "projects"  # Changed from "/projects" to match the existing structure
    project_dir = os.path.join(projects_dir, repo_id)

    try:
        # Construct the full GitHub repository URL
        clone_url = f"https://github.com/{request.repo_url}.git"

        # Create projects directory if it doesn't exist
        os.makedirs(projects_dir, exist_ok=True)

        process = await asyncio.create_subprocess_exec(
            "git", "clone", clone_url, project_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_message = f"Clone failed: {stderr.decode()}"
            logger.error(error_message)
            raise HTTPException(status_code=400, detail=error_message)

        # Update the database
        db = next(get_db())
        project_name = request.repo_url.split('/')[-1]
        update_project_user_data(project_name, request.user_id, request.repo_url, db)

        # Add the cloned repository to the cloned_repos dictionary
        cloned_repos[repo_id] = project_dir

        logger.info(f"Repository cloned successfully with ID: {repo_id}")
        return {"repo_id": repo_id, "message": "Repository cloned successfully and project created"}
    except Exception as e:
        logger.error(f"Error cloning repository: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/repos", 
            response_model=List[Dict[str, Any]],
            summary="List cloned repositories",
            description="List all cloned repositories with their IDs and paths")
async def list_repos(db: Session = Depends(get_db)):
    try:
        projects = db.query(Project).all()
        return [
            {
                "repo_id": str(project.id),  # Convert UUID to string
                "path": f"projects/{project.id}"
            }
            for project in projects
        ]
    except Exception as e:
        logger.error(f"Error listing repositories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/explore", 
             response_model=Dict[str, Any],
             summary="Explore repository",
             description="Explore, modify, create, or remove files in a cloned repository")
async def explore_repo(request: ExploreRequest = Body(
    ...,
    example={
        "repo_id": "123e4567-e89b-12d3-a456-426614174000",
        "action": "explore",
        "path": "/app",
        "content": ""
    },
    description="Request to explore or modify repository contents"
)):
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

async def explore_directory(path):
    try:
        if not os.path.exists(path):
            logger.error(f"Path does not exist: {path}")
            raise HTTPException(status_code=404, detail="Path does not exist")
        if os.path.isfile(path):
            with open(path, 'r') as f:
                content = f.read()
            return {"type": "file", "content": content}
        elif os.path.isdir(path):
            items = os.listdir(path)
            return {"type": "directory", "items": items}
        else:
            logger.error(f"Unknown path type: {path}")
            raise HTTPException(status_code=400, detail="Unknown path type")
    except Exception as e:
        logger.error(f"Error exploring directory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def modify_file(path, content):
    try:
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(content)
        logger.info(f"File modified successfully: {path}")
        return {"message": "File modified successfully"}
    except Exception as e:
        logger.error(f"Error modifying file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def create_file(path, content):
    try:
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(content)
        logger.info(f"File created successfully: {path}")
        return {"message": "File created successfully"}
    except Exception as e:
        logger.error(f"Error creating file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def remove_file(path):
    try:
        if os.path.isfile(path):
            os.remove(path)
            logger.info(f"File removed successfully: {path}")
            return {"message": "File removed successfully"}
        elif os.path.isdir(path):
            shutil.rmtree(path)
            logger.info(f"Directory removed successfully: {path}")
            return {"message": "Directory removed successfully"}
        else:
            logger.error(f"Path does not exist: {path}")
            raise HTTPException(status_code=404, detail="Path does not exist")
    except Exception as e:
        logger.error(f"Error removing file or directory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def create_dockerfile(repo_path):
    try:
        logger.info(f"Generating Dockerfile for repository at: {repo_path}")
        process = await asyncio.create_subprocess_exec(
            "gh", "copilot", "suggest", "-t", "shell",
            "--input", "Create a Dockerfile for the project",
            cwd=repo_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_message = f"Dockerfile creation failed: {stderr.decode()}"
            logger.error(error_message)
            raise HTTPException(status_code=500, detail=error_message)

        dockerfile_content = stdout.decode()

        dockerfile_path = os.path.join(repo_path, 'Dockerfile')
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content)

        logger.info(f"Dockerfile created successfully at: {dockerfile_path}")
        return {"message": "Dockerfile created successfully", "content": dockerfile_content}
    except Exception as e:
        logger.error(f"Error creating Dockerfile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/projects", response_model=Dict[str, Any], summary="List all projects")
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
                "repo_id": project.id,  # Adding `repo_id` explicitly
                "path": f"projects/{project.id}"  # Dynamically constructing `path`
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

@router.on_event("shutdown")
async def cleanup():
    # Clean up cloned repositories
    for repo_id, repo_path in cloned_repos.items():
        shutil.rmtree(repo_path, ignore_errors=True)
        logger.info(f"Cleaned up repository: {repo_id}")

    # Clean up deployments (optional)
    for app_name in list(deployments.keys()):
        try:
            await execute_command(['flyctl', 'apps', 'destroy', app_name, '--yes'])
            logger.info(f"Destroyed app: {app_name}")
            del deployments[app_name]
        except Exception as e:
            logger.error(f"Error destroying app during cleanup: {e}")

@router.get("/projects", response_model=Dict[str, Any], summary="List all projects")
async def list_projects(db: Session = Depends(get_db)):
    try:
        projects = db.query(Project).all()
        project_list = [
            {
                "id": project.id,  # Assuming `id` is used as `repo_id`
                "name": project.name,
                "user_id": project.user_id,
                "repo_url": project.repo_url,
                "created_at": project.created_at,
                "updated_at": project.updated_at,
                "repo_id": project.id,  # Adding `repo_id` explicitly
                "path": f"projects/{project.id}"  # Dynamically constructing `path`
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


@router.put("/projects/{project_id}", 
            response_model=Dict[str, str],
            summary="Update a project",
            description="Update the details of an existing project")
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

@router.delete("/projects/{project_id}", 
               response_model=Dict[str, str],
               summary="Delete a project",
               description="Delete an existing project")
async def delete_project(
    project_id: str,
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Delete the project directory
    project_dir = os.path.join("projects", project_id)
    if os.path.exists(project_dir):
        shutil.rmtree(project_dir)
    
    # Delete the project from the database
    db.delete(project)
    db.commit()
    
    return {"message": "Project deleted successfully"}
async def stream_aider_output(process):
    async for line in process.stdout:
        logger.info(line.decode().strip())
@router.post("/docker", response_model=Dict[str, Any])
async def create_dockerfile(repo_id: str = Body(..., embed=True), db: Session = Depends(get_db)):
    debug_info = {}
    try:
        # Get the project from the database
        project = db.query(Project).filter(Project.id == repo_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        debug_info["project_id"] = str(project.id)
        debug_info["project_name"] = project.name
        
        # Get the absolute path of the current working directory
        current_dir = os.path.abspath(os.getcwd())
        debug_info["current_dir"] = current_dir
        
        # Construct the project path
        projects_dir = os.path.abspath(os.path.join(current_dir, "..", "projects"))
        project_dir = os.path.join(projects_dir, str(project.id))
        debug_info["projects_dir"] = projects_dir
        debug_info["project_dir"] = project_dir
        
        # Check if the project directory exists
        if not os.path.exists(project_dir):
            debug_info["error"] = f"Project directory does not exist: {project_dir}"
            logger.error(debug_info["error"])
            raise HTTPException(status_code=404, detail="Project directory not found")
        
        # List contents of the project directory
        debug_info["project_contents"] = os.listdir(project_dir)
        
        # Check if Dockerfile already exists
        dockerfile_path = os.path.join(project_dir, "Dockerfile")
        if os.path.exists(dockerfile_path):
            return {"message": "Dockerfile already exists", "debug_info": debug_info}
        
        # Prepare the Aider command
        aider_command = [
            "aider",
            "--yes-always",
            f"--work-dir={project_dir}",
            "--model=gpt-4o-mini",
            "--use-github",
            "--message=Review the files and folder structure in this project. Identify the main application, its dependencies, and any specific requirements. Then, create a Dockerfile that can build and run this application. The Dockerfile should be optimized for production use and follow best practices. Include comments in the Dockerfile to explain each step."
        ]
        debug_info["aider_command"] = " ".join(aider_command)
        
        # Run Aider and stream output
        process = await asyncio.create_subprocess_exec(
            *aider_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        debug_info["aider_stdout"] = stdout.decode()
        debug_info["aider_stderr"] = stderr.decode()
        
        # Check if Dockerfile was created
        if os.path.exists(dockerfile_path):
            with open(dockerfile_path, 'r') as f:
                dockerfile_content = f.read()
            return {"message": "Dockerfile created successfully", "content": dockerfile_content, "debug_info": debug_info}
        else:
            debug_info["error"] = "Dockerfile creation failed"
            return {"message": "Dockerfile creation failed", "debug_info": debug_info}
    
    except Exception as e:
        logger.error(f"Error creating Dockerfile: {e}")
        debug_info["error"] = str(e)
        debug_info["traceback"] = traceback.format_exc()
        return JSONResponse(
            status_code=500,
            content={"detail": str(e), "debug_info": debug_info}
        )
