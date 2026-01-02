#!/usr/bin/env python3
"""
Inception Dashboard
Multi-project self-improvement system web interface
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from functools import wraps
import os
import sys
import threading
import time
import json

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import database
import dynamic_config
import incept_plus_suggester
import incept_plus_tracker
import incept_processor
import project_automation
import render_manager

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# Embedded processor state
_embedded_processor_thread = None
_embedded_processor_running = False


# ==================== AUTH ====================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == config.DASHBOARD_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        flash('Invalid password', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))


# ==================== MAIN ROUTES ====================

@app.route('/')
@login_required
def index():
    """Main dashboard - show all projects."""
    projects = database.get_projects()

    # Get stats for each project
    for project in projects:
        project['pending_requests'] = len(database.get_pending_claude_requests(project['id']))
        project['total_requests'] = len(database.get_claude_requests(project['id'], limit=1000))
        project['suggestions'] = len(database.get_incept_suggestions(project['id'], limit=1000))
        project['improvements'] = len(database.get_incept_improvements(project['id'], limit=1000))

    return render_template('index.html', projects=projects)


@app.route('/projects/new', methods=['GET', 'POST'])
@login_required
def new_project():
    """Create a new project."""
    if request.method == 'POST':
        try:
            # Check which automation features are requested
            auto_create_github = request.form.get('auto_create_github') == 'on'
            auto_create_render = request.form.get('auto_create_render') == 'on'

            project_name = request.form['name']
            description = request.form.get('description')
            project_type = request.form.get('project_type', 'Flask')

            # PATH 1: Both GitHub and Render automation
            if auto_create_github and auto_create_render:
                github_token = request.form.get('github_token') or config.DEFAULT_GITHUB_TOKEN
                render_api_key = request.form.get('render_api_key') or config.RENDER_API_KEY
                render_owner_id = request.form.get('render_owner_id') or config.RENDER_OWNER_ID

                # Validation
                if not github_token:
                    flash('GitHub token required for automated creation', 'error')
                    return render_template('new_project.html')
                if not render_api_key or not render_owner_id:
                    flash('Render API key and Owner ID required for automated deployment', 'error')
                    return render_template('new_project.html')

                # Create both (existing function works for this)
                success, result = project_automation.create_full_project(
                    project_name=project_name,
                    description=description,
                    project_type=project_type,
                    github_token=github_token,
                    render_api_key=render_api_key,
                    render_owner_id=render_owner_id,
                    private=request.form.get('private_repo') == 'on'
                )

                if not success:
                    flash(f'Automated creation failed: {result}', 'error')
                    return render_template('new_project.html')

                # Add to database
                project_id = database.add_project(
                    name=result['name'],
                    description=result['description'],
                    repo_url=result['repo_url'],
                    repo_branch=result['repo_branch'],
                    github_token=result['github_token'],
                    local_path=None,
                    render_service_id=result['render_service_id'],
                    render_service_url=result['render_service_url'],
                    project_type=result['project_type']
                )

                flash(f'Project "{result["name"]}" created and deployed! 🚀', 'success')
                flash(f'GitHub: {result["repo_html_url"]}', 'success')
                flash(f'Render: {result["render_service_url"]}', 'success')
                return redirect(url_for('project_detail', project_id=project_id))

            # PATH 2: GitHub only automation
            elif auto_create_github and not auto_create_render:
                github_token = request.form.get('github_token') or config.DEFAULT_GITHUB_TOKEN

                if not github_token:
                    flash('GitHub token required for automated repository creation', 'error')
                    return render_template('new_project.html')

                # Create GitHub repo only
                success, result = project_automation.create_github_project_only(
                    project_name=project_name,
                    description=description,
                    project_type=project_type,
                    github_token=github_token,
                    private=request.form.get('private_repo') == 'on'
                )

                if not success:
                    flash(f'GitHub creation failed: {result}', 'error')
                    return render_template('new_project.html')

                # Add to database (no Render details)
                project_id = database.add_project(
                    name=result['name'],
                    description=result['description'],
                    repo_url=result['repo_url'],
                    repo_branch=result['repo_branch'],
                    github_token=result['github_token'],
                    local_path=request.form.get('local_path'),
                    render_service_id=request.form.get('render_service_id'),
                    render_service_url=request.form.get('render_service_url'),
                    project_type=result['project_type']
                )

                flash(f'GitHub repository "{result["name"]}" created! 📦', 'success')
                flash(f'Repository: {result["repo_html_url"]}', 'success')
                return redirect(url_for('project_detail', project_id=project_id))

            # PATH 3: Render only automation (requires existing repo)
            elif not auto_create_github and auto_create_render:
                repo_url = request.form.get('repo_url')
                if not repo_url:
                    flash('Repository URL required for Render deployment', 'error')
                    return render_template('new_project.html')

                github_token = request.form.get('github_token') or config.DEFAULT_GITHUB_TOKEN
                render_api_key = request.form.get('render_api_key') or config.RENDER_API_KEY
                render_owner_id = request.form.get('render_owner_id') or config.RENDER_OWNER_ID

                if not render_api_key or not render_owner_id:
                    flash('Render API key and Owner ID required for automated deployment', 'error')
                    return render_template('new_project.html')

                # Create Render service only
                success, result = project_automation.create_render_service_only(
                    project_name=project_name,
                    repo_url=repo_url,
                    description=description,
                    project_type=project_type,
                    github_token=github_token,
                    render_api_key=render_api_key,
                    render_owner_id=render_owner_id
                )

                if not success:
                    flash(f'Render deployment failed: {result}', 'error')
                    return render_template('new_project.html')

                # Add to database
                project_id = database.add_project(
                    name=project_name,
                    description=description,
                    repo_url=repo_url,
                    repo_branch=request.form.get('repo_branch', 'main'),
                    github_token=github_token,
                    local_path=request.form.get('local_path'),
                    render_service_id=result['render_service_id'],
                    render_service_url=result['render_service_url'],
                    project_type=project_type
                )

                flash(f'Project "{project_name}" deployed to Render! 🚀', 'success')
                flash(f'Render: {result["render_service_url"]}', 'success')
                return redirect(url_for('project_detail', project_id=project_id))

            # PATH 4: No automation (manual mode)
            else:
                # Manual project creation - requires repo_url
                repo_url = request.form.get('repo_url')
                if not repo_url:
                    flash('Repository URL is required', 'error')
                    return render_template('new_project.html')

                project_id = database.add_project(
                    name=project_name,
                    description=description,
                    repo_url=repo_url,
                    repo_branch=request.form.get('repo_branch', 'main'),
                    github_token=request.form.get('github_token') or config.DEFAULT_GITHUB_TOKEN,
                    local_path=request.form.get('local_path'),
                    render_service_id=request.form.get('render_service_id'),
                    render_service_url=request.form.get('render_service_url'),
                    project_type=project_type
                )
                flash(f'Project "{project_name}" created successfully!', 'success')
                return redirect(url_for('project_detail', project_id=project_id))

        except Exception as e:
            flash(f'Error creating project: {str(e)}', 'error')
            import traceback
            traceback.print_exc()

    return render_template('new_project.html')


@app.route('/projects/<int:project_id>')
@login_required
def project_detail(project_id):
    """Project detail page."""
    project = database.get_project(project_id)
    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('index'))

    # Get recent requests
    requests_list = database.get_claude_requests(project_id, limit=10)

    # Get recent suggestions
    suggestions = database.get_incept_suggestions(project_id, limit=10)

    # Get recent improvements
    improvements = database.get_incept_improvements(project_id, limit=10)

    # Get settings
    incept_settings = database.get_incept_settings(project_id)
    incept_plus_settings = database.get_incept_plus_settings(project_id)

    return render_template('project_detail.html',
                         project=project,
                         requests=requests_list,
                         suggestions=suggestions,
                         improvements=improvements,
                         incept_settings=incept_settings,
                         incept_plus_settings=incept_plus_settings)


@app.route('/projects/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    """Edit project settings."""
    project = database.get_project(project_id)
    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            database.update_project(
                project_id,
                name=request.form.get('name'),
                description=request.form.get('description'),
                repo_url=request.form.get('repo_url'),
                repo_branch=request.form.get('repo_branch'),
                github_token=request.form.get('github_token'),
                local_path=request.form.get('local_path'),
                render_service_id=request.form.get('render_service_id'),
                render_service_url=request.form.get('render_service_url'),
                project_type=request.form.get('project_type'),
                status=request.form.get('status')
            )
            flash('Project updated successfully!', 'success')
            return redirect(url_for('project_detail', project_id=project_id))
        except Exception as e:
            flash(f'Error updating project: {str(e)}', 'error')

    return render_template('edit_project.html', project=project)


@app.route('/projects/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    """Delete a project (cascades to all related data)."""
    project = database.get_project(project_id)
    if project:
        database.delete_project(project_id)
        flash(f'Project "{project["name"]}" deleted successfully!', 'success')
    return redirect(url_for('index'))


# ==================== INCEPT ROUTES ====================

@app.route('/projects/<int:project_id>/incept')
@login_required
def incept(project_id):
    """Incept control panel for a project."""
    project = database.get_project(project_id)
    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('index'))

    requests_list = database.get_claude_requests(project_id, limit=50)
    settings = database.get_incept_settings(project_id)

    # Check for available credentials
    has_api_key = bool(config.ANTHROPIC_API_KEY)
    has_oauth_token = bool(os.environ.get('CLAUDE_CODE_OAUTH_TOKEN') or config.CLAUDE_CODE_OAUTH_TOKEN)

    return render_template('incept.html',
                         project=project,
                         requests=requests_list,
                         settings=settings,
                         has_api_key=has_api_key,
                         has_oauth_token=has_oauth_token)


@app.route('/api/incept/request', methods=['POST'])
@login_required
def api_incept_request():
    """Submit a new Incept request."""
    data = request.get_json()
    project_id = data.get('project_id')
    text = data.get('text', '').strip()

    if not project_id or not text:
        return jsonify({'success': False, 'error': 'Missing project_id or text'}), 400

    project = database.get_project(project_id)
    if not project:
        return jsonify({'success': False, 'error': 'Project not found'}), 404

    # Get settings
    settings = database.get_incept_settings(project_id)
    mode = data.get('mode', settings.get('mode', 'api'))
    model = data.get('model', settings.get('model', 'claude-sonnet-4-20250514'))
    auto_push = data.get('auto_push', True)

    req_id = database.add_claude_request(
        project_id,
        text,
        mode=mode,
        model=model,
        auto_push=auto_push
    )

    # Start embedded processor if configured
    _ensure_embedded_processor()

    return jsonify({'success': True, 'request_id': req_id})


@app.route('/api/incept/requests/<int:project_id>')
@login_required
def api_incept_requests(project_id):
    """Get requests for a project."""
    requests_list = database.get_claude_requests(project_id, limit=50)
    return jsonify({'success': True, 'requests': requests_list})


@app.route('/api/incept/request/<int:req_id>/logs')
@login_required
def api_incept_request_logs(req_id):
    """Get logs for a request."""
    logs = database.get_claude_logs(req_id)
    return jsonify({'success': True, 'logs': logs})


@app.route('/api/incept/request/<int:req_id>/full-log')
@login_required
def api_incept_request_full_log(req_id):
    """Get full detailed log file for a request."""
    # Get the request to find the project
    req = database.get_claude_request(req_id)
    if not req:
        return jsonify({'success': False, 'error': 'Request not found'}), 404

    # Get project to find the log file
    project = database.get_project(req['project_id'])
    if not project or not project['local_path']:
        return jsonify({'success': False, 'error': 'Project not found'}), 404

    # Build log file path
    log_file = os.path.join(project['local_path'], 'inception_logs', f'request_{req_id}.log')

    if not os.path.exists(log_file):
        return jsonify({'success': False, 'error': 'Log file not found'}), 404

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Get relative path for display
        rel_path = os.path.relpath(log_file, project['local_path'])

        return jsonify({
            'success': True,
            'content': content,
            'log_file': rel_path
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/incept/request/<int:req_id>/cancel', methods=['POST'])
@login_required
def api_incept_cancel(req_id):
    """Cancel a pending request."""
    success = database.cancel_claude_request(req_id)
    return jsonify({'success': success})


@app.route('/api/incept/request/<int:req_id>/restart', methods=['POST'])
@login_required
def api_incept_restart(req_id):
    """Restart a request."""
    data = request.get_json() or {}
    new_req_id = database.restart_claude_request(
        req_id,
        new_text=data.get('text'),
        mode=data.get('mode'),
        model=data.get('model'),
        auto_push=data.get('auto_push')
    )

    if new_req_id:
        _ensure_embedded_processor()
        return jsonify({'success': True, 'request_id': new_req_id})
    return jsonify({'success': False, 'error': 'Failed to restart request'}), 400


@app.route('/api/incept/request/<int:req_id>/delete', methods=['POST'])
@login_required
def api_incept_delete(req_id):
    """Delete a request."""
    database.delete_claude_request(req_id)
    return jsonify({'success': True})


@app.route('/api/incept/settings/<int:project_id>', methods=['GET', 'POST'])
@login_required
def api_incept_settings(project_id):
    """Get or update Incept settings for a project."""
    if request.method == 'POST':
        data = request.get_json()
        database.save_incept_settings(
            project_id,
            mode=data.get('mode', 'api'),
            model=data.get('model', 'claude-sonnet-4-20250514')
        )
        return jsonify({'success': True})

    settings = database.get_incept_settings(project_id)
    return jsonify({'success': True, 'settings': settings})


# ==================== INCEPT+ ROUTES ====================

@app.route('/projects/<int:project_id>/incept-plus')
@login_required
def incept_plus(project_id):
    """Incept+ dashboard for a project."""
    project = database.get_project(project_id)
    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('index'))

    suggestions = database.get_incept_suggestions(project_id, limit=50)
    improvements = database.get_incept_improvements(project_id, limit=50)
    settings = database.get_incept_plus_settings(project_id)
    auto_session = database.get_active_incept_auto_session(project_id)

    # Check for available credentials
    has_api_key = bool(config.ANTHROPIC_API_KEY)
    has_oauth_token = bool(os.environ.get('CLAUDE_CODE_OAUTH_TOKEN') or config.CLAUDE_CODE_OAUTH_TOKEN)

    # Also get incept settings for mode
    incept_settings = database.get_incept_settings(project_id)

    return render_template('incept_plus.html',
                         project=project,
                         suggestions=suggestions,
                         improvements=improvements,
                         settings=settings,
                         incept_settings=incept_settings,
                         auto_session=auto_session,
                         has_api_key=has_api_key,
                         has_oauth_token=has_oauth_token)


@app.route('/api/incept-plus/suggest', methods=['POST'])
@login_required
def api_incept_plus_suggest():
    """Generate improvement suggestions."""
    data = request.get_json()
    project_id = data.get('project_id')
    direction = data.get('direction', '').strip()

    if not project_id or not direction:
        return jsonify({'success': False, 'error': 'Missing project_id or direction'}), 400

    try:
        suggestions = incept_plus_suggester.generate_and_save_suggestions(
            project_id,
            direction,
            context=data.get('context'),
            max_suggestions=data.get('max_suggestions', 5)
        )
        return jsonify({'success': True, 'suggestions': suggestions})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/incept-plus/suggestions/<int:project_id>')
@login_required
def api_incept_plus_suggestions(project_id):
    """Get suggestions for a project."""
    status = request.args.get('status')
    category = request.args.get('category')
    suggestions = database.get_incept_suggestions(project_id, status=status, category=category)
    return jsonify({'success': True, 'suggestions': suggestions})


@app.route('/api/incept-plus/suggestion/<int:suggestion_id>/accept', methods=['POST'])
@login_required
def api_incept_plus_accept(suggestion_id):
    """Accept a suggestion."""
    database.update_incept_suggestion_status(suggestion_id, 'accepted')
    return jsonify({'success': True})


@app.route('/api/incept-plus/suggestion/<int:suggestion_id>/reject', methods=['POST'])
@login_required
def api_incept_plus_reject(suggestion_id):
    """Reject a suggestion."""
    database.update_incept_suggestion_status(suggestion_id, 'rejected')
    return jsonify({'success': True})


@app.route('/api/incept-plus/suggestion/<int:suggestion_id>/implement', methods=['POST'])
@login_required
def api_incept_plus_implement(suggestion_id):
    """Create an Incept request to implement a suggestion."""
    suggestion = database.get_incept_suggestion(suggestion_id)
    if not suggestion:
        return jsonify({'success': False, 'error': 'Suggestion not found'}), 404

    # Create request text from suggestion
    request_text = f"""Implement the following improvement:

