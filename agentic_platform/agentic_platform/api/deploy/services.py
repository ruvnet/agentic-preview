import asyncio
import json
import os
import shutil
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException
from .utils import get_project_directory, is_fly_installed, execute_command
import logging

logger = logging.getLogger(__name__)

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

        return {
            "status": "Deployed",
            "preview_url": f"https://{hostname}",
            "message": "Deployment successful.",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error during deployment: {e}")
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

async def stop_instance(app_name: str):
    # Implement the logic to stop the instance after a certain time
    pass

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

async def stop_app(app_name: str, signal: str = "SIGINT", timeout: int = 30, wait_timeout: int = 300):
    logger.info(f"Attempting to stop app: {app_name} with signal: {signal}, timeout: {timeout}, wait_timeout: {wait_timeout}")
    
    if not is_fly_installed():
        logger.error("The 'fly' command is not installed or not in the system PATH.")
        raise HTTPException(status_code=500, detail="The 'fly' command is not available. Please contact the administrator.")

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
            raise HTTPException(status_code=500, detail=f"Failed to list apps: {check_app_stderr.decode()}")
        
        apps = json.loads(check_app_stdout.decode())
        if not any(app['Name'] == app_name for app in apps):
            logger.info(f"App {app_name} not found. It may have been already deleted.")
            return {"message": f"App {app_name} not found. It may have been already deleted."}

        # If the app exists, proceed with listing and stopping machines
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
            raise HTTPException(status_code=500, detail=f"Failed to list machines: {list_stderr.decode()}")
        
        machines = json.loads(list_stdout.decode())
        
        if not machines:
            logger.info(f"No machines found for app {app_name}")
            return {"message": f"No machines found for app {app_name}"}
        
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
            
            if stop_process.returncode != 0:
                logger.error(f"Failed to stop machine {machine_id} for app {app_name}. Error: {stop_stderr.decode()}")
                raise HTTPException(status_code=500, detail=f"Failed to stop machine {machine_id}: {stop_stderr.decode()}")
            
            logger.info(f"Successfully stopped machine {machine_id} for app {app_name}")

        return {"message": f"All machines for app {app_name} have been stopped"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error stopping app {app_name}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

async def stream_aider_output(process):
    async for line in process.stdout:
        logger.info(line.decode().strip())

async def get_flyctl_help():
    try:
        result = await execute_command(['flyctl', '--help'])
        return result
    except Exception as e:
        logger.error(f"Error getting flyctl help: {e}")
        raise Exception(f"Error getting flyctl help: {str(e)}")
