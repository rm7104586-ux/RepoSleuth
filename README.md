# RepoSleuth – Smart Codebase Analyzer and Project Explorer

> **Academic Project**: Third-Year Computer Science & Engineering (CSE)  
> **Topic**: Software Engineering, Code Comprehension & Static Code Analysis  
> **Technology Stack**: Python, Django, SQLite, Python AST, ReportLab, HTML5, CSS3, JavaScript, Chart.js, Vis-Network

---

## 📌 Project Overview

**RepoSleuth** is a developer web application built to inspect and understand software projects without executing untrusted source code. By leveraging Python's standard **Abstract Syntax Tree (`ast`)** module and safe archive extraction routines, RepoSleuth performs in-depth static analysis on uploaded ZIP archives to map directory trees, trace module import dependencies, detect program entry points, identify code quality issues, and generate academic-grade PDF reports.

---

## 🚀 Core Features

### 1. Modern Developer Dashboard
- Real-time aggregate statistics: Total projects scanned, total files, directories, lines of code, and issues detected.
- Interactive **Languages Breakdown Chart** (powered by Chart.js) visualizing codebase composition by file extensions.
- Recent analysis history table with status badges and quick links.

### 2. Secure Project Upload & Sandboxing
- Drag-and-drop file upload supporting `.zip` archives.
- **Security Guardrails**:
  - **Path Traversal Protection**: Defends against "Zip Slip" directory traversal attacks by validating resolved canonical paths before extraction.
  - **Decompression Bomb Protection**: Enforces uncompressed file size limits (max 100MB) and file count caps (max 5,000 files).
  - **Zero Execution Policy**: User code is never executed or dynamically imported; analysis is 100% static.

### 3. Interactive File Explorer
- Hierarchical, collapsible directory tree displaying folders, files, file sizes, and lines of code.
- Integrated **Safe Code Viewer**: Click any file to preview source code line-by-line with syntax highlighting and line numbers.

### 4. AST Dependency Analyzer
- Parses Python `import` and `from ... import` statements using the Python `ast` module.
- Identifies internal project relationships vs. standard library and external third-party dependencies.
- **Confirmed vs. Estimated Classification**:
  - **Confirmed**: Exact matching module file found within the project repository (represented with solid green arrows).
  - **Estimated**: Inferred or relative package references that cannot be strictly verified on disk (represented with dashed amber arrows).
- Interactive **Network Graph** (Vis-Network) with pan, zoom, layout stabilization, and node inspection.
- Catalog of detected third-party packages (e.g., Flask, Requests, Django) and referencing files.

### 5. Application Entry Point Detector
- Scans files for known startup conventions (`manage.py`, `main.py`, `app.py`, `run.py`, `wsgi.py`, `asgi.py`, `cli.py`).
- Detects `if __name__ == '__main__':` execution guards via AST node inspection.
- Identifies framework factories (Flask `Flask(__name__)`, FastAPI, Click CLI, Argparse).
- Provides clear pedagogical explanations for why each file is flagged as an entry point with line references.

### 6. Code Issue & Smell Detector
- **Syntax Errors**: Catches `SyntaxError` via AST parsing with exact line number, column offset, and offending snippet.
- **TODO / FIXME Tags**: Regex scanner that flags technical debt items with line numbers.
- **Empty Python Files**: Detects 0-byte or whitespace-only Python files (differentiating standard `__init__.py` markers from code files).
- **Oversized Source Files**: Flags modules exceeding 500 lines of code to encourage modular decomposition.
- **Wildcard Imports**: Detects `from module import *` anti-patterns.
- **Codebase Health Score**: Calculates an overall health index from 0 to 100.

### 7. Academic PDF Analysis Report
- Compiles a multi-page, publication-ready PDF report using **ReportLab**.
- Includes project metadata, metrics summary, language distribution, entry points table, categorized code issues, and external dependencies.
- One-click export directly from the browser.