Title: {suggestion['title']}

Description: {suggestion['description']}

Implementation Details:
{suggestion['implementation_details']}

Category: {suggestion['category']}
Priority: {suggestion['priority']}
Estimated Effort: {suggestion.get('estimated_effort', 'unknown')}
"""

    # Get settings for this project
    settings = database.get_incept_settings(suggestion['project_id'])

    # Create the request
    req_id = database.add_claude_request(
        suggestion['project_id'],
        request_text,
        mode=settings.get('mode', 'api'),
        model=settings.get('model', 'claude-sonnet-4-20250514'),
        auto_push=True
    )

    # Update suggestion status
    database.update_incept_suggestion_status(suggestion_id, 'implementing')

    _ensure_embedded_processor()

    return jsonify({'success': True, 'request_id': req_id})


@app.route('/api/incept-plus/improvements/<int:project_id>')
@login_required
def api_incept_plus_improvements(project_id):
    """Get improvements for a project."""
    improvements = database.get_incept_improvements(project_id)
    return jsonify({'success': True, 'improvements': improvements})


@app.route('/api/incept-plus/improvement/<int:improvement_id>/toggle', methods=['POST'])
@login_required
def api_incept_plus_toggle(improvement_id):
    """Toggle an improvement on/off."""
    data = request.get_json()
    enabled = data.get('enabled', True)
    database.toggle_incept_improvement(improvement_id, enabled)
    return jsonify({'success': True})


@app.route('/api/incept-plus/improvement/<int:improvement_id>/rollback', methods=['POST'])
@login_required
def api_incept_plus_rollback(improvement_id):
    """Rollback an improvement."""
    success, message = incept_plus_tracker.rollback_improvement(improvement_id)
    return jsonify({'success': success, 'message': message})


@app.route('/api/incept-plus/auto-mode/start', methods=['POST'])
@login_required
def api_incept_plus_auto_start():
    """Start auto-mode for a project."""
    data = request.get_json()
    project_id = data.get('project_id')
    direction = data.get('direction', '').strip()

    if not project_id or not direction:
        return jsonify({'success': False, 'error': 'Missing project_id or direction'}), 400

    # Check if there's already an active session for this project
    existing = database.get_active_incept_auto_session(project_id)
    if existing:
        return jsonify({'success': False, 'error': 'Auto-mode already running for this project'}), 400

    session_id = database.start_incept_auto_session(
        project_id,
        direction,
        max_suggestions=data.get('max_suggestions', 10)
    )

    return jsonify({'success': True, 'session_id': session_id})


@app.route('/api/incept-plus/auto-mode/stop/<int:session_id>', methods=['POST'])
@login_required
def api_incept_plus_auto_stop(session_id):
    """Stop auto-mode session."""
    database.update_incept_auto_session(session_id, status='stopped')
    return jsonify({'success': True})


@app.route('/api/incept-plus/auto-mode/status/<int:project_id>')
@login_required
def api_incept_plus_auto_status(project_id):
    """Get auto-mode status for a project."""
    session = database.get_active_incept_auto_session(project_id)
    return jsonify({'success': True, 'session': session})


@app.route('/api/incept-plus/settings/<int:project_id>', methods=['GET', 'POST'])
@login_required
def api_incept_plus_settings(project_id):
    """Get or update Incept+ settings."""
    if request.method == 'POST':
        data = request.get_json()
        database.update_incept_plus_settings(
            project_id,
            auto_mode_enabled=data.get('auto_mode_enabled'),
            auto_mode_interval=data.get('auto_mode_interval'),
            suggestion_model=data.get('suggestion_model'),
            max_list_length=data.get('max_list_length'),
            auto_implement_approved=data.get('auto_implement_approved')
        )
        return jsonify({'success': True})

    settings = database.get_incept_plus_settings(project_id)
    return jsonify({'success': True, 'settings': settings})


# ==================== EMBEDDED PROCESSOR ====================

def _run_embedded_processor():
    """Run the processor in a background thread."""
    global _embedded_processor_running

    print("Starting embedded processor...")

    while _embedded_processor_running:
        try:
            # Check for pending requests across all projects
            pending = database.get_pending_claude_requests()

            if pending:
                print(f"Processing {len(pending)} pending request(s)")
                # Process one at a time
                incept_processor.process_request(pending[0])

            time.sleep(5)  # Poll interval

        except Exception as e:
            print(f"Error in embedded processor: {e}")
            time.sleep(5)

    print("Embedded processor stopped")


def _ensure_embedded_processor():
    """Start embedded processor if enabled and not running."""
    global _embedded_processor_thread, _embedded_processor_running

    if not config.EMBEDDED_PROCESSOR:
        return

    if _embedded_processor_thread is None or not _embedded_processor_thread.is_alive():
        _embedded_processor_running = True
        _embedded_processor_thread = threading.Thread(
            target=_run_embedded_processor,
            daemon=True
        )
        _embedded_processor_thread.start()
        print("Embedded processor started")


@app.route('/api/processor/status')
@login_required
def api_processor_status():
    """Get processor status."""
    return jsonify({
        'success': True,
        'enabled': config.EMBEDDED_PROCESSOR,
        'running': _embedded_processor_running and _embedded_processor_thread and _embedded_processor_thread.is_alive()
    })


# ==================== SYSTEM ROUTES ====================

@app.route('/api/system/logs/<int:project_id>')
@login_required
def api_system_logs(project_id):
    """Get system logs for a project."""
    logs = database.get_system_logs(project_id)
    return jsonify({'success': True, 'logs': logs})


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'})


# ==================== RENDER API MANAGEMENT ====================

@app.route('/api/render/project/<int:project_id>/env-vars')
@login_required
def api_render_get_env_vars(project_id):
    """Get environment variables for a project's Render service."""
    project = database.get_project(project_id)
    if not project or not project.get('render_service_id'):
        return jsonify({'success': False, 'error': 'Project or Render service not found'}), 404

    rm = render_manager.get_render_manager(project.get('render_api_key'))
    success, result = rm.get_env_vars(project['render_service_id'])

    if success:
        return jsonify({'success': True, 'env_vars': result})
    else:
        return jsonify({'success': False, 'error': result}), 500


