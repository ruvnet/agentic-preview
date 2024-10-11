# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /app

# Copy the entire project directory
COPY . /app

# Debug: List contents of /app
RUN ls -la /app

# Install Poetry
RUN pip install --no-cache-dir poetry

# Debug: Print Poetry version
RUN poetry --version

# Configure Poetry
RUN poetry config virtualenvs.create false

# Change to the agentic_platform directory
WORKDIR /app/agentic_platform

# Debug: List contents of /app/agentic_platform
RUN ls -la /app/agentic_platform

# Install dependencies
RUN if [ -f pyproject.toml ]; then \
        poetry install --only main --no-interaction --no-ansi; \
    elif [ -f requirements.txt ]; then \
        pip install -r requirements.txt; \
    else \
        echo "No pyproject.toml or requirements.txt found. Skipping dependency installation."; \
    fi

# Expose port 5000 for the FastAPI application
EXPOSE 5000

# Run the FastAPI application using Uvicorn
CMD ["uvicorn", "agentic_platform.main:app", "--host", "0.0.0.0", "--port", "5000"]