### 8. Analysis History & Project Management
- Persistent SQLite database storing all previous scans.
- Search filter by project name.
- Safe deletion feature that purges database records and removes uploaded archives and extracted files from disk.

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Backend Framework** | Django 6.1 (Python 3.10+) |
| **Code Analysis Engine** | Python Standard Library `ast`, `zipfile`, `pathlib`, `re` |
| **PDF Generation** | ReportLab 5.0+ |
| **Database** | SQLite 3 |
| **Frontend Styling** | Custom Developer Dark Theme (`#090d16`, `#111827`, Purple & Blue accents), Bootstrap 5 |
| **Icons & Typography** | Bootstrap Icons, Inter & JetBrains Mono Fonts |
| **Visualizations** | Chart.js (Doughnut charts), Vis-Network (Interactive physics-based graph) |

---

## 💻 Exact Windows Setup & Run Instructions

Open **PowerShell** or **Command Prompt** in the project directory (`c:\Users\rm710\Desktop\RepoSleuth`):

### 1. Verify Python Installation
```powershell
python --version
```
*(Requires Python 3.10 or higher. Python 3.13 was verified during development).*

### 2. Apply Database Migrations
Initialize the SQLite database schema:
```powershell
python manage.py migrate
```

### 3. Load Sample Demo Project (Optional but Recommended)
Populate the database with a pre-packaged sample project (`demo_library_app.zip`) containing realistic entry points, dependencies, TODO comments, and intentional syntax test cases:
```powershell
python manage.py seed_demo
```

### 4. Run Automated Test Suite
Verify that all 19 unit and integration tests pass:
```powershell
python manage.py test analyzer
```

### 5. Start the Development Server
```powershell
python manage.py runserver 127.0.0.1:8000
```

### 6. Access RepoSleuth in your Browser
Open your web browser and navigate to:
```
http://127.0.0.1:8000/
```

---

## 📁 Project Directory Structure

```
RepoSleuth/
├── manage.py                          # Django management entry point
├── build.sh                           # Render production build script
├── requirements.txt                   # Production Python dependencies
├── .env.example                       # Sample environment variables configuration
├── .gitignore                         # Git exclusion rules
├── db.sqlite3                         # Local SQLite database (ignored in git)
├── README.md                          # Project documentation
│
├── reposleuth/                        # Django Project Configuration
│   ├── settings.py                    # Project settings (WhiteNoise, PostgreSQL/SQLite, Render)
│   ├── urls.py                        # Root URL routing & media serving
│   ├── wsgi.py                        # WSGI entry point (Gunicorn target)
│   └── asgi.py                        # ASGI entry point
│
├── analyzer/                          # Core RepoSleuth Application
│   ├── models.py                      # Project & ProjectAnalysis database models
│   ├── views.py                       # View controllers (Dashboard, Explorer, Graph, PDF, etc.)
│   ├── urls.py                        # Application URL patterns
│   ├── forms.py                       # Upload form with archive validation
│   ├── tests.py                       # Complete automated test suite (19 test cases)
│   │
│   ├── services/                      # Modular Static Analysis Engine
│   │   ├── zip_extractor.py           # Safe ZIP extraction & Zip-Slip defense
│   │   ├── file_explorer.py           # Directory hierarchy, LOC counting & safe file viewer
│   │   ├── ast_analyzer.py            # AST module import parser & dependency mapping
│   │   ├── entrypoint_detector.py     # Framework & __main__ entry point detector
│   │   ├── issue_detector.py          # Syntax error, TODO, empty & large file detector
│   │   ├── pdf_generator.py           # ReportLab PDF report builder
│   │   └── project_service.py         # Pipeline coordinator
│   │
│   ├── management/commands/
│   │   └── seed_demo.py               # Management command to load sample demo project
│   │
│   └── templates/analyzer/            # Dark-Themed Developer Templates
│       ├── base.html                  # Base layout with sidebar and breadcrumbs
│       ├── dashboard.html             # Main dashboard with stat cards & charts
│       ├── upload.html                # ZIP upload with drag-and-drop
│       ├── project_overview.html      # Project metrics & investigation hubs
│       ├── file_explorer.html         # Tree view & code viewer with line numbers
│       ├── dependency_analyzer.html   # Vis.js interactive dependency graph
│       ├── entry_points.html          # Entry point cards & explanations
│       ├── code_issues.html           # Filterable code smells & syntax errors
│       ├── history.html               # Scan history table & search
│       └── project_confirm_delete.html# Delete confirmation modal
│
├── static/                            # Static Assets
│   └── css/
│       └── style.css                  # Custom Developer Dark Theme (Purple/Blue accents)
│
├── media/                             # Storage for Uploaded Archives & Extracted Projects
│   ├── uploads/                       # ZIP storage (.gitkeep)
│   └── extracted/                     # Extracted codebase directories (.gitkeep)
│
└── sample_projects/                   # Bundled Sample Codebases
    ├── create_sample_zip.py           # Script to generate demo archive
    └── demo_library_app.zip           # Sample Python project for instant testing
```

