# Render Deployment Setup

## Auto-Import Projects

To auto-import your projects on Render, add these environment variables in your Render dashboard:

### 1. Telegram Project

**Environment Variable Name:** `PROJECT_TELEGRAM_CONFIG`

**Value:**
```json
{"repo_url":"https://github.com/vibeach/telegram-monitor.git","repo_branch":"main","description":"Telegram monitoring dashboard with AI assistant (Claude) for analyzing conversations, Incept+ for self-improvement, and integration with Control Room for health/mood tracking","render_service_id":"srv-d57acqjuibrs73a25p60","render_service_url":"https://telegram-monitor.onrender.com","project_type":"Flask"}
```

### 2. ControlRoom (QuantumLab) Project

**Environment Variable Name:** `PROJECT_CONTROLROOM_CONFIG`

**Value:**
```json
{"repo_url":"https://github.com/vibeach/quantumLab.git","repo_branch":"main","description":"Personal health, mood, social, and intimate tracking dashboard with REST API, webhooks, and comprehensive analytics. Exposes data to Telegram dashboard via API.","render_service_url":"https://quantumlab-73wx.onrender.com","project_type":"Node.js"}
```

## How to Add Environment Variables on Render

1. Go to https://dashboard.render.com/web/srv-d5b9dkggjchc73brik10
2. Click "Environment" in the left sidebar
3. Click "Add Environment Variable"
4. Add each PROJECT_*_CONFIG variable with the JSON values above
5. Click "Save Changes"
6. Render will automatically redeploy

## Change Dashboard Password

To change your dashboard password:

1. Go to https://dashboard.render.com/web/srv-d5b9dkggjchc73brik10
2. Click "Environment" in the left sidebar
3. Find the `DASHBOARD_PASSWORD` variable
4. Click "Edit" and change the value to your desired password
5. Click "Save Changes"
6. Render will redeploy with the new password

**Current password:** `aaa`
**Recommended:** Change to a strong password!

## Important Notes

- **No `local_path` needed**: On Render, the system works without local paths. Projects are managed via git repos.
- **GitHub tokens**: Projects will use the global `GITHUB_TOKEN` environment variable for git operations.
- **Auto-import runs on every deployment**: The startup script checks for new projects each time the service starts.
- **Existing projects won't be duplicated**: The script checks if a project already exists before creating it.

## Manual Project Creation (Alternative)

If you prefer not to use auto-import, you can also add projects manually:

1. Login to https://inception-doje.onrender.com
2. Click "New Project"
3. Fill in the project details
4. Don't check the "auto-create" box (these repos already exist)
5. Enter the repo URL, branch, and Render service details
6. Leave "Local Path" empty (not used on Render)

## Verify Projects Imported

After adding the environment variables and redeploying:

1. Go to https://inception-doje.onrender.com
2. Login with your password
3. You should see both "telegram" and "controlroom" projects listed
4. Click on each project to verify the details
