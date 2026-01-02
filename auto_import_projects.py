#!/usr/bin/env python3
"""
Auto-import projects from environment variables on startup.
Set PROJECT_<NAME>_CONFIG environment variables to auto-create projects.
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database
import config


def auto_import_projects():
    """Auto-import projects from environment variables."""
    database.init_db()

    # Look for PROJECT_*_CONFIG environment variables
    # Format: PROJECT_TELEGRAM_CONFIG='{"repo_url":"...","repo_branch":"main","local_path":"..."}'

    imported = []

    for key, value in os.environ.items():
        if key.startswith('PROJECT_') and key.endswith('_CONFIG'):
            # Extract project name from env var name
            # PROJECT_TELEGRAM_CONFIG -> telegram
            project_name = key[8:-7].lower().replace('_', '-')

            try:
                project_config = json.loads(value)

                # Check if project already exists
                existing = database.get_project_by_name(project_name)
                if existing:
                    print(f"✓ Project '{project_name}' already exists (ID: {existing['id']})")
                    continue

                # Create project
                project_id = database.add_project(
                    name=project_name,
                    description=project_config.get('description', f'Auto-imported {project_name}'),
                    repo_url=project_config['repo_url'],
                    repo_branch=project_config.get('repo_branch', 'main'),
                    github_token=project_config.get('github_token', config.DEFAULT_GITHUB_TOKEN),
                    local_path=project_config.get('local_path'),
                    render_service_id=project_config.get('render_service_id'),
                    render_service_url=project_config.get('render_service_url'),
                    project_type=project_config.get('project_type')
                )

                print(f"✓ Auto-imported project '{project_name}' (ID: {project_id})")
                imported.append(project_name)

            except json.JSONDecodeError as e:
                print(f"✗ Error parsing {key}: {e}")
            except KeyError as e:
                print(f"✗ Missing required field in {key}: {e}")
            except Exception as e:
                print(f"✗ Error importing {project_name}: {e}")

    if imported:
        print(f"\n🎉 Auto-imported {len(imported)} project(s): {', '.join(imported)}")
    else:
        print("\nℹ️  No projects to auto-import (no PROJECT_*_CONFIG env vars found)")

    return imported


if __name__ == '__main__':
    auto_import_projects()
