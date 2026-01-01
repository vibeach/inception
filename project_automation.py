#!/usr/bin/env python3
"""
Project Automation Module
Automatically creates GitHub repos and Render services for new projects.
"""

import os
import requests
import json
import tempfile
import shutil
import subprocess
from datetime import datetime


def create_github_repo(repo_name, description, github_token, private=False):
    """
    Create a new GitHub repository.

    Returns: (success, repo_url or error_message)
    """
    try:
        response = requests.post(
            'https://api.github.com/user/repos',
            headers={
                'Authorization': f'token {github_token}',
                'Content-Type': 'application/json'
            },
            json={
                'name': repo_name,
                'description': description,
                'private': private,
                'auto_init': False  # We'll push initial commit ourselves
            }
        )

        if response.status_code == 201:
            data = response.json()
            return True, data['clone_url'], data['html_url']
        else:
            error = response.json().get('message', 'Unknown error')
            return False, f"GitHub API error: {error}", None

    except Exception as e:
        return False, f"Error creating GitHub repo: {str(e)}", None


def create_render_service(service_name, repo_url, github_token, render_api_key,
                          owner_id, project_type='python', port=5000):
    """
    Create a new Render web service.

    Returns: (success, service_id, service_url or error_message)
    """
    try:
        # Determine build and start commands based on project type
        if project_type.lower() in ['flask', 'django', 'python']:
            build_command = 'pip install -r requirements.txt'
            start_command = 'gunicorn app:app --bind 0.0.0.0:$PORT' if project_type.lower() == 'flask' else 'python app.py'
            env = 'python'
        elif project_type.lower() in ['node.js', 'nodejs', 'express']:
            build_command = 'npm install'
            start_command = 'npm start'
            env = 'node'
        elif project_type.lower() == 'react':
            build_command = 'npm install && npm run build'
            start_command = 'npm start'
            env = 'node'
        elif project_type.lower() == 'next.js':
            build_command = 'npm install && npm run build'
            start_command = 'npm start'
            env = 'node'
        else:
            # Default to Python
            build_command = 'pip install -r requirements.txt'
            start_command = 'python app.py'
            env = 'python'

        response = requests.post(
            'https://api.render.com/v1/services',
            headers={
                'Authorization': f'Bearer {render_api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            json={
                'type': 'web_service',
                'name': service_name,
                'ownerId': owner_id,
                'repo': repo_url,
                'branch': 'main',
                'autoDeploy': 'yes',
                'serviceDetails': {
                    'env': env,
                    'plan': 'starter',
                    'region': 'oregon',
                    'healthCheckPath': '/health',
                    'envSpecificDetails': {
                        'buildCommand': build_command,
                        'startCommand': start_command
                    }
                }
            }
        )

        if response.status_code == 201:
            data = response.json()
            service_id = data['service']['id']
            service_url = data['service']['serviceDetails']['url']
            return True, service_id, service_url
        else:
            error = response.json().get('message', 'Unknown error')
            return False, f"Render API error: {error}", None

    except Exception as e:
        return False, f"Error creating Render service: {str(e)}", None


def create_project_template(project_type, project_name, description):
    """
    Create a basic project template based on project type.

    Returns: dict of files to create {filename: content}
    """
    templates = {}

    if project_type.lower() in ['flask', 'python']:
        # Flask template
        templates['app.py'] = f'''"""
{project_name}
{description or 'A Flask application'}
"""

from flask import Flask, render_template, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html', title='{project_name}')

@app.route('/health')
def health():
    return jsonify({{'status': 'ok'}})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
'''

        templates['requirements.txt'] = '''Flask>=3.0.0
gunicorn>=21.0.0
'''

        templates['templates/index.html'] = f'''<!DOCTYPE html>
<html>
<head>
    <title>{project_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background: #0f172a;
            color: #e2e8f0;
        }}
        h1 {{ color: #60a5fa; }}
    </style>
</head>
<body>
    <h1>{{{{ title }}}}</h1>
    <p>{description or 'Welcome to your new Flask application!'}</p>
    <p>This project was automatically created and deployed by Inception.</p>
</body>
</html>
'''

        templates['README.md'] = f'''# {project_name}

{description or 'A Flask application'}

## Created by Inception

This project was automatically created, initialized, and deployed by the Inception system.

## Getting Started

```bash
pip install -r requirements.txt
python app.py
```

Visit http://localhost:5000

## Deployment

Automatically deployed to Render. Any push to main branch will trigger a redeploy.
'''

        templates['.gitignore'] = '''# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store

# Logs
*.log
'''

    elif project_type.lower() in ['node.js', 'nodejs', 'express']:
        # Node.js/Express template
        templates['app.js'] = f'''/**
 * {project_name}
 * {description or 'An Express application'}
 */

const express = require('express');
const app = express();
const port = process.env.PORT || 5000;

app.get('/', (req, res) => {{
  res.send(`
    <html>
      <head>
        <title>{project_name}</title>
        <style>
          body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background: #0f172a;
            color: #e2e8f0;
          }}
          h1 {{ color: #60a5fa; }}
        </style>
      </head>
      <body>
        <h1>{project_name}</h1>
        <p>{description or 'Welcome to your new Express application!'}</p>
        <p>This project was automatically created and deployed by Inception.</p>
      </body>
    </html>
  `);
}});

app.get('/health', (req, res) => {{
  res.json({{ status: 'ok' }});
}});

app.listen(port, () => {{
  console.log(`Server running on port ${{port}}`);
}});
'''

        templates['package.json'] = f'''{{
  "name": "{project_name.lower().replace(' ', '-')}",
  "version": "1.0.0",
  "description": "{description or 'An Express application'}",
  "main": "app.js",
  "scripts": {{
    "start": "node app.js"
  }},
  "dependencies": {{
    "express": "^4.18.0"
  }}
}}
'''

        templates['README.md'] = f'''# {project_name}

{description or 'An Express application'}

## Created by Inception

This project was automatically created, initialized, and deployed by the Inception system.

## Getting Started

```bash
npm install
npm start
```

Visit http://localhost:5000

## Deployment

Automatically deployed to Render. Any push to main branch will trigger a redeploy.
'''

        templates['.gitignore'] = '''node_modules/
npm-debug.log
.env
.DS_Store
'''

    else:
        # Generic template
        templates['README.md'] = f'''# {project_name}

{description or 'A new project'}

## Created by Inception

This project was automatically created by the Inception system.

Add your application code here!
'''

        templates['.gitignore'] = '''.DS_Store
*.log
'''

    return templates


