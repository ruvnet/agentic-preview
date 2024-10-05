import os
import asyncio
import json
import shutil
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import RedirectResponse
import logging

app = FastAPI()

# Configurable runtime limit in seconds
RUN_TIME_LIMIT = 200  # You can change this value as needed

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class DeployRequest(BaseModel):
    repo: str
    branch: str
    args: Optional[List[str]] = []

    class Config:
        json_schema_extra = {
            "example": {
                "repo": "octocat/Hello-World",
                "branch": "main",
                "args": ["--build-arg", "ENV=production"]
            }
        }

@app.get("/")
async def redirect_to_docs():
    return RedirectResponse(url="/docs")

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
        logger.error(f"Command failed with return code {process.returncode}: {' '.join(cmd)}")
        raise Exception(f"Command {' '.join(cmd)} failed with error: {stderr.decode()}")

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

async def deploy_app(repo: str, branch: str, args: List[str], app_name: str, repo_dir: str):
    try:
        # Set up Fly.io deployment
        await execute_command(['flyctl', 'launch', '--name', app_name, '--no-deploy', '--auto-confirm', '--region', 'iad'], cwd=repo_dir)

        # Check if Dockerfile exists, generate one if not
        dockerfile_path = os.path.join(repo_dir, 'Dockerfile')
        if not os.path.exists(dockerfile_path):
            logger.warning(f"Dockerfile not found in {repo_dir}. Generating a default Dockerfile.")
            with open(dockerfile_path, 'w') as dockerfile:
                dockerfile.write(
                    """
                    FROM python:3.9-slim
                    WORKDIR /app
                    COPY . /app
                    RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; else echo 'No requirements.txt found, skipping dependency installation.'; fi
                    CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
                    """
                )

        # Deploy the app (Step 1)
        deploy_cmd = ['flyctl', 'deploy', '--remote-only']
        deploy_cmd.extend(args)
        await execute_command(deploy_cmd, cwd=repo_dir)

        # Get the app URL (Step 2)
        app_info_json = await execute_command(['flyctl', 'info', '--json'], cwd=repo_dir)
        app_info = json.loads(app_info_json)
        preview_url = app_info.get('hostname', f"{app_name}.fly.dev")
        logger.info(f"Preview URL: {preview_url}")

        # Schedule the instance to stop after RUN_TIME_LIMIT seconds
        asyncio.create_task(stop_instance(app_name))

        # Cleanup the cloned repository
        shutil.rmtree(repo_dir, ignore_errors=True)
        logger.info(f"Cleaned up repository directory: {repo_dir}")

    except Exception as e:
        logger.error(f"Error during deployment: {e}")

@app.post("/deploy")
async def deploy(deploy_request: DeployRequest):
    app_name: Optional[str] = None
    try:
        repo = deploy_request.repo
        branch = deploy_request.branch
        args = deploy_request.args or []

        logger.info(f"Deploying repository: {repo}, branch: {branch}, args: {args}")

        # Clone the repository
        repo_name = repo.split('/')[-1]
        timestamp = int(datetime.utcnow().timestamp())
        repo_dir = f"/tmp/{repo_name}-{timestamp}"
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
        # Attempt to clone the repository without specifying a branch (use default branch)
        try:
            await execute_command(['git', 'clone', clone_url, repo_dir])
        except Exception as e:
            logger.error(f"Failed to clone default branch: {e}")
            # If cloning without a branch fails, fall back to explicitly looking for 'main' or 'master'
            branches_output = await execute_command(['git', 'ls-remote', '--heads', clone_url])
            logger.debug(f"Branches output: {branches_output}")
            if 'refs/heads/main' in branches_output:
                logger.warning(f"Default branch not found. Falling back to 'main'.")
                branch = 'main'
            elif 'refs/heads/master' in branches_output:
                logger.warning(f"Default branch not found. Falling back to 'master'.")
                branch = 'master'
            else:
                logger.error(f"No suitable branch found in repository '{repo}'.")
                raise HTTPException(status_code=400, detail=f"No suitable branch found in repository '{repo}'.")
            # Clone the repository without specifying a branch if none is provided
        if branch:
            await execute_command(['git', 'clone', '-b', branch, clone_url, repo_dir])
        else:
            await execute_command(['git', 'clone', clone_url, repo_dir])

        # Generate a unique app name
        app_name = f"preview-{repo_name.lower()}-{branch.lower() if branch else 'default'}-{timestamp}"
        logger.info(f"Generated app name: {app_name}")

        # Run deployment in the background
        asyncio.create_task(deploy_app(repo, branch, args, app_name, repo_dir))

        return {"app_name": app_name, "message": "Deployment started. Use /status/{app_name} to check the status."}
    except HTTPException as http_exc:
        logger.error(f"HTTP exception occurred: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{app_name}")
async def check_status(app_name: str):
    try:
        logger.info(f"Checking status for app: {app_name}")
        status_output = await execute_command(['flyctl', 'status', '--app', app_name])
        return {"status": status_output}
    except Exception as e:
        logger.error(f"Error checking app status: {e}")
        raise HTTPException(status_code=500, detail=f"Error checking app status: {str(e)}")

@app.get("/apps")
async def list_apps():
    try:
        logger.info("Listing all apps")
        apps_output = await execute_command(['flyctl', 'apps', 'list'])
        return {"apps": apps_output}
    except Exception as e:
        logger.error(f"Error listing apps: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing apps: {str(e)}")

@app.post("/deploy_test")
async def deploy_test():
    try:
        # Using a minimal, simple FastAPI Hello World repository
        repo = "dockersamples/example-voting-app"  # Using a known public Docker example
        branch = ""  # Default branch initially set to an empty string
        args = []

        logger.info(f"Starting test deployment for repository: {repo}, branch: {branch}")

        # Clone the repository
        repo_name = repo.split('/')[-1]
        timestamp = int(datetime.utcnow().timestamp())
        repo_dir = f"/tmp/{repo_name}-{timestamp}"
        clone_url = f"https://github.com/{repo}.git"

        # Clone the specified branch
        await execute_command(['git', 'clone', '-b', branch, clone_url, repo_dir])

        # Generate a unique app name
        app_name = f"preview-{repo_name.lower()}-{branch.lower()}-{timestamp}"
        logger.info(f"Generated app name: {app_name}")

        # Check if Dockerfile exists, generate a simple one if not
        dockerfile_path = os.path.join(repo_dir, 'Dockerfile')
        if not os.path.exists(dockerfile_path):
            logger.warning(f"Dockerfile not found in {repo_dir}. Generating a default Dockerfile.")
            with open(dockerfile_path, 'w') as dockerfile:
                dockerfile.write(
                    """
                    FROM python:3.9-slim
                    WORKDIR /app
                    COPY . /app
                    RUN pip install --no-cache-dir fastapi uvicorn
                    CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
                    """
                )

        # Run deployment in the background
        asyncio.create_task(deploy_app(repo, branch, args, app_name, repo_dir))

        return {"app_name": app_name, "message": "Test deployment started. Use /status/{app_name} to check the status."}
    except HTTPException as http_exc:
        logger.error(f"HTTP exception occurred during test deployment: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error during test deployment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)