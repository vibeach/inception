#!/usr/bin/env python3
"""
Inception Database Module
Multi-project self-improvement system database
"""

import sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager
import config


def utc_now():
    """Get current UTC time for consistent timestamps."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def init_db():
    """Initialize the database with required tables."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Projects table - stores information about managed projects
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                repo_url TEXT NOT NULL,
                repo_branch TEXT DEFAULT 'main',
                github_token TEXT,
                local_path TEXT,
                render_service_id TEXT,
                render_service_url TEXT,
                project_type TEXT,
                status TEXT DEFAULT 'active',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Claude requests table - tracks improvement requests per project
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS claude_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                response TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME,
                mode TEXT DEFAULT 'api',
                model TEXT DEFAULT 'claude-sonnet-4-20250514',
                parent_id INTEGER,
                auto_push BOOLEAN DEFAULT 1,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)

        # Claude log entries table (for detailed progress)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS claude_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER NOT NULL,
                log_type TEXT DEFAULT 'info',
                message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (request_id) REFERENCES claude_requests(id) ON DELETE CASCADE
            )
        """)

        # Incept+ improvement suggestions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS incept_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                implementation_details TEXT,
                category TEXT DEFAULT 'feature',
                priority INTEGER DEFAULT 3,
                status TEXT DEFAULT 'suggested',
                context TEXT,
                estimated_effort TEXT,
                dependencies TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                accepted_at DATETIME,
                rejected_at DATETIME,
                implemented_at DATETIME,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)

        # Incept+ implemented improvements tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS incept_improvements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                suggestion_id INTEGER,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                implementation_summary TEXT,
                commit_hash TEXT,
                files_changed TEXT,
                enabled INTEGER DEFAULT 1,
                feature_flag TEXT,
                rollback_info TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                disabled_at DATETIME,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (suggestion_id) REFERENCES incept_suggestions(id) ON DELETE SET NULL
            )
        """)

        # Incept+ auto-mode sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS incept_auto_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                status TEXT DEFAULT 'running',
                direction TEXT,
                max_suggestions INTEGER DEFAULT 10,
                suggestions_generated INTEGER DEFAULT 0,
                suggestions_implemented INTEGER DEFAULT 0,
                started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                stopped_at DATETIME,
                last_activity_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)

        # Incept settings table (per-project processor settings)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS incept_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL UNIQUE,
                mode TEXT DEFAULT 'api',
                model TEXT DEFAULT 'claude-sonnet-4-20250514',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)

        # Incept+ settings table (per-project Incept+ settings)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS incept_plus_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL UNIQUE,
                auto_mode_enabled INTEGER DEFAULT 0,
                auto_mode_interval INTEGER DEFAULT 300,
                suggestion_model TEXT DEFAULT 'claude-sonnet-4-20250514',
                max_list_length INTEGER DEFAULT 10,
                auto_implement_approved INTEGER DEFAULT 1,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)

        # A/B test tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ab_tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                improvement_id INTEGER NOT NULL,
                test_name TEXT NOT NULL,
                control_commit TEXT NOT NULL,
                variant_commit TEXT NOT NULL,
                control_url TEXT,
                variant_url TEXT,
                status TEXT DEFAULT 'running',
                winner TEXT,
                metrics TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (improvement_id) REFERENCES incept_improvements(id) ON DELETE CASCADE
            )
        """)

        # System logs - comprehensive logging for all activity
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                category TEXT NOT NULL,
                action TEXT NOT NULL,
                status TEXT DEFAULT 'info',
                message TEXT,
                details TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
            )
        """)

        # Create indexes for faster queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_requests_project ON claude_requests(project_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_requests_status ON claude_requests(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_request ON claude_logs(request_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_suggestions_project ON incept_suggestions(project_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_improvements_project ON incept_improvements(project_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_auto_sessions_project ON incept_auto_sessions(project_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_system_logs_project ON system_logs(project_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp)")

        conn.commit()


@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ==================== PROJECTS ====================

