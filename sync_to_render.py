#!/usr/bin/env python3
"""
Sync environment variables to Render services.
Reads from .env file and updates all Render services for projects in database.
"""

import os
import sys
import database
import render_manager


def load_env_file():
    """Load environment variables from .env file."""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.exists(env_path):
        print("Error: .env file not found!")
        print("Run setup_env.py first to create it.")
        sys.exit(1)

    env_vars = {}
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value

    return env_vars


def main():
    """Sync environment variables to all Render services."""
    print("=" * 60)
    print("SYNC ENVIRONMENT VARIABLES TO RENDER")
    print("=" * 60)

    # Load .env file
    print("\nLoading environment variables from .env...")
    env_vars = load_env_file()

    required = ['ANTHROPIC_API_KEY', 'GITHUB_TOKEN', 'RENDER_API_KEY', 'DASHBOARD_PASSWORD', 'SECRET_KEY']
    missing = [var for var in required if var not in env_vars]

    if missing:
        print(f"\nError: Missing required variables in .env: {', '.join(missing)}")
        sys.exit(1)

    print(f"✓ Loaded {len(env_vars)} environment variables")

    # Initialize database
    database.init_db()

    # Get all projects
    projects = database.get_all_projects()
    projects_with_render = [p for p in projects if p.get('render_service_id')]

    if not projects_with_render:
        print("\nNo projects with Render service IDs found.")
        print("Add Render service IDs to your projects first.")
        sys.exit(0)

    print(f"\nFound {len(projects_with_render)} project(s) with Render services:")
    for p in projects_with_render:
        print(f"  - {p['name']} ({p['render_service_id']})")

    # Confirm sync
    response = input("\nSync to all Render services? (y/N): ").strip().lower()
    if response != 'y':
        print("Sync cancelled.")
        sys.exit(0)

    # Initialize Render manager
    rm = render_manager.RenderManager(env_vars['RENDER_API_KEY'])

    # Variables to sync (exclude Render-specific vars)
    sync_vars = {
        'ANTHROPIC_API_KEY': env_vars['ANTHROPIC_API_KEY'],
        'GITHUB_TOKEN': env_vars['GITHUB_TOKEN'],
        'DASHBOARD_PASSWORD': env_vars['DASHBOARD_PASSWORD'],
        'SECRET_KEY': env_vars['SECRET_KEY'],
    }

    # Add optional vars if present
    if 'CLAUDE_CODE_OAUTH_TOKEN' in env_vars:
        sync_vars['CLAUDE_CODE_OAUTH_TOKEN'] = env_vars['CLAUDE_CODE_OAUTH_TOKEN']

    if 'RENDER_OWNER_ID' in env_vars:
        sync_vars['RENDER_OWNER_ID'] = env_vars['RENDER_OWNER_ID']

    print("\n" + "=" * 60)
    print("SYNCING TO RENDER SERVICES")
    print("=" * 60)

    success_count = 0
    fail_count = 0

    for project in projects_with_render:
        service_id = project['render_service_id']
        print(f"\n[{project['name']}] Syncing to {service_id}...")

        # Get current env vars to compare
        current_success, current_vars = rm.get_env_vars(service_id)
        if current_success:
            current_keys = [var['key'] for var in current_vars]
            print(f"  Current variables: {len(current_keys)}")

        # Sync new variables
        success, result = rm.set_env_vars(service_id, sync_vars)

        if success:
            print(f"  ✓ Successfully synced {len(sync_vars)} variables")
            success_count += 1

            # Ask if they want to trigger deploy
            trigger = input(f"  Trigger deploy for {project['name']}? (y/N): ").strip().lower()
            if trigger == 'y':
                deploy_success, deploy_result = rm.trigger_deploy(service_id)
                if deploy_success:
                    print(f"  ✓ Deploy triggered")
                else:
                    print(f"  ✗ Failed to trigger deploy: {deploy_result}")
        else:
            print(f"  ✗ Failed: {result}")
            fail_count += 1

    print("\n" + "=" * 60)
    print("SYNC COMPLETE")
    print("=" * 60)
    print(f"\nSuccessful: {success_count}")
    print(f"Failed: {fail_count}")
    print()


if __name__ == '__main__':
    main()
