#!/usr/bin/env python3
"""
Incept Request Processor - Multi-Project
Polls for pending requests and processes them using either:
- Claude API with tool use (works on Render and locally) - ACTUALLY MAKES CHANGES
- Local Claude CLI (requires claude command installed)

Supports multiple projects with project-specific git repos and directories.
"""

import subprocess
import time
import sys
import os
import json
import glob as glob_module

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import database
import dynamic_config

POLL_INTERVAL = 5  # seconds between checks

# Define tools for Claude to use
TOOLS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file. Use this to examine existing code before making changes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file from project root (e.g., 'app.py' or 'templates/index.html')"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write content to a file. This will overwrite the entire file. Use for creating new files or completely rewriting existing ones.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file from project root"
                },
                "content": {
                    "type": "string",
                    "description": "The complete content to write to the file"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "edit_file",
        "description": "Make a targeted edit to a file by replacing a specific string with new content. More precise than write_file for small changes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file from project root"
                },
                "old_string": {
                    "type": "string",
                    "description": "The exact string to find and replace (must be unique in the file)"
                },
                "new_string": {
                    "type": "string",
                    "description": "The string to replace it with"
                }
            },
            "required": ["path", "old_string", "new_string"]
        }
    },
    {
        "name": "list_files",
        "description": "List files in a directory or matching a glob pattern.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern (e.g., '*.py', 'templates/*.html', '**/*.js')"
                }
            },
            "required": ["pattern"]
        }
    },
    {
        "name": "log_progress",
        "description": "Log progress message to the request log. Use this to communicate what you're doing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Progress message to log"
                },
                "level": {
                    "type": "string",
                    "enum": ["info", "success", "warning", "error"],
                    "description": "Log level"
                }
            },
            "required": ["message"]
        }
    }
]


def execute_tool(tool_name, tool_input, req_id, project_path):
    """Execute a tool and return the result."""
    try:
        if tool_name == "read_file":
            path = os.path.join(project_path, tool_input["path"])
            if not os.path.exists(path):
                return f"Error: File not found: {tool_input['path']}"
            with open(path, 'r') as f:
                content = f.read()
            return f"Contents of {tool_input['path']}:\n{content}"

        elif tool_name == "write_file":
            path = os.path.join(project_path, tool_input["path"])
            # Create directory if needed
            os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
            with open(path, 'w') as f:
                f.write(tool_input["content"])
            database.add_claude_log(req_id, f"Wrote file: {tool_input['path']}", 'info')
            return f"Successfully wrote {len(tool_input['content'])} characters to {tool_input['path']}"

        elif tool_name == "edit_file":
            path = os.path.join(project_path, tool_input["path"])
            if not os.path.exists(path):
                return f"Error: File not found: {tool_input['path']}"
            with open(path, 'r') as f:
                content = f.read()
            old_string = tool_input["old_string"]
            new_string = tool_input["new_string"]
            if old_string not in content:
                return f"Error: Could not find the specified string in {tool_input['path']}. The string to replace was not found."
            if content.count(old_string) > 1:
                return f"Error: The string appears {content.count(old_string)} times in the file. Please provide a more unique string to replace."
            new_content = content.replace(old_string, new_string, 1)
            with open(path, 'w') as f:
                f.write(new_content)
            database.add_claude_log(req_id, f"Edited file: {tool_input['path']}", 'info')
            return f"Successfully edited {tool_input['path']}"

        elif tool_name == "list_files":
            pattern = tool_input["pattern"]
            files = glob_module.glob(os.path.join(project_path, pattern), recursive=True)
            # Make paths relative
            files = [os.path.relpath(f, project_path) for f in files]
            return f"Files matching '{pattern}':\n" + "\n".join(files) if files else f"No files found matching '{pattern}'"

        elif tool_name == "log_progress":
            level = tool_input.get("level", "info")
            database.add_claude_log(req_id, tool_input["message"], level)
            return "Logged successfully"

        else:
            return f"Unknown tool: {tool_name}"

    except Exception as e:
        return f"Error executing {tool_name}: {str(e)}"