def add_project(name, repo_url, description=None, repo_branch='main', github_token=None,
                local_path=None, render_service_id=None, render_service_url=None, project_type=None,
                render_api_key=None):
    """Add a new project to manage."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO projects
            (name, description, repo_url, repo_branch, github_token, local_path,
             render_service_id, render_service_url, project_type, render_api_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, description, repo_url, repo_branch, github_token or config.DEFAULT_GITHUB_TOKEN,
              local_path, render_service_id, render_service_url, project_type,
              render_api_key or config.RENDER_API_KEY))
        conn.commit()
        return cursor.lastrowid


def get_projects(status=None, limit=100):
    """Get all projects, optionally filtered by status."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if status:
            cursor.execute("""
                SELECT * FROM projects
                WHERE status = ?
                ORDER BY name
                LIMIT ?
            """, (status, limit))
        else:
            cursor.execute("""
                SELECT * FROM projects
                ORDER BY name
                LIMIT ?
            """, (limit,))
        return [dict(row) for row in cursor.fetchall()]


def get_project(project_id):
    """Get a single project by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_project_by_name(name):
    """Get a project by name."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE name = ?", (name,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_project(project_id, name=None, description=None, repo_url=None, repo_branch=None,
                   github_token=None, local_path=None, render_service_id=None,
                   render_service_url=None, project_type=None, status=None, render_api_key=None):
    """Update project information."""
    with get_connection() as conn:
        cursor = conn.cursor()
        updates = []
        values = []

        for field, value in [
            ('name', name), ('description', description), ('repo_url', repo_url),
            ('repo_branch', repo_branch), ('github_token', github_token),
            ('local_path', local_path), ('render_service_id', render_service_id),
            ('render_service_url', render_service_url), ('project_type', project_type),
            ('status', status), ('render_api_key', render_api_key)
        ]:
            if value is not None:
                updates.append(f"{field} = ?")
                values.append(value)

        if updates:
            updates.append("updated_at = ?")
            values.append(utc_now())
            values.append(project_id)
            cursor.execute(f"UPDATE projects SET {', '.join(updates)} WHERE id = ?", values)
            conn.commit()


def delete_project(project_id):
    """Delete a project (cascades to all related data)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()


# ==================== CLAUDE REQUESTS ====================

def add_claude_request(project_id, text, mode='api', model='claude-sonnet-4-20250514',
                      parent_id=None, auto_push=True):
    """Add a new request for Claude."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO claude_requests (project_id, text, status, mode, model, parent_id, auto_push)
            VALUES (?, ?, 'pending', ?, ?, ?, ?)
        """, (project_id, text, mode, model, parent_id, 1 if auto_push else 0))
        conn.commit()
        return cursor.lastrowid


def get_claude_requests(project_id=None, limit=50):
    """Get recent Claude requests, optionally filtered by project."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if project_id:
            cursor.execute("""
                SELECT r.*, p.name as project_name
                FROM claude_requests r
                LEFT JOIN projects p ON r.project_id = p.id
                WHERE r.project_id = ?
                ORDER BY r.created_at DESC
                LIMIT ?
            """, (project_id, limit))
        else:
            cursor.execute("""
                SELECT r.*, p.name as project_name
                FROM claude_requests r
                LEFT JOIN projects p ON r.project_id = p.id
                ORDER BY r.created_at DESC
                LIMIT ?
            """, (limit,))
        return [dict(row) for row in cursor.fetchall()]


def get_pending_claude_requests(project_id=None):
    """Get pending Claude requests, optionally filtered by project."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if project_id:
            cursor.execute("""
                SELECT * FROM claude_requests
                WHERE status = 'pending' AND project_id = ?
                ORDER BY created_at ASC
            """, (project_id,))
        else:
            cursor.execute("""
                SELECT * FROM claude_requests
                WHERE status = 'pending'
                ORDER BY created_at ASC
            """)
        return [dict(row) for row in cursor.fetchall()]


def update_claude_request(req_id, status, response=None):
    """Update a Claude request status and response."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE claude_requests
            SET status = ?, response = ?, completed_at = ?
            WHERE id = ?
        """, (status, response, utc_now() if status != 'pending' else None, req_id))
        conn.commit()


def get_claude_request(req_id):
    """Get a single Claude request by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.*, p.name as project_name, p.local_path as project_path
            FROM claude_requests r
            LEFT JOIN projects p ON r.project_id = p.id
            WHERE r.id = ?
        """, (req_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def cancel_claude_request(req_id):
    """Cancel a pending or processing request."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE claude_requests
            SET status = 'cancelled', completed_at = ?
            WHERE id = ? AND status IN ('pending', 'processing')
        """, (utc_now(), req_id))
        conn.commit()
        return cursor.rowcount > 0


def restart_claude_request(req_id, new_text=None, mode=None, model=None, auto_push=None):
    """Restart a request (creates a child request)."""
    req = get_claude_request(req_id)
    if not req:
        return None

    text = new_text if new_text is not None else req['text']
    return add_claude_request(
        req['project_id'],
        text,
        mode=mode if mode is not None else req['mode'],
        model=model if model is not None else req['model'],
        parent_id=req_id,
        auto_push=auto_push if auto_push is not None else bool(req['auto_push'])
    )


def delete_claude_request(req_id):
    """Delete a request and its logs."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM claude_requests WHERE id = ?", (req_id,))
        conn.commit()


