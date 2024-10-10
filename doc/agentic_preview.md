# Agentic Preview

Last updated: [Current Date]

The Agentic Preview is now part of the Agentic Platform, located in the `agentic_platform/agentic_platform/api/deploy.py` file. It is responsible for deploying and previewing projects.

## Key Components

1. **API File**: `deploy.py`
   - Contains the core functionality of the Agentic Preview

## Key Functions

1. **App Deployment and Management**:
   - `stop_instance(app_name: str)`: Stop an instance of an application
   - `deploy_app(repo: str, branch: str, args: List[str], app_name: str, repo_dir: str, memory: int)`: Deploy an application

2. **File Operations**:
   - `explore_directory(path)`: Explore a directory
   - `modify_file(path, content)`: Modify a file
   - `create_file(path, content)`: Create a new file
   - `remove_file(path)`: Remove a file

3. **Dockerfile Creation**:
   - `create_dockerfile(repo_path)`: Create a Dockerfile

4. **API Endpoints**:
   - POST `/docker`: Create a Dockerfile for a specified project using Aider

For more detailed information on the implementation of these functions, please refer to the `deploy.py` file in the `agentic_platform/agentic_platform/api/` directory.
