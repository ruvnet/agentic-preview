# Agentic Preview

Welcome to Agentic Preview, a cutting-edge, asynchronous FastAPI backend service that revolutionizes the way developers create, manage, and deploy applications. By seamlessly integrating the powerful capabilities of Agentic Editor and Agentic Preview into a unified Agentic Platform, we offer a comprehensive solution for modern software development workflows.

## Introduction

In today's fast-paced software development landscape, efficiency and automation are key. Agentic Preview addresses these needs by providing a robust platform that combines AI-assisted coding, streamlined project management, and effortless deployment capabilities. Our solution leverages the power of Fly.io for deployments and integrates advanced AI technologies to assist in coding tasks, making it an indispensable tool for developers of all levels.

Agentic Preview is designed to be your all-in-one solution for:
- Rapid prototyping and development
- Efficient project management
- Seamless deployment and preview of applications
- AI-assisted code generation and refactoring

Whether you're a solo developer working on a passion project or part of a large team tackling complex applications, Agentic Preview has the tools and features to streamline your workflow and boost productivity.

## Features

Agentic Preview offers a rich set of features designed to enhance every aspect of your development process:

1. **Unified Agentic Platform**
   - Seamlessly integrates Agentic Editor and Agentic Preview functionalities
   - Provides a cohesive environment for coding, managing, and deploying projects

2. **AI-Assisted Coding with Aider**
   - Harnesses the power of advanced language models for intelligent code editing
   - Offers code generation, refactoring, and optimization suggestions
   - Supports natural language prompts for code-related tasks

3. **Asynchronous Deployments**
   - Rapidly deploy GitHub repositories to Fly.io
   - Ensures non-blocking operations for improved performance and responsiveness

4. **Comprehensive Project Management**
   - Create, update, and manage multiple projects effortlessly
   - Track project status, history, and associated resources

5. **User Management System**
   - Manage user accounts and permissions
   - Associate users with specific projects for collaborative development

6. **Intelligent Resource Management**
   - Automatically cleans up resources after usage
   - Implements smart allocation and deallocation of computing resources

7. **Customizable Deployments**
   - Supports custom deployment arguments and configurations
   - Allows fine-tuning of deployment processes to meet specific project needs

8. **Real-time Logging and Monitoring**
   - Stream deployment and application logs in real-time
   - Monitor application performance and status effortlessly

9. **Robust Database Integration**
   - Utilizes SQLAlchemy for efficient and reliable data management
   - Supports complex queries and data operations

10. **RESTful API**
    - Well-documented API endpoints for easy integration with other tools and services
    - Follows best practices for API design and implementation

11. **Containerization Support**
    - Includes Dockerfile for easy containerization of applications
    - Ensures consistency across different development and deployment environments

## Installation

Before diving into the world of Agentic Preview, let's ensure you have everything set up correctly. Follow these comprehensive installation steps to get started:

### Prerequisites