# ==================== CLAUDE LOGS ====================

def add_claude_log(request_id, message, log_type='info'):
    """Add a log entry for a Claude request."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO claude_logs (request_id, log_type, message)
            VALUES (?, ?, ?)
        """, (request_id, log_type, message))
        conn.commit()
        return cursor.lastrowid


def get_claude_logs(request_id):
    """Get all log entries for a Claude request."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM claude_logs
            WHERE request_id = ?
            ORDER BY timestamp ASC
        """, (request_id,))
        return [dict(row) for row in cursor.fetchall()]


# ==================== INCEPT SETTINGS ====================

def get_incept_settings(project_id):
    """Get Incept settings for a project."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM incept_settings WHERE project_id = ?
        """, (project_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        # Return defaults if no settings exist
        return {
            'mode': 'api',
            'model': 'claude-sonnet-4-20250514'
        }


def save_incept_settings(project_id, mode, model):
    """Save Incept settings for a project."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO incept_settings
            (project_id, mode, model, updated_at)
            VALUES (?, ?, ?, ?)
        """, (project_id, mode, model, utc_now()))
        conn.commit()


# ==================== INCEPT SUGGESTIONS ====================

def add_incept_suggestion(project_id, title, description, implementation_details,
                         category='feature', priority=3, context=None,
                         estimated_effort=None, dependencies=None):
    """Add a new Incept+ improvement suggestion."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO incept_suggestions
            (project_id, title, description, implementation_details, category, priority,
             context, estimated_effort, dependencies)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (project_id, title, description, implementation_details, category, priority,
              context, estimated_effort, dependencies))
        conn.commit()
        return cursor.lastrowid


def get_incept_suggestions(project_id=None, status=None, category=None, limit=50):
    """Get Incept+ suggestions with optional filtering."""
    with get_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT s.*, p.name as project_name
            FROM incept_suggestions s
            LEFT JOIN projects p ON s.project_id = p.id
        """
        conditions = []
        params = []

        if project_id:
            conditions.append("s.project_id = ?")
            params.append(project_id)
        if status:
            conditions.append("s.status = ?")
            params.append(status)
        if category:
            conditions.append("s.category = ?")
            params.append(category)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY s.priority DESC, s.created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_incept_suggestion(suggestion_id):
    """Get a single Incept+ suggestion by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.*, p.name as project_name
            FROM incept_suggestions s
            LEFT JOIN projects p ON s.project_id = p.id
            WHERE s.id = ?
        """, (suggestion_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_incept_suggestion_status(suggestion_id, status):
    """Update the status of an Incept+ suggestion."""
    with get_connection() as conn:
        cursor = conn.cursor()
        timestamp_field = None
        if status == 'accepted':
            timestamp_field = 'accepted_at'
        elif status == 'rejected':
            timestamp_field = 'rejected_at'
        elif status == 'implemented':
            timestamp_field = 'implemented_at'

        if timestamp_field:
            cursor.execute(f"""
                UPDATE incept_suggestions
                SET status = ?, {timestamp_field} = ?
                WHERE id = ?
            """, (status, utc_now(), suggestion_id))
        else:
            cursor.execute("""
                UPDATE incept_suggestions
                SET status = ?
                WHERE id = ?
            """, (status, suggestion_id))
        conn.commit()


# ==================== INCEPT IMPROVEMENTS ====================

def add_incept_improvement(project_id, title, description, implementation_summary,
                          suggestion_id=None, commit_hash=None, files_changed=None,
                          feature_flag=None, rollback_info=None):
    """Record an implemented improvement."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO incept_improvements
            (project_id, suggestion_id, title, description, implementation_summary,
             commit_hash, files_changed, feature_flag, rollback_info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (project_id, suggestion_id, title, description, implementation_summary,
              commit_hash, files_changed, feature_flag, rollback_info))
        conn.commit()
        return cursor.lastrowid


def get_incept_improvements(project_id=None, enabled_only=False, limit=100):
    """Get implemented improvements."""
    with get_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT i.*, p.name as project_name
            FROM incept_improvements i
            LEFT JOIN projects p ON i.project_id = p.id
        """
        conditions = []
        params = []

        if project_id:
            conditions.append("i.project_id = ?")
            params.append(project_id)
        if enabled_only:
            conditions.append("i.enabled = 1")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY i.created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_incept_improvement(improvement_id):
    """Get a single improvement by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT i.*, p.name as project_name
            FROM incept_improvements i
            LEFT JOIN projects p ON i.project_id = p.id
            WHERE i.id = ?
        """, (improvement_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def toggle_incept_improvement(improvement_id, enabled):
    """Enable or disable an implemented improvement."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE incept_improvements
            SET enabled = ?, disabled_at = ?
            WHERE id = ?
        """, (1 if enabled else 0, None if enabled else utc_now(), improvement_id))
        conn.commit()


# ==================== INCEPT AUTO SESSIONS ====================

def start_incept_auto_session(project_id, direction, max_suggestions=10):
    """Start a new auto-mode session."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO incept_auto_sessions (project_id, direction, max_suggestions)
            VALUES (?, ?, ?)
        """, (project_id, direction, max_suggestions))
        conn.commit()
        return cursor.lastrowid