def git_commit_and_push(req_id, project_path, repo_url, repo_branch, github_token, commit_message=None):
    """Commit and push changes to git after making modifications."""
    try:
        # Check if there are any changes
        status_result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=10
        )

        if not status_result.stdout.strip():
            database.add_claude_log(req_id, 'No changes to commit', 'info')
            return True

        changes = status_result.stdout.strip().split('\n')
        database.add_claude_log(req_id, f'Found {len(changes)} changed file(s), committing...', 'info')

        # Configure git identity
        subprocess.run(['git', 'config', 'user.email', 'incept@inception-system.local'],
                      cwd=project_path, capture_output=True, timeout=5)
        subprocess.run(['git', 'config', 'user.name', 'Inception System'],
                      cwd=project_path, capture_output=True, timeout=5)

        # Stage all changes
        add_result = subprocess.run(
            ['git', 'add', '-A'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=10
        )

        if add_result.returncode != 0:
            database.add_claude_log(req_id, f'Git add failed: {add_result.stderr}', 'error')
            return False

        # Commit
        msg = commit_message or f'Incept #{req_id}: Auto-commit changes'
        commit_result = subprocess.run(
            ['git', 'commit', '-m', msg],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=10
        )

        if commit_result.returncode != 0 and 'nothing to commit' not in commit_result.stdout:
            database.add_claude_log(req_id, f'Git commit failed: {commit_result.stderr}', 'error')
            return False

        # Check if origin remote exists, configure if needed
        remote_check = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            cwd=project_path, capture_output=True, text=True, timeout=5
        )

        if remote_check.returncode != 0:
            if not repo_url:
                database.add_claude_log(req_id, 'No git remote configured for this project.', 'error')
                return False
            subprocess.run(['git', 'remote', 'add', 'origin', repo_url],
                          cwd=project_path, capture_output=True, timeout=5)

        # Set up authentication if token available
        if github_token:
            url_result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                cwd=project_path, capture_output=True, text=True, timeout=5
            )
            remote_url = url_result.stdout.strip()
            if github_token not in remote_url and 'github.com' in remote_url:
                push_url = remote_url.replace('https://', f'https://{github_token}@')
                subprocess.run(['git', 'remote', 'set-url', 'origin', push_url],
                              cwd=project_path, capture_output=True, timeout=5)

        # Get current branch (empty if detached HEAD - common on Render)
        branch_result = subprocess.run(
            ['git', 'branch', '--show-current'],
            cwd=project_path, capture_output=True, text=True, timeout=5
        )
        current_branch = branch_result.stdout.strip()
        target_branch = repo_branch or 'main'

        # Push - handle detached HEAD state
        if current_branch:
            push_cmd = ['git', 'push', '-u', 'origin', current_branch]
        else:
            push_cmd = ['git', 'push', 'origin', f'HEAD:{target_branch}']

        database.add_claude_log(req_id, 'Pushing to remote (will trigger redeploy if connected to Render)...', 'info')
        push_result = subprocess.run(
            push_cmd,
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        if push_result.returncode != 0:
            error_msg = push_result.stderr
            if 'Authentication failed' in error_msg or 'could not read Username' in error_msg:
                database.add_claude_log(req_id, 'Git push auth failed. Check GitHub token for this project.', 'error')
            else:
                database.add_claude_log(req_id, f'Git push failed: {error_msg}', 'error')
            return False

        database.add_claude_log(req_id, 'Changes pushed to git successfully', 'success')
        return True

    except subprocess.TimeoutExpired:
        database.add_claude_log(req_id, 'Git operation timed out', 'error')
        return False
    except Exception as e:
        database.add_claude_log(req_id, f'Git error: {str(e)}', 'error')
        return False


def build_context_summary(req):
    """Build a context summary from parent requests if this is a restart."""
    parent_id = req.get('parent_id')
    if not parent_id:
        return ""

    # Get parent request
    parent = database.get_claude_request(parent_id)
    if not parent:
        return ""

    parts = []
    parts.append("\n=== PREVIOUS ATTEMPT CONTEXT ===")
    parts.append(f"\nPrevious request #{parent_id}:")
    parts.append(f"Status: {parent.get('status', 'unknown')}")

    # Add logs from parent
    logs = database.get_claude_logs(parent_id)
    if logs:
        parts.append("\nProgress log from previous attempt:")
        for log in logs[-10:]:  # Last 10 logs
            parts.append(f"  [{log.get('log_type', 'info')}] {log.get('message', '')}")

    # Add response/summary if available
    if parent.get('response'):
        parts.append(f"\nPrevious result summary:\n{parent['response'][:1000]}")

    parts.append("\n=== END PREVIOUS CONTEXT ===\n")
    parts.append("Continue from where the previous attempt left off. Avoid repeating completed work.")

    return "\n".join(parts)


def process_with_api(req, project):
    """Process request using Claude API with tool use to actually make changes."""
    try:
        import anthropic
    except ImportError:
        database.add_claude_log(req['id'], 'anthropic package not installed. Run: pip install anthropic', 'error')
        database.update_claude_request(req['id'], 'error', 'anthropic package not installed')
        return False

    req_id = req['id']
    request_text = req['text']
    project_path = project['local_path']

    # Get settings for this project
    settings = database.get_incept_settings(project['id'])
    model = req.get('model') or settings.get('model', 'claude-sonnet-4-20250514')

    print(f"\n{'='*60}")
    print(f"Processing request #{req_id} for project: {project['name']}")
    print(f"Via API ({model})")
    print(f"Request: {request_text[:50]}...")
    if req.get('parent_id'):
        print(f"Continuation of: #{req.get('parent_id')}")
    print(f"{'='*60}\n")

    database.update_claude_request(req_id, 'processing')
    database.add_claude_log(req_id, f'Processing via API with model: {model}', 'info')

    # System prompt for tool use - loaded from dynamic config (hot-reloadable!)
    system_prompt = dynamic_config.get_incept_system_prompt()

    # Build context from parent if this is a restart
    context_summary = build_context_summary(req)

    user_message = f"""Please implement the following request for the project "{project['name']}":

{request_text}
{context_summary}

Start by reading relevant files to understand the current code, then make the necessary changes."""

    try:
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        messages = [{"role": "user", "content": user_message}]

        database.add_claude_log(req_id, 'Starting agentic loop with tools...', 'info')

        total_input_tokens = 0
        total_output_tokens = 0
        iteration = 0
        max_iterations = 50  # Safety limit
        changes_made = []

        while iteration < max_iterations:
            iteration += 1
            print(f"  Iteration {iteration}...")

            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_prompt,
                tools=TOOLS,
                messages=messages
            )

            # Track tokens
            total_input_tokens += response.usage.input_tokens if response.usage else 0
            total_output_tokens += response.usage.output_tokens if response.usage else 0

            # Check if we're done (no more tool use)
            if response.stop_reason == "end_turn":
                # Extract final text response
                final_text = ""
                for block in response.content:
                    if hasattr(block, 'text'):
                        final_text += block.text

                database.add_claude_log(req_id, f'Completed after {iteration} iterations', 'success')
                database.add_claude_log(req_id, f'Tokens: {total_input_tokens} in, {total_output_tokens} out', 'info')

                summary = f"Changes made:\n" + "\n".join(changes_made) if changes_made else "No file changes made"
                summary += f"\n\nFinal response:\n{final_text[:1000]}"

                database.update_claude_request(req_id, 'completed', summary)

                # Auto-commit and push changes to git if files were modified and auto_push is enabled
                if changes_made:
                    auto_push = req.get('auto_push', True)
                    if auto_push:
                        git_commit_and_push(
                            req_id,
                            project_path,
                            project['repo_url'],
                            project['repo_branch'],
                            project['github_token'],
                            f'Incept #{req_id}: {request_text[:50]}'
                        )
                    else:
                        database.add_claude_log(req_id, 'Changes made but not pushed (auto_push disabled). Use push button to push manually.', 'info')

                print(f"Request #{req_id} completed via API")
                return True

            # Process tool calls
            assistant_content = response.content
            tool_results = []

            for block in assistant_content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    tool_id = block.id

                    print(f"    Tool: {tool_name}")
                    result = execute_tool(tool_name, tool_input, req_id, project_path)

                    # Track file changes
                    if tool_name in ("write_file", "edit_file") and "Successfully" in result:
                        changes_made.append(f"- {tool_name}: {tool_input.get('path', 'unknown')}")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result
                    })

            # Add assistant response and tool results to messages
            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": tool_results})

        # Max iterations reached
        database.add_claude_log(req_id, f'Max iterations ({max_iterations}) reached', 'warning')
        database.update_claude_request(req_id, 'completed', f'Completed with {len(changes_made)} changes (max iterations reached)')

        # Auto-commit and push changes to git if files were modified and auto_push is enabled
        if changes_made:
            auto_push = req.get('auto_push', True)
            if auto_push:
                git_commit_and_push(
                    req_id,
                    project_path,
                    project['repo_url'],
                    project['repo_branch'],
                    project['github_token'],
                    f'Incept #{req_id}: {request_text[:50]}'
                )
            else:
                database.add_claude_log(req_id, 'Changes made but not pushed (auto_push disabled). Use push button to push manually.', 'info')

        return True

    except Exception as e:
        error_msg = f'Error: {str(e)}'
        database.add_claude_log(req_id, error_msg, 'error')
        database.update_claude_request(req_id, 'error', error_msg)
        print(f"Request #{req_id} failed: {error_msg}")
        import traceback
        traceback.print_exc()
        return False


