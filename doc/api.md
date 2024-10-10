# Agentic Platform API Documentation

Last updated: [Current Date]

## Introduction

The Agentic Platform API provides a comprehensive set of endpoints for interacting with the Agentic Preview system. This API allows developers to manage projects, users, deployments, and utilize AI-assisted coding features. The API is built using FastAPI and follows RESTful principles.

## Base URL

All API requests should be made to:

```
http://localhost:8000
```

Replace `localhost:8000` with your actual server address and port if different.

## Authentication

Currently, the API does not implement authentication. However, it's strongly recommended to implement proper authentication and authorization mechanisms before deploying to a production environment.

## API Endpoints

### Agentic Editor

#### 1. Run Aider for AI-Assisted Coding

- **Endpoint**: `/run-aider`
- **Method**: POST
- **Description**: Executes the Aider AI assistant for code generation, refactoring, or analysis.
- **Request Body**:
  ```json
  {
    "chat_mode": "code",
    "edit_format": "diff",
    "model": "gpt-4",
    "prompt": "string",
    "files": ["string"]
  }
  ```
- **Response**:
  ```json
  {
    "output": "string",
    "changes": [
      {
        "file": "string",
        "diff": "string"
      }
    ]
  }
  ```
- **Example**:
  ```bash
  curl -X POST "http://localhost:8000/run-aider" \
    -H "Content-Type: application/json" \
    -d '{
      "chat_mode": "code",
      "edit_format": "diff",
      "model": "gpt-4",
      "prompt": "Optimize the database query in main.py",
      "files": ["main.py", "database.py"]
    }'
  ```

#### 2. List All Projects

- **Endpoint**: `/projects`
- **Method**: GET
- **Description**: Retrieves a list of all projects in the system.
- **Response**:
  ```json
  [
    {
      "id": "integer",
      "name": "string",
      "description": "string",
      "repository_url": "string",
      "created_at": "datetime",
      "updated_at": "datetime"
    }
  ]
  ```
- **Example**:
  ```bash
  curl "http://localhost:8000/projects"
  ```

#### 3. List All Users

- **Endpoint**: `/users`
- **Method**: GET
- **Description**: Retrieves a list of all users in the system.
- **Response**:
  ```json
  [
    {
      "id": "integer",
      "username": "string",
      "email": "string",
      "created_at": "datetime"
    }
  ]
  ```
- **Example**:
  ```bash
  curl "http://localhost:8000/users"
  ```

### Agentic Preview

#### 1. Deploy an Application

- **Endpoint**: `/deploy`
- **Method**: POST
- **Description**: Deploys an application to Fly.io based on the provided GitHub repository.
- **Request Body**:
  ```json
  {
    "repo": "string",
    "branch": "string",
    "args": ["string"],
    "app_name": "string",
    "memory": "integer"
  }
  ```
- **Response**:
  ```json
  {
    "status": "string",
    "message": "string",
    "app_url": "string"
  }
  ```
- **Example**:
  ```bash
  curl -X POST "http://localhost:8000/deploy" \
    -H "Content-Type: application/json" \
    -d '{
      "repo": "username/repository",
      "branch": "main",
      "args": ["--build-arg", "ENV=production"],
      "app_name": "my-awesome-app",
      "memory": 512
    }'
  ```

#### 2. Check Deployment Status

- **Endpoint**: `/status/{app_name}`
- **Method**: GET
- **Description**: Retrieves the current status of a deployed application.
- **Parameters**:
  - `app_name` (path): The name of the deployed application
- **Response**:
  ```json
  {
    "status": "string",
    "details": "string"
  }
  ```
- **Example**:
  ```bash
  curl "http://localhost:8000/status/my-awesome-app"
  ```

#### 3. Stream Application Logs

- **Endpoint**: `/logs/{app_name}`
- **Method**: GET
- **Description**: Streams the logs of a deployed application in real-time.
- **Parameters**:
  - `app_name` (path): The name of the deployed application
- **Response**: Server-Sent Events (SSE) stream
- **Example**:
  ```bash
  curl "http://localhost:8000/logs/my-awesome-app"
  ```

### Project Management

#### 1. Create a New Project

- **Endpoint**: `/projects`
- **Method**: POST
- **Description**: Creates a new project in the system.
- **Request Body**:
  ```json
  {
    "name": "string",
    "description": "string",
    "repository_url": "string"
  }
  ```
