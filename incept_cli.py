#!/usr/bin/env python3
"""
Incept CLI - Submit and process improvement requests using local Claude CLI
No API key required - uses your installed claude command
"""

import sys
import os
import subprocess
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import database

def submit_request(project_name, text, process_now=False):
    """Submit a new improvement request."""
    # Get project by name
    project = database.get_project_by_name(project_name)
    if not project:
        print(f"❌ Project '{project_name}' not found")
        print("\nAvailable projects:")
        for p in database.get_projects():
            print(f"  - {p['name']}")
        return None

    # Add request to database
    req_id = database.add_claude_request(
        project_id=project['id'],
        text=text,
        mode='local',  # Mark as local processing
        auto_push=True
    )

    print(f"✅ Created request #{req_id} for project '{project_name}'")
    print(f"   Request: {text}")

    if process_now:
        process_request(req_id)

    return req_id


def process_request(req_id):
    """Process a request using local Claude CLI."""
    req = database.get_claude_request(req_id)
    if not req:
        print(f"❌ Request #{req_id} not found")
        return False

    if req['status'] not in ['pending', 'error']:
        print(f"ℹ️  Request #{req_id} already {req['status']}")
        return False

    print(f"\n🚀 Processing request #{req_id}...")
    print(f"   Project: {req['project_name']}")
    print(f"   Request: {req['text']}")
    print(f"   Path: {req['project_path']}")

    # Update status
    database.update_claude_request(req_id, 'processing')

    # Change to project directory
    project_path = req['project_path']
    if not project_path or not os.path.exists(project_path):
        error = f"Project path not found: {project_path}"
        print(f"❌ {error}")
        database.update_claude_request(req_id, 'error', error)
        return False

    # Build claude command
    prompt = f"""You are working on the '{req['project_name']}' project.

Project directory: {project_path}

Task: {req['text']}

Please:
1. Read relevant files to understand the codebase
2. Make the requested changes
3. Explain what you did

Work in the project directory and make all necessary file changes."""

    print(f"\n📝 Sending request to Claude CLI...")

    try:
        # Run claude CLI in non-interactive mode with auto-accept
        # -p = print mode (non-interactive)
        # --dangerously-skip-permissions = auto-accept all changes
        result = subprocess.run(
            ['claude', '-p', '--dangerously-skip-permissions', prompt],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode == 0:
            response = result.stdout
            print(f"\n✅ Request completed successfully!")
            print(f"\nClaude's response:")
            print("=" * 60)
            print(response)
            print("=" * 60)

            database.update_claude_request(req_id, 'completed', response)
            return True
        else:
            error = f"Claude CLI failed: {result.stderr}"
            print(f"\n❌ {error}")
            database.update_claude_request(req_id, 'error', error)
            return False

    except subprocess.TimeoutExpired:
        error = "Request timed out after 5 minutes"
        print(f"\n❌ {error}")
        database.update_claude_request(req_id, 'error', error)
        return False
    except Exception as e:
        error = f"Error: {str(e)}"
        print(f"\n❌ {error}")
        database.update_claude_request(req_id, 'error', error)
        return False


def list_requests(project_name=None, status=None):
    """List requests."""
    if project_name:
        project = database.get_project_by_name(project_name)
        if not project:
            print(f"❌ Project '{project_name}' not found")
            return
        project_id = project['id']
    else:
        project_id = None

    requests = database.get_claude_requests(project_id=project_id, limit=50)

    if not requests:
        print("No requests found")
        return

    print(f"\n{'ID':<5} {'Project':<15} {'Status':<12} {'Created':<20} {'Request'}")
    print("=" * 100)

    for req in requests:
        if status and req['status'] != status:
            continue
        text = req['text'][:50] + "..." if len(req['text']) > 50 else req['text']
        print(f"{req['id']:<5} {req['project_name']:<15} {req['status']:<12} {req['created_at']:<20} {text}")


def list_projects():
    """List all projects."""
    projects = database.get_projects()

    if not projects:
        print("No projects found")
        return

    print(f"\n{'ID':<5} {'Name':<20} {'Type':<15} {'Path'}")
    print("=" * 100)

    for project in projects:
        print(f"{project['id']:<5} {project['name']:<20} {project['project_type'] or 'N/A':<15} {project['local_path'] or 'N/A'}")


def main():
    parser = argparse.ArgumentParser(description='Incept CLI - Submit and process improvement requests')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Submit command
    submit_parser = subparsers.add_parser('submit', help='Submit a new request')
    submit_parser.add_argument('project', help='Project name')
    submit_parser.add_argument('text', help='Request text')
    submit_parser.add_argument('--now', action='store_true', help='Process immediately')

    # Process command
    process_parser = subparsers.add_parser('process', help='Process a pending request')
    process_parser.add_argument('request_id', type=int, help='Request ID')

    # List command
    list_parser = subparsers.add_parser('list', help='List requests')
    list_parser.add_argument('--project', help='Filter by project name')
    list_parser.add_argument('--status', help='Filter by status')

    # Projects command
    projects_parser = subparsers.add_parser('projects', help='List all projects')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == 'submit':
        submit_request(args.project, args.text, process_now=args.now)
    elif args.command == 'process':
        process_request(args.request_id)
    elif args.command == 'list':
        list_requests(project_name=args.project, status=args.status)
    elif args.command == 'projects':
        list_projects()


if __name__ == '__main__':
    main()