def process_request(req):
    """Process a single request based on request's mode or project settings."""
    # Get project info
    project = database.get_project(req['project_id'])
    if not project:
        database.add_claude_log(req['id'], f"Project ID {req['project_id']} not found", 'error')
        database.update_claude_request(req['id'], 'error', 'Project not found')
        return False

    # Check if project path exists
    if not project['local_path'] or not os.path.exists(project['local_path']):
        database.add_claude_log(req['id'], f"Project path not found: {project['local_path']}", 'error')
        database.update_claude_request(req['id'], 'error', 'Project path not found')
        return False

    # Get mode from request or project settings
    settings = database.get_incept_settings(project['id'])
    mode = req.get('mode') or settings.get('mode', 'api')

    if mode == 'api':
        return process_with_api(req, project)
    else:
        # CLI mode not implemented for multi-project yet
        database.add_claude_log(req['id'], 'CLI mode not yet supported for multi-project', 'error')
        database.update_claude_request(req['id'], 'error', 'CLI mode not supported')
        return False


def main():
    """Main polling loop."""
    print("Inception Request Processor")
    print("=" * 40)
    print(f"Poll interval: {POLL_INTERVAL}s")

    # Check auth status
    if os.environ.get('ANTHROPIC_API_KEY'):
        print("API Key: Set (API mode available)")
    else:
        print("API Key: Not set")

    print("Waiting for requests...")
    print("=" * 40)

    # Initialize database
    database.init_db()

    while True:
        try:
            # Check for pending requests across all projects
            pending = database.get_pending_claude_requests()

            if pending:
                print(f"\nFound {len(pending)} pending request(s)")
                # Process one at a time
                process_request(pending[0])

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print("\nStopping processor...")
            break
        except Exception as e:
            print(f"Error in main loop: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    main()
