# Inception - Quick Start Guide

## First Time Setup

### 1. Run Interactive Setup

This will prompt you for all required environment variables and create a `.env` file:

```bash
python3 setup_env.py
```

You'll be asked for:
- **DASHBOARD_PASSWORD** - Password for web interface
- **SECRET_KEY** - Auto-generated session key (or provide your own)
- **ANTHROPIC_API_KEY** - Claude API key (sk-ant-api03-...)
- **CLAUDE_CODE_OAUTH_TOKEN** - Optional Claude OAuth token
- **GITHUB_TOKEN** - GitHub personal access token (ghp_...)
- **RENDER_API_KEY** - Render API key (rnd_...)
- **RENDER_OWNER_ID** - Render owner/team ID (tea-... or usr-...)
- **DATA_DIR** - Optional data directory (defaults to current dir)

The script will:
- Create `.env` file with your variables
- Optionally sync variables to your Render services
- Show next steps

### 2. Start the Local Server

Simply run:

```bash
./start_local.sh
```

This script will:
- Check if `.env` exists (run setup if not)
- Load environment variables
- Install Python dependencies if needed
- Initialize the database
- Start the Flask dashboard on http://localhost:5000

**Or start manually:**

```bash
source .env
python3 dashboard.py
```

## Syncing to Render

To sync your local `.env` variables to Render services:

```bash
python3 sync_to_render.py
```

This will:
- Load variables from `.env`
- Show all projects with Render service IDs
- Ask for confirmation
- Sync variables to each Render service
- Optionally trigger deploys

## Daily Usage

### Start the dashboard:
```bash
./start_local.sh
```

### Access the dashboard:
Open http://localhost:5000 in your browser

### Stop the server:
Press `Ctrl+C` in the terminal

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Claude API key | `sk-ant-api03-...` |
| `GITHUB_TOKEN` | GitHub personal access token | `ghp_...` |
| `RENDER_API_KEY` | Render API key | `rnd_...` |
| `RENDER_OWNER_ID` | Render owner/team ID | `tea-...` or `usr-...` |
| `DASHBOARD_PASSWORD` | Web UI password | Any secure password |
| `SECRET_KEY` | Flask session key | Random string (auto-generated) |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CLAUDE_CODE_OAUTH_TOKEN` | Claude OAuth token | None |
| `DATA_DIR` | Data directory path | Current directory |
| `DASHBOARD_HOST` | Dashboard host | `0.0.0.0` |
| `DASHBOARD_PORT` | Dashboard port | `5000` |
| `EMBEDDED_PROCESSOR` | Auto-start processor | `1` (enabled) |

## Project Structure

```
inception/
├── setup_env.py           # Interactive environment setup
├── start_local.sh         # Local startup script
├── sync_to_render.py      # Sync vars to Render
├── dashboard.py           # Web interface
├── database.py            # Database operations
├── incept_processor.py    # Request processor
├── render_manager.py      # Render API client
├── .env                   # Your environment variables (not in git)
├── .env.example          # Example template
└── inception.db          # SQLite database (not in git)
```

## Useful Commands

### Check database projects:
```bash
sqlite3 inception.db "SELECT id, name, render_service_id FROM projects;"
```

### Add a project manually:
```python
import database
database.init_db()
database.add_project(
    name="my-app",
    repo_url="https://github.com/user/my-app",
    description="My awesome app",
    repo_branch="main",
    github_token="ghp_...",
    local_path="/path/to/my-app",
    render_service_id="srv-...",
    project_type="Flask"
)
```

### Check Render service info:
```python
import render_manager
rm = render_manager.get_render_manager()
success, info = rm.get_service("srv-...")
print(info)
```

### Get Render environment variables:
```python
import render_manager
rm = render_manager.get_render_manager()
success, env_vars = rm.get_env_vars("srv-...")
for var in env_vars:
    print(f"{var['key']} = {var['value']}")
```

## Troubleshooting

### "No .env file found"
Run `python3 setup_env.py` to create it.

### "Missing required environment variables"
Check your `.env` file has all required variables listed above.

### "Database not initialized"
The startup script handles this, but you can manually run:
```bash
python3 -c "import database; database.init_db()"
```

### "Port 5000 already in use"
Set a different port:
```bash
export DASHBOARD_PORT=8000
./start_local.sh
```

### "Cannot connect to Render API"
- Verify your `RENDER_API_KEY` is correct
- Check you have network connectivity
- Ensure the Render service ID is correct

## Next Steps

1. **Add Projects** - Use the web interface to add your projects
2. **Configure Git Repos** - Link each project to its GitHub repository
3. **Link Render Services** - Add Render service IDs for deployments
4. **Submit Requests** - Start requesting improvements via Claude
5. **Enable Auto-Mode** - Let Claude autonomously suggest improvements

## Support

For issues or questions:
- Check the main [README.md](README.md) for detailed documentation
- Review [RENDER_SETUP.md](RENDER_SETUP.md) for Render deployment info
- Check the logs in `processor.log` and `logs/` directory