---

## 🌐 Deploying on Render (Free Tier Step-by-Step)

RepoSleuth is pre-configured with `build.sh`, `WhiteNoise`, `Gunicorn`, and automatic PostgreSQL integration for Render.

### Step 1: Push Codebase to GitHub
Run the following commands in PowerShell from the project folder:
```powershell
git init
git add .
git commit -m "Initial commit: RepoSleuth Codebase Analyzer"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo-name>.git
git push -u origin main
```

### Step 2: Create a PostgreSQL Database on Render
1. Log in to your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** > **PostgreSQL**.
3. Name it `reposleuth-db`, select the **Free** tier, and click **Create Database**.
4. Once created, copy the **Internal Database URL** (e.g. `postgresql://...`).

### Step 3: Create a Web Service on Render
1. In the Render Dashboard, click **New +** > **Web Service**.
2. Connect your GitHub repository.
3. Configure the settings:
   - **Name**: `reposleuth`
   - **Region**: Closest to you (e.g., Singapore, Frankfurt, Oregon)
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn reposleuth.wsgi:application`
   - **Instance Type**: `Free`

### Step 4: Add Environment Variables
Under the **Environment** tab of your Web Service, add:
| Key | Value | Description |
|---|---|---|
| `SECRET_KEY` | *(Generate a 50+ char random string)* | Production Django Secret Key |
| `DEBUG` | `False` | Disables debug mode in production |
| `DATABASE_URL` | *(Paste Internal Database URL from Step 2)* | PostgreSQL database connection string |
| `PYTHON_VERSION` | `3.13.0` | Python version for Render runtime |

Click **Create Web Service**. Render will run `build.sh`, run migrations, collect static files with WhiteNoise, seed the demo library project, and boot Gunicorn!

---

## ⚠️ Storage & Free-Tier Limitations on Render

> [!WARNING]
> - **Ephemeral Filesystem on Free Tier**: Render's free Web Services run inside temporary container dynos. If the service is inactive for 15 minutes or redeployed, files written to disk in `media/uploads/` and `media/extracted/` are cleared.
> - **What Persists**: All analyzed project metrics, file counts, LOC, AST dependency graphs, detected issues, and entry points are stored in the PostgreSQL database and **persist permanently**!
> - **Source Code Viewer**: The interactive file viewer reads raw files from the extracted directory. If a project was analyzed before an instance spin-down, the summary reports and issue metrics remain viewable, but previewing file lines may require re-uploading the project ZIP.
> - **Production Recommendation**: For permanent raw file storage across dyno restarts, attach a [Render Persistent Disk](https://render.com/docs/disks) (available on paid tiers) mounted to `/opt/render/project/src/media`, or integrate cloud object storage (e.g., AWS S3 or Cloudinary) via `django-storages`.


---

## 🧪 Testing with Your Own Projects

1. Compress any Python codebase into a standard `.zip` file.
2. In RepoSleuth, click **"Upload Project"** or **"Scan Project"** in the top navigation bar.
3. Drag and drop the `.zip` archive or select it via the file browser.
4. Click **"Start Analysis"**.
5. RepoSleuth will safely extract the repository, run the AST analyzer, and display the project overview dashboard in seconds.
6. Click **"Export PDF Report"** to download a formatted analysis document.