@app.route('/api/render/project/<int:project_id>/env-vars', methods=['POST'])
@login_required
def api_render_set_env_vars(project_id):
    """Set environment variables for a project's Render service."""
    project = database.get_project(project_id)
    if not project or not project.get('render_service_id'):
        return jsonify({'success': False, 'error': 'Project or Render service not found'}), 404

    data = request.get_json()
    env_vars = data.get('env_vars', {})

    rm = render_manager.get_render_manager(project.get('render_api_key'))
    success, result = rm.set_env_vars(project['render_service_id'], env_vars)

    if success:
        return jsonify({'success': True, 'message': 'Environment variables updated', 'result': result})
    else:
        return jsonify({'success': False, 'error': result}), 500


@app.route('/api/render/project/<int:project_id>/deploy', methods=['POST'])
@login_required
def api_render_trigger_deploy(project_id):
    """Trigger a deploy for a project's Render service."""
    project = database.get_project(project_id)
    if not project or not project.get('render_service_id'):
        return jsonify({'success': False, 'error': 'Project or Render service not found'}), 404

    rm = render_manager.get_render_manager(project.get('render_api_key'))
    success, result = rm.trigger_deploy(project['render_service_id'])

    if success:
        return jsonify({'success': True, 'message': 'Deploy triggered', 'result': result})
    else:
        return jsonify({'success': False, 'error': result}), 500


# ==================== STARTUP ====================

def init():
    """Initialize database and start embedded processor if configured."""
    database.init_db()

    if config.EMBEDDED_PROCESSOR:
        print("Auto-starting embedded processor (EMBEDDED_PROCESSOR=1)")
        _ensure_embedded_processor()


if __name__ == '__main__':
    init()
    app.run(
        host=config.DASHBOARD_HOST,
        port=config.DASHBOARD_PORT,
        debug=True
    )
