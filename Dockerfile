# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /app

# Copy only the necessary files
COPY pyproject.toml poetry.lock ./

# Install Poetry and dependencies
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi

# Copy the application code
COPY agentic_preview ./agentic_preview

# Expose port 5000 for the FastAPI application
EXPOSE 5000

# Run the FastAPI application using Uvicorn
CMD ["uvicorn", "agentic_preview.main:app", "--host", "0.0.0.0", "--port", "5000"]