def initialize_and_push_repo(repo_url, github_token, templates, branch='main'):
    """
    Initialize a local repo, add template files, and push to GitHub.

    Returns: (success, message)
    """
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()

    try:
        # Initialize git repo
        subprocess.run(['git', 'init'], cwd=temp_dir, check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'inception@system.local'],
                      cwd=temp_dir, check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Inception System'],
                      cwd=temp_dir, check=True, capture_output=True)

        # Create template files
        for filepath, content in templates.items():
            full_path = os.path.join(temp_dir, filepath)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                f.write(content)

        # Add and commit
        subprocess.run(['git', 'add', '.'], cwd=temp_dir, check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit - Created by Inception'],
                      cwd=temp_dir, check=True, capture_output=True)

        # Add remote with token auth
        auth_url = repo_url.replace('https://', f'https://{github_token}@')
        subprocess.run(['git', 'remote', 'add', 'origin', auth_url],
                      cwd=temp_dir, check=True, capture_output=True)

        # Rename branch to main if needed
        subprocess.run(['git', 'branch', '-M', branch],
                      cwd=temp_dir, check=True, capture_output=True)

        # Push
        result = subprocess.run(['git', 'push', '-u', 'origin', branch],
                               cwd=temp_dir, capture_output=True, text=True)

        if result.returncode != 0:
            return False, f"Git push failed: {result.stderr}"

        return True, "Repository initialized and pushed successfully"

    except subprocess.CalledProcessError as e:
        return False, f"Git operation failed: {e.stderr.decode() if e.stderr else str(e)}"
    except Exception as e:
        return False, f"Error: {str(e)}"
    finally:
        # Clean up temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)


def create_full_project(project_name, description, project_type, github_token,
                       render_api_key, render_owner_id, private=False):
    """
    Full automated project creation:
    1. Create GitHub repo
    2. Initialize with template
    3. Push initial commit
    4. Create Render service
    5. Return project details

    Returns: (success, project_details_dict or error_message)
    """
    import database

    # Step 1: Create GitHub repo
    print(f"Creating GitHub repo: {project_name}")
    success, result, html_url = create_github_repo(
        project_name.lower().replace(' ', '-'),
        description,
        github_token,
        private
    )

    if not success:
        return False, result

    repo_url = result
    print(f"✓ GitHub repo created: {html_url}")

    # Step 2: Create project template
    print("Generating project template...")
    templates = create_project_template(project_type, project_name, description)

    # Step 3: Initialize and push
    print("Initializing git repo and pushing...")
    success, message = initialize_and_push_repo(repo_url, github_token, templates)

    if not success:
        return False, f"Failed to push initial commit: {message}"

    print(f"✓ {message}")

    # Step 4: Create Render service
    print("Creating Render service...")
    success, service_id, service_url = create_render_service(
        project_name.lower().replace(' ', '-'),
        repo_url,
        github_token,
        render_api_key,
        render_owner_id,
        project_type
    )

    if not success:
        return False, f"Failed to create Render service: {service_id}"

    print(f"✓ Render service created: {service_url}")

    # Step 5: Return project details
    project_details = {
        'name': project_name,
        'description': description,
        'repo_url': repo_url,
        'repo_html_url': html_url,
        'repo_branch': 'main',
        'github_token': github_token,
        'render_service_id': service_id,
        'render_service_url': service_url,
        'project_type': project_type
    }

    print("✓ Project creation complete!")

    return True, project_details
