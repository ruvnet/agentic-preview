from fastapi import APIRouter, Body, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional
import asyncio
from datetime import datetime
import logging
import json
import shutil

router = APIRouter()
logger = logging.getLogger(__name__)

def is_fly_installed():
    return shutil.which("fly") is not None

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

async def deploy_app_background(deployment: DeploymentRequest, app_name: str):
    try:
        # Placeholder for actual deployment logic
        await asyncio.sleep(5)  # Simulate deployment process
        logger.info(f"Deployed {app_name} from {deployment.repo}")
        
        # Schedule the app to stop after a certain time (e.g., 30 minutes)
        await asyncio.sleep(1800)  # 30 minutes
        await stop_app(app_name)
    except Exception as e:
        logger.error(f"Error in deploy_app_background: {str(e)}")

async def stop_app(app_name: str, signal: str = "SIGINT", timeout: int = 30, wait_timeout: int = 300):
    if not is_fly_installed():
        logger.error("The 'fly' command is not installed or not in the system PATH.")
        raise Exception("The 'fly' command is not available. Please contact the administrator.")

    try:
        # Check if the app exists
        check_app_cmd = ["fly", "apps", "list", "--json"]
        logger.debug(f"Executing command: {' '.join(check_app_cmd)}")
        
        check_app_process = await asyncio.create_subprocess_exec(
            *check_app_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        check_app_stdout, check_app_stderr = await check_app_process.communicate()
        
        if check_app_process.returncode != 0:
            logger.error(f"Failed to list apps. Error: {check_app_stderr.decode()}")
            return
        
        apps = json.loads(check_app_stdout.decode())
        if not any(app['Name'] == app_name for app in apps):
            logger.info(f"App {app_name} not found. It may have been already deleted.")
            return

        # List machines for the app
        list_cmd = ["fly", "machines", "list", "-a", app_name, "--json"]
        logger.debug(f"Executing command: {' '.join(list_cmd)}")
        
        list_process = await asyncio.create_subprocess_exec(
            *list_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        list_stdout, list_stderr = await list_process.communicate()
        
        if list_process.returncode != 0:
            logger.error(f"Failed to list machines for app {app_name}. Error: {list_stderr.decode()}")
            return
        
        machines = json.loads(list_stdout.decode())
        
        if not machines:
            logger.info(f"No machines found for app {app_name}")
            return

        # Stop each machine
        for machine in machines:
            machine_id = machine['id']
            stop_cmd = [
                "fly", "machine", "stop",
                machine_id,
                "-a", app_name,
                "-s", signal,
                "--timeout", str(timeout),
                "-w", f"{wait_timeout}s"
            ]
            logger.debug(f"Executing command: {' '.join(stop_cmd)}")
            
            stop_process = await asyncio.create_subprocess_exec(
                *stop_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stop_stdout, stop_stderr = await stop_process.communicate()
            
            if stop_process.returncode == 0:
                logger.info(f"Successfully stopped machine {machine_id} for app {app_name}")
            else:
                logger.error(f"Failed to stop machine {machine_id} for app {app_name}. Error: {stop_stderr.decode()}")

        logger.info(f"Finished stopping all machines for app {app_name}")

    except Exception as e:
        logger.error(f"Error stopping app {app_name}: {str(e)}")

@router.post("/deploy", 
             summary="Deploy an application",
             description="Clone a GitHub repository and deploy it to the platform")
async def deploy_app(background_tasks: BackgroundTasks, deployment: DeploymentRequest = Body(...)):
    try:
        # Generate a unique app name if not provided
        app_name = deployment.app_name or f"preview-{deployment.repo.split('/')[-1].lower()}-{deployment.branch.lower()}-{int(datetime.utcnow().timestamp())}"
        
        # Start the deployment in the background
        background_tasks.add_task(deploy_app_background, deployment, app_name)
        
        return {
            "app_name": app_name,
            "message": "Deployment started.",
            "status_url": f"/status/{app_name}"
        }
    except Exception as e:
        logger.error(f"Error in deploy_app: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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

@router.post("/stop/{app_name}",
             summary="Stop an application",
             description="Stop a deployed application")
async def stop_application(app_name: str):
    try:
        await stop_app(app_name)
        return {"message": f"Stop command issued for {app_name}"}
    except Exception as e:
        logger.error(f"Error stopping app {app_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Add other route handlers as needed