1. **Python**: Agentic Preview requires Python 3.8 or higher. You can download it from [python.org](https://www.python.org/downloads/).

2. **Poetry**: We use Poetry for dependency management. Install it by following the instructions at [python-poetry.org](https://python-poetry.org/docs/#installation).

3. **Fly.io CLI**: You'll need the Fly.io command-line tool (flyctl) for deployments. Install it using:
   
   For macOS and Linux:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```
   
   For Windows (using PowerShell):
   ```powershell
   iwr https://fly.io/install.ps1 -useb | iex
   ```

4. **Git**: Ensure you have Git installed on your system. Download it from [git-scm.com](https://git-scm.com/downloads).

### Installation Steps

1. **Clone the Repository**:
   Open your terminal and run:
   ```bash
   git clone https://github.com/ruvnet/agentic-preview.git
   cd agentic-preview
   ```

2. **Install Dependencies**:
   Use Poetry to install the project dependencies:
   ```bash
   poetry install
   ```

3. **Authenticate with Fly.io**:
   Set up your Fly.io account:
   ```bash
   flyctl auth login
   ```

4. **Set Up Environment Variables**:
   Create a `.env` file in the root directory with the following content:
   ```
   DATABASE_URL=sqlite:///./agentic_platform.db
   OPENAI_API_KEY=your_openai_api_key
   FLY_API_TOKEN=your_fly_api_token
   ```
   Replace `your_openai_api_key` and `your_fly_api_token` with your actual API keys.

5. **Initialize the Database**:
   Run the database initialization script:
   ```bash
   poetry run python agentic_platform/init_db.py
   ```

6. **Verify Installation**:
   Ensure everything is set up correctly by running:
   ```bash
   poetry run python -c "from agentic_platform import __version__; print(f'Agentic Preview version: {__version__}')"
   ```

Congratulations! You've successfully installed Agentic Preview and are ready to start using its powerful features.

## Usage Guide

Now that you have Agentic Preview installed, let's explore how to use its various features and capabilities.

### Starting the Application

1. **Activate the Virtual Environment**:
   ```bash
   poetry shell
   ```

2. **Run the Application**:
   ```bash
   uvicorn agentic_platform.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   The application will start, and you can access it at `http://localhost:8000`.

### API Endpoints

Agentic Preview offers a rich set of API endpoints to interact with its various features. Here's an overview of the main endpoints:

#### Agentic Editor Endpoints

1. **Run Aider for AI-Assisted Coding**:
   - **POST** `/run-aider`
   - Example usage:
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

2. **List All Projects**:
   - **GET** `/projects`
   - Example usage:
     ```bash
     curl "http://localhost:8000/projects"
     ```

3. **List All Users**:
   - **GET** `/users`
   - Example usage:
     ```bash
     curl "http://localhost:8000/users"
     ```

#### Agentic Preview Endpoints

1. **Deploy an Application**:
   - **POST** `/deploy`
   - Example usage:
     ```bash
     curl -X POST "http://localhost:8000/deploy" \
       -H "Content-Type: application/json" \
       -d '{
         "repo": "username/repository",
         "branch": "main",
         "args": ["--build-arg", "ENV=production"]
       }'
     ```

2. **Check Deployment Status**:
   - **GET** `/status/{app_name}`
   - Example usage:
     ```bash
     curl "http://localhost:8000/status/my-awesome-app"
     ```

3. **Stream Application Logs**:
   - **GET** `/logs/{app_name}`
   - Example usage:
     ```bash
     curl "http://localhost:8000/logs/my-awesome-app"
     ```

### Working with Projects

1. **Create a New Project**:
   ```bash
   curl -X POST "http://localhost:8000/projects" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "My Awesome Project",
       "description": "A revolutionary web application",
       "repository_url": "https://github.com/username/awesome-project"
     }'
   ```

2. **Update Project Details**:
   ```bash
   curl -X PUT "http://localhost:8000/projects/1" \
     -H "Content-Type: application/json" \
     -d '{
       "description": "An even more revolutionary web application"
     }'
   ```

3. **Delete a Project**:
   ```bash
   curl -X DELETE "http://localhost:8000/projects/1"
   ```

### AI-Assisted Coding with Aider

1. **Generate Code Based on a Prompt**:
   ```bash
   curl -X POST "http://localhost:8000/run-aider" \
     -H "Content-Type: application/json" \
     -d '{
       "chat_mode": "code",
       "edit_format": "diff",
       "model": "gpt-4",
       "prompt": "Create a Python function to calculate Fibonacci numbers",
       "files": ["math_utils.py"]
     }'
   ```

2. **Refactor Existing Code**:
   ```bash
   curl -X POST "http://localhost:8000/run-aider" \
     -H "Content-Type: application/json" \
     -d '{
       "chat_mode": "code",
       "edit_format": "diff",
       "model": "gpt-4",
       "prompt": "Refactor the main() function to improve readability",
       "files": ["main.py"]
     }'
   ```

## Configuration

Agentic Preview offers various configuration options to tailor the platform to your specific needs:

1. **Application-wide Settings**:
   Modify `agentic_platform/config.py` to adjust global settings such as database URLs, API keys, and default values.

2. **Deployment Settings**:
   Fine-tune deployment configurations in `agentic_platform/api/deploy.py`. This includes settings for Fly.io deployments and resource allocation.

3. **Aider Behavior**:
   Customize the AI-assisted coding features by modifying `agentic_platform/api/aider.py`. Adjust model parameters, prompts, and output formats.

4. **Database Models**:
   If you need to extend or modify the data structure, update the models in `agentic_platform/models.py`.

5. **API Endpoints**:
   Add or modify API endpoints in `agentic_platform/main.py` to extend the platform's functionality.

## Contributing

We welcome contributions from the community! If you'd like to contribute to Agentic Preview, please follow these steps:

1. Fork the repository on GitHub.
2. Create a new branch for your feature or bug fix.
3. Write your code and add tests if applicable.
4. Ensure all tests pass by running `pytest`.
5. Submit a pull request with a clear description of your changes.

For more detailed information on contributing, please read our [CONTRIBUTING.md](CONTRIBUTING.md) file.

## License

Agentic Preview is open-source software licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

## Support and Community

If you encounter any issues or have questions about Agentic Preview, please don't hesitate to:

- Open an issue on our [GitHub repository](https://github.com/ruvnet/agentic-preview/issues).
- Join our community forum at [community.agentic-preview.com](https://community.agentic-preview.com).
- Follow us on Twitter [@AgenticPreview](https://twitter.com/AgenticPreview) for the latest updates and announcements.

We're excited to see what you'll build with Agentic Preview! Happy coding!
