# Agentic Platform

Agentic Platform is a unified FastAPI backend service that combines the functionalities of Agentic Preview and Agentic Editor.

## Features

- Deploy GitHub repositories to Fly.io
- Asynchronous operations for improved performance
- Configurable runtime limit for deployments
- Cleans up resources after usage
- RESTful API for executing Aider commands
- Virtual Environment Management
- Configurable Execution

## Installation

This project uses Poetry for dependency management. Follow these steps to set up the project:

1. Ensure you have Python 3.8 or higher installed on your system.

2. Install Poetry if you haven't already:
   ```
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. Clone the repository:
   ```
   git clone <repository-url>
   cd agentic_platform
   ```

4. Install the project dependencies:
   ```
   poetry install
   ```

## Running the Application

To run the application, follow these steps:

1. Activate the Poetry virtual environment:
   ```
   poetry shell
   ```

2. Start the application:
   ```
   poetry run uvicorn main:app --host 0.0.0.0 --port 8000
   ```

3. The application should now be running. Check the console output for the local address and port where the service is available.

## Usage

### Deploying an Application

To deploy an application, send a POST request to the `/preview/deploy` endpoint with the following JSON body:

```json
{
  "repo": "username/repository",
  "branch": "main",
  "args": ["--build-arg", "ENV=production"]
}
```

### Running Aider

To execute the Aider tool, send a POST request to the `/editor/run-aider` endpoint with the appropriate JSON payload.

## License

MIT License
