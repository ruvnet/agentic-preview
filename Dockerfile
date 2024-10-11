# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /app

# Copy the entire project directory
COPY . /app

# Copy the templates directory
COPY ./templates /app/templates

# Install Poetry
RUN pip install --no-cache-dir poetry

# Configure Poetry
RUN poetry config virtualenvs.create false

# Change to the agentic_platform directory
WORKDIR /app/agentic_platform

# Install dependencies
RUN if [ -f pyproject.toml ]; then \
        poetry install --only main --no-interaction --no-ansi; \
    elif [ -f requirements.txt ]; then \
        pip install -r requirements.txt; \
    else \
        echo "No pyproject.toml or requirements.txt found. Skipping dependency installation."; \
    fi

# Expose port 8080 for the FastAPI application
EXPOSE 8080

# Run the FastAPI application using Uvicorn on port 8080
CMD ["uvicorn", "agentic_platform.main:app", "--host", "0.0.0.0", "--port", "8080"]