def update_incept_auto_session(session_id, status=None, suggestions_generated=None,
                               suggestions_implemented=None):
    """Update auto-mode session progress."""
    with get_connection() as conn:
        cursor = conn.cursor()
        updates = []
        params = []

        if status:
            updates.append("status = ?")
            params.append(status)
            if status in ['stopped', 'completed', 'error']:
                updates.append("stopped_at = ?")
                params.append(utc_now())

        if suggestions_generated is not None:
            updates.append("suggestions_generated = ?")
            params.append(suggestions_generated)

        if suggestions_implemented is not None:
            updates.append("suggestions_implemented = ?")
            params.append(suggestions_implemented)

        updates.append("last_activity_at = ?")
        params.append(utc_now())
        params.append(session_id)

        query = f"UPDATE incept_auto_sessions SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()


def get_incept_auto_session(session_id):
    """Get an auto-mode session by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.*, p.name as project_name
            FROM incept_auto_sessions s
            LEFT JOIN projects p ON s.project_id = p.id
            WHERE s.id = ?
        """, (session_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_active_incept_auto_session(project_id=None):
    """Get the currently active auto-mode session if any."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if project_id:
            cursor.execute("""
                SELECT * FROM incept_auto_sessions
                WHERE project_id = ? AND status = 'running'
                ORDER BY started_at DESC
                LIMIT 1
            """, (project_id,))
        else:
            cursor.execute("""
                SELECT * FROM incept_auto_sessions
                WHERE status = 'running'
                ORDER BY started_at DESC
                LIMIT 1
            """)
        row = cursor.fetchone()
        return dict(row) if row else None


# ==================== INCEPT PLUS SETTINGS ====================

def get_incept_plus_settings(project_id):
    """Get Incept+ settings for a project."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM incept_plus_settings WHERE project_id = ?
        """, (project_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        # Return defaults if no settings exist
        return {
            'auto_mode_enabled': 0,
            'auto_mode_interval': 300,
            'suggestion_model': 'claude-sonnet-4-20250514',
            'max_list_length': 10,
            'auto_implement_approved': 1
        }


def update_incept_plus_settings(project_id, auto_mode_enabled=None, auto_mode_interval=None,
                                suggestion_model=None, max_list_length=None,
                                auto_implement_approved=None):
    """Update Incept+ settings for a project."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Get existing settings
        settings = get_incept_plus_settings(project_id)

        # Update with new values
        if auto_mode_enabled is not None:
            settings['auto_mode_enabled'] = auto_mode_enabled
        if auto_mode_interval is not None:
            settings['auto_mode_interval'] = auto_mode_interval
        if suggestion_model is not None:
            settings['suggestion_model'] = suggestion_model
        if max_list_length is not None:
            settings['max_list_length'] = max_list_length
        if auto_implement_approved is not None:
            settings['auto_implement_approved'] = auto_implement_approved

        # Insert or replace
        cursor.execute("""
            DELETE FROM incept_plus_settings WHERE project_id = ?
        """, (project_id,))
        cursor.execute("""
            INSERT INTO incept_plus_settings
            (project_id, auto_mode_enabled, auto_mode_interval, suggestion_model,
             max_list_length, auto_implement_approved, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (project_id, settings['auto_mode_enabled'], settings['auto_mode_interval'],
              settings['suggestion_model'], settings['max_list_length'],
              settings['auto_implement_approved'], utc_now()))
        conn.commit()


# ==================== A/B TESTS ====================

def create_ab_test(project_id, improvement_id, test_name, control_commit, variant_commit,
                  control_url=None, variant_url=None):
    """Create a new A/B test."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ab_tests
            (project_id, improvement_id, test_name, control_commit, variant_commit,
             control_url, variant_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (project_id, improvement_id, test_name, control_commit, variant_commit,
              control_url, variant_url))
        conn.commit()
        return cursor.lastrowid


def get_ab_tests(project_id=None, status=None, limit=50):
    """Get A/B tests with optional filtering."""
    with get_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT t.*, p.name as project_name, i.title as improvement_title
            FROM ab_tests t
            LEFT JOIN projects p ON t.project_id = p.id
            LEFT JOIN incept_improvements i ON t.improvement_id = i.id
        """
        conditions = []
        params = []

        if project_id:
            conditions.append("t.project_id = ?")
            params.append(project_id)
        if status:
            conditions.append("t.status = ?")
            params.append(status)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY t.created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def update_ab_test(test_id, status=None, winner=None, metrics=None):
    """Update A/B test results."""
    with get_connection() as conn:
        cursor = conn.cursor()
        updates = []
        params = []

        if status:
            updates.append("status = ?")
            params.append(status)
            if status == 'completed':
                updates.append("completed_at = ?")
                params.append(utc_now())

        if winner is not None:
            updates.append("winner = ?")
            params.append(winner)

        if metrics is not None:
            updates.append("metrics = ?")
            params.append(metrics)

        if updates:
            params.append(test_id)
            query = f"UPDATE ab_tests SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()


# ==================== SYSTEM LOGS ====================

def add_system_log(category, action, status='info', message=None, details=None, project_id=None):
    """Add a system log entry."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO system_logs
            (project_id, category, action, status, message, details)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (project_id, category, action, status, message, details))
        conn.commit()
        return cursor.lastrowid


def get_system_logs(project_id=None, category=None, limit=100):
    """Get system logs with optional filtering."""
    with get_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM system_logs"
        conditions = []
        params = []

        if project_id:
            conditions.append("project_id = ?")
            params.append(project_id)
        if category:
            conditions.append("category = ?")
            params.append(category)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


# Initialize database on import
init_db()
