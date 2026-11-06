# RepoSleuth

**A Django-based Static Code Analysis and Project Health Assessment Tool**

🌐 **Live Demo:** [https://reposleuth.onrender.com](https://reposleuth.onrender.com)

## About the Project

RepoSleuth is a web-based tool that analyzes software projects and provides insights into their structure, dependencies, potential code issues, and overall project health.

Users can upload a project as a ZIP file and view the analysis through a simple dashboard.

## Key Features

- **Project Upload:** Upload software projects using ZIP files.
- **Static Code Analysis:** Analyze Python source code using Python AST.
- **Issue Detection:** Identify potential code issues.
- **Dependency Analysis:** Display project dependencies and external libraries.
- **Project Structure:** View files, folders, and entry points.
- **Health Score:** Get an overall project health score.
- **Quick Demo:** Explore the tool using a sample project.
- **ZIP Security:** Protection against Zip Slip attacks and excessive archive extraction.

## Technology Stack

| Component     | Technology            |
| ------------- | --------------------- |
| Backend       | Python, Django        |
| Frontend      | HTML, CSS, JavaScript |
| Database      | SQLite, PostgreSQL    |
| Code Analysis | Python AST            |
| Deployment    | Render                |
| Static Files  | WhiteNoise            |

## How to Use

1. Open the RepoSleuth website.
2. Click **Quick Demo** to explore a sample analysis.
3. Click **Scan Project** to upload your own project ZIP file.
4. Wait for the analysis to complete.
5. Explore the project structure, detected issues, dependencies, and health score.

## Run Locally

Clone the repository:

```bash
git clone https://github.com/rm7104586-ux/RepoSleuth.git
cd RepoSleuth
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run database migrations:

```bash
python manage.py migrate
```

Start the development server:

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

## Deployment

RepoSleuth is deployed using Render.

**Live Website:** [https://reposleuth.onrender.com](https://reposleuth.onrender.com)

## Project Purpose

The purpose of RepoSleuth is to make software project inspection easier by providing a centralized view of code structure, potential issues, dependencies, and project health.
