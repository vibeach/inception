# Inception - Multi-Project Self-Improvement System

Inception is a meta-system that manages multiple web application projects, using Claude AI to automatically suggest and implement improvements. It can deploy on Render and manage the entire lifecycle of multiple projects.

## Overview

Inception ports the self-improvement logic from the telegram project and extends it to:
- ✅ Manage multiple projects simultaneously
- ✅ Track each project's git repo, local path, and Render deployment
- ✅ Generate AI-powered improvement suggestions per project
- ✅ Automatically implement approved improvements
- ✅ Full/partial auto-mode for continuous improvement
- 🚧 A/B test improvements with side-by-side comparison
- 🚧 Render integration for automated deployments
- 🚧 Web interface for managing all projects

## Current Status

### ✅ Completed Core Components

1. **Database Schema** (`database.py`)
   - Multi-project support with `projects` table
   - All incept tables now have `project_id` foreign keys
   - Complete CRUD operations for projects, requests, suggestions, improvements
   - A/B testing schema ready
   - System logging support

2. **Configuration** (`config.py`, `dynamic_config.py`)
   - Hot-reloadable prompts and settings
   - Per-project git/Render configuration
   - Environment variable support

3. **Incept Processor** (`incept_processor.py`)
   - Multi-project aware processor
   - Claude API integration with file manipulation tools
   - Automatic git commit and push per project
   - Project-specific working directories

4. **Incept+ Features**
   - **Suggester** (`incept_plus_suggester.py`): AI-powered suggestion generation per project
   - **Tracker** (`incept_plus_tracker.py`): Implementation tracking, rollback support
   - **Auto-Mode** (`incept_plus_auto.py`): Continuous autonomous improvement

### 🚧 To Be Built

1. **Render Integration Module**
   - Create/configure Render services programmatically
   - Deploy projects to Render
   - Manage render.yaml files
   - Link git repos to Render services

2. **Web Interface**
   - Dashboard for all projects
   - Per-project views (requests, suggestions, improvements)
   - Multi-project request submission
   - A/B test management UI

3. **A/B Testing**
   - Deploy variants with feature flags
   - Side-by-side comparison UI
   - Metrics tracking and winner selection

## Architecture

### Database Tables

**Projects**
- `id`, `name`, `description`, `repo_url`, `repo_branch`, `github_token`
- `local_path`, `render_service_id`, `render_service_url`
- `project_type`, `status`, `created_at`, `updated_at`

**Claude Requests** (per project)
- Improvement requests for specific projects
- Status tracking: pending → processing → completed/error
- Auto-push to git option

**Incept Suggestions** (per project)
- AI-generated improvement ideas
- Status: suggested → accepted → implementing → implemented
- Category, priority, effort estimation

**Incept Improvements** (per project)
- Tracks implemented changes
- Commit hashes for rollback
- Feature flags for A/B testing
- Enable/disable toggle

**A/B Tests** (per project)
- Control vs variant tracking
- Metrics and winner selection
- Side-by-side URLs

### Key Features

1. **Multi-Project Support**
   - Each project has its own local path and git repo
   - Project-specific settings and configurations
   - Isolated request/suggestion/improvement tracking

2. **AI-Powered Workflow**
   ```
   User → Request Improvement
     ↓
   Incept Processor (Claude API)
     ↓
   Claude reads files, makes changes using tools
     ↓
   Auto-commit to git
     ↓
   Auto-push triggers Render redeploy
   ```

3. **Incept+ Autonomous Mode**
   ```
   User sets direction (e.g., "improve performance")
     ↓
   Claude generates suggestions
     ↓
   User approves or auto-approves
     ↓
   Incept implements
     ↓
   Tracks commit, allows rollback
   ```

4. **A/B Testing (Planned)**
   ```
   Improvement implemented
     ↓
   Create test with control/variant commits
     ↓
   Deploy both versions
     ↓
   Compare side-by-side
     ↓
   Select winner or rollback
   ```

## Setup

### Prerequisites
- Python 3.10+
- Git
- Anthropic API key
- GitHub personal access token
- Render account (for deployments)

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export GITHUB_TOKEN="ghp_..."
export RENDER_API_KEY="rnd_..."
export DASHBOARD_PASSWORD="your-password"
export SECRET_KEY="random-secret-key"
```

3. Initialize database:
```python
python -c "import database; database.init_db()"
```

### Adding a Project

```python
import database

