# Agentic Preview

Agentic Preview is an asynchronous FastAPI backend service that allows users to deploy preview environments using Fly.io.

## Features

- Deploys GitHub repositories to Fly.io
- Asynchronous operations for improved performance
- Configurable runtime limit for deployments
- Cleans up resources after usage

## Requirements

- Python 3.8 or higher
- Git
- Fly.io CLI (`flyctl`)

## Installation

Run the `install.sh` script to set up the project environment:

```bash
bash install.sh
```
# Agentic Preview

## Installation

This project uses Poetry for dependency management. Follow these steps to set up and run the project:

1. Ensure you have Python 3.8 or higher installed on your system.

2. Install Poetry if you haven't already:
   ```
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. Clone the repository:
   ```
   git clone <repository-url>
   cd agentic_preview
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
   python main.py
   ```

   Or, if you prefer to run it without activating the virtual environment:
   ```
   poetry run python main.py
   ```

3. The application should now be running. Check the console output for the local address and port where the service is available.

## Development

To add new dependencies to the project:

```
poetry add <package-name>
```

To update dependencies:

```
poetry update
```

To run tests (if applicable):

```
poetry run pytest
```

## Troubleshooting

If you encounter any issues during installation or running the application, please check the following:

1. Ensure you're using the correct Python version (3.8+).
2. Make sure Poetry is correctly installed and in your system PATH.
3. If you're having dependency issues, try deleting the `poetry.lock` file and running `poetry install` again.

For more information on using Poetry, refer to the [official Poetry documentation](https://python-poetry.org/docs/).
