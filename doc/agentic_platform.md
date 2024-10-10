# Agentic Platform

Last updated: [Current Date]

The Agentic Platform is the main component of this repository, located in the `agentic_platform/` directory. It combines the functionality of the Agentic Editor and Agentic Preview into a unified platform.

## Key Components

1. **API Files**:
   - `aider.py`: Contains Agentic Editor functionality
   - `deploy.py`: Contains Agentic Preview functionality
   - `architect.py`: Contains Architect functionality

2. **Database Management**:
   - `database.py`: Database initialization
   - `models.py`: Database models for User and Project
   - `crud.py`: CRUD operations for database interactions

## Key Functions

1. **Aider Operations**:
   - `process_aider_output(output_lines)`: Process Aider output

2. **Deployment Operations**:
   - `deploy_app(repo: str, branch: str, args: List[str], app_name: str, repo_dir: str, memory: int)`: Deploy an application
   - `stop_instance(app_name: str)`: Stop an instance of an application
   - `create_dockerfile(repo_path)`: Create a Dockerfile

3. **Database Operations**:
   - `get_db()`: Get a database session
   - `update_project_user_data(project_name: str, user_id: str, repo_url: str, db: Session)`: Update project user data
   - `remove_old_projects(db: Session, age: timedelta = None, user_id: str = None)`: Remove old projects
   - `cleanup_projects(db: Session)`: Clean up projects
   - `update_project_cost(db: Session, project_name: str, user_id: str, cost: float)`: Update project cost

For more detailed information on the implementation of these components and functions, please refer to the files in the `agentic_platform/agentic_platform/` directory.