# Add a project
project_id = database.add_project(
    name="my-app",
    repo_url="https://github.com/user/my-app.git",
    description="My awesome app",
    repo_branch="main",
    github_token="ghp_...",
    local_path="/path/to/my-app",
    render_service_id="srv-...",
    project_type="Flask"
)
```

### Running the Processor

```bash
python incept_processor.py
```

The processor will:
1. Poll for pending requests every 5 seconds
2. Process them using Claude API
3. Make file changes using tools
4. Auto-commit and push to git
5. Trigger Render redeployment

### Running Auto-Mode

```bash
python incept_plus_auto.py
```

Or start a session from code:
```python
import database

session_id = database.start_incept_auto_session(
    project_id=1,
    direction="improve UI responsiveness",
    max_suggestions=10
)
```

## Configuration

### Dynamic Prompts (`/data/dynamic_config/prompts.json`)
- Edit system prompts without redeploying
- Hot-reloaded on each request
- Customize for different project types

### Per-Project Settings
- Mode: API (production) or CLI (dev)
- Model: claude-sonnet-4, claude-opus-4, etc.
- Auto-push: Enable/disable automatic git pushes
- Suggestion model for Incept+

## Tools Available to Claude

When processing requests, Claude has access to:

1. **read_file**: Read contents of any file in the project
2. **write_file**: Create or overwrite files
3. **edit_file**: Make targeted edits (find/replace)
4. **list_files**: Glob pattern file listing
5. **log_progress**: Log status updates

Example request:
```
Add a dark mode toggle to the settings page
```

Claude will:
1. Read relevant files (settings page, CSS, etc.)
2. Implement the toggle component
3. Update styles
4. Log progress
5. Commit and push changes

## Rollback System

Every improvement is tracked with:
- Commit hash
- Changed files list
- Implementation date
- Rollback instructions

To rollback:
```python
import incept_plus_tracker

success, message = incept_plus_tracker.rollback_improvement(improvement_id)
```

This will:
1. Create a git revert commit
2. Disable the improvement in the DB
3. Push the revert (triggers redeploy)

## Next Steps

1. **Build Render Integration**
   - Create module to interact with Render API
   - Auto-create services for new projects
   - Generate and manage render.yaml files

2. **Build Web Interface**
   - Multi-project dashboard
   - Request submission per project
   - Suggestion review and approval
   - Improvement tracking
   - A/B test management

3. **Implement A/B Testing**
   - Deploy control and variant simultaneously
   - Side-by-side iframe comparison
   - Metrics collection
   - Winner selection workflow

4. **Deploy Inception on Render**
   - Create render.yaml for inception itself
   - Set up persistent disk for database
   - Configure environment variables
   - Inception manages itself!

## Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...          # Claude API key
DASHBOARD_PASSWORD=xxx                 # Web UI password
SECRET_KEY=random-string               # Flask secret

# Optional (can be set per-project in DB)
GITHUB_TOKEN=ghp_...                   # Default GitHub token
RENDER_API_KEY=rnd_...                 # Render API key
RENDER_OWNER_ID=usr-...                # Your Render user/team ID
DATA_DIR=/data                         # Persistent data directory
EMBEDDED_PROCESSOR=1                   # Auto-start processor with web app
```

## Project Structure

```
inception/
├── config.py                    # Main configuration
├── dynamic_config.py            # Hot-reloadable config
├── database.py                  # Multi-project database
├── incept_processor.py          # Request processor
├── incept_plus_suggester.py     # AI suggestion generator
├── incept_plus_tracker.py       # Implementation tracker
├── incept_plus_auto.py          # Auto-mode worker
├── requirements.txt             # Python dependencies
└── README.md                    # This file

To be created:
├── render_integration.py        # Render API wrapper
├── dashboard.py                 # Flask web interface
├── templates/                   # Jinja2 templates
│   ├── base.html
│   ├── projects.html
│   ├── project_detail.html
│   ├── incept.html
│   └── incept_plus.html
├── render.yaml                  # Render deployment config
└── start.sh                     # Startup script
```

## License

MIT