- **Response**:
  ```json
  {
    "id": "integer",
    "name": "string",
    "description": "string",
    "repository_url": "string",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
  ```
- **Example**:
  ```bash
  curl -X POST "http://localhost:8000/projects" \
    -H "Content-Type: application/json" \
    -d '{
      "name": "My Awesome Project",
      "description": "A revolutionary web application",
      "repository_url": "https://github.com/username/awesome-project"
    }'
  ```

#### 2. Update Project Details

- **Endpoint**: `/projects/{project_id}`
- **Method**: PUT
- **Description**: Updates the details of an existing project.
- **Parameters**:
  - `project_id` (path): The ID of the project to update
- **Request Body**:
  ```json
  {
    "name": "string",
    "description": "string",
    "repository_url": "string"
  }
  ```
- **Response**:
  ```json
  {
    "id": "integer",
    "name": "string",
    "description": "string",
    "repository_url": "string",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
  ```
- **Example**:
  ```bash
  curl -X PUT "http://localhost:8000/projects/1" \
    -H "Content-Type: application/json" \
    -d '{
      "description": "An even more revolutionary web application"
    }'
  ```

#### 3. Delete a Project

- **Endpoint**: `/projects/{project_id}`
- **Method**: DELETE
- **Description**: Deletes a project from the system.
- **Parameters**:
  - `project_id` (path): The ID of the project to delete
- **Response**:
  ```json
  {
    "message": "string"
  }
  ```
- **Example**:
  ```bash
  curl -X DELETE "http://localhost:8000/projects/1"
  ```

### User Management

#### 1. Create a New User

- **Endpoint**: `/users`
- **Method**: POST
- **Description**: Creates a new user in the system.
- **Request Body**:
  ```json
  {
    "username": "string",
    "email": "string",
    "password": "string"
  }
  ```
- **Response**:
  ```json
  {
    "id": "integer",
    "username": "string",
    "email": "string",
    "created_at": "datetime"
  }
  ```
- **Example**:
  ```bash
  curl -X POST "http://localhost:8000/users" \
    -H "Content-Type: application/json" \
    -d '{
      "username": "johndoe",
      "email": "john@example.com",
      "password": "securepassword123"
    }'
  ```

#### 2. Update User Details

- **Endpoint**: `/users/{user_id}`
- **Method**: PUT
- **Description**: Updates the details of an existing user.
- **Parameters**:
  - `user_id` (path): The ID of the user to update
- **Request Body**:
  ```json
  {
    "username": "string",
    "email": "string"
  }
  ```
- **Response**:
  ```json
  {
    "id": "integer",
    "username": "string",
    "email": "string",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
  ```
- **Example**:
  ```bash
  curl -X PUT "http://localhost:8000/users/1" \
    -H "Content-Type: application/json" \
    -d '{
      "email": "newemail@example.com"
    }'
  ```

#### 3. Delete a User

- **Endpoint**: `/users/{user_id}`
- **Method**: DELETE
- **Description**: Deletes a user from the system.
- **Parameters**:
  - `user_id` (path): The ID of the user to delete
- **Response**:
  ```json
  {
    "message": "string"
  }
  ```
- **Example**:
  ```bash
  curl -X DELETE "http://localhost:8000/users/1"
  ```

## Error Handling

The API uses standard HTTP status codes to indicate the success or failure of requests. In case of an error, the response will include a JSON object with an `error` field containing a description of the error.

Example error response:

```json
{
  "error": "Project not found"
}
```

Common status codes:

- 200: OK - The request was successful
- 201: Created - A new resource was successfully created
- 400: Bad Request - The request was invalid or cannot be served
- 404: Not Found - The requested resource does not exist
- 500: Internal Server Error - The server encountered an unexpected condition

## Rate Limiting

Currently, there is no rate limiting implemented on the API. However, it's recommended to implement rate limiting in a production environment to prevent abuse and ensure fair usage of resources.

## Versioning

The current version of the API is v1. All endpoints should be prefixed with `/api/v1/` in a production environment to allow for future versioning.

## Best Practices and Guidelines

For detailed best practices and guidelines on using the Agentic Platform API, please refer to our [API Best Practices and Guidelines](./api_best_practices.md) document.

## Conclusion

This API documentation provides a comprehensive overview of the endpoints available in the Agentic Platform. For any additional information, best practices, or support, please refer to the main README.md file, the API Best Practices and Guidelines document, or contact the development team.
