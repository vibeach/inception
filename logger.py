#!/usr/bin/env python3
"""
Comprehensive Logging System
Logs to both database and files for debugging and monitoring.
"""

import os
import sys
import traceback
from datetime import datetime
from functools import wraps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import database


class InceptionLogger:
    """Centralized logging for all Inception operations."""

    def __init__(self):
        """Initialize logger with file and database support."""
        # Create logs directory
        self.log_dir = os.path.join(config.DATA_DIR, 'logs')
        os.makedirs(self.log_dir, exist_ok=True)

        # Main log file
        self.main_log_file = os.path.join(self.log_dir, 'inception.log')

        # Separate log files for different categories
        self.auth_log_file = os.path.join(self.log_dir, 'auth.log')
        self.api_log_file = os.path.join(self.log_dir, 'api.log')
        self.error_log_file = os.path.join(self.log_dir, 'errors.log')

    def _write_to_file(self, log_file, message):
        """Write log message to file."""
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(message + '\n')
        except Exception as e:
            print(f"Failed to write to log file: {e}", file=sys.stderr)

    def _format_message(self, level, category, message, details=None):
        """Format log message with timestamp and details."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

        level_markers = {
            'debug': '🔍',
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌',
            'critical': '🚨'
        }
        marker = level_markers.get(level, '•')

        formatted = f"[{timestamp}] {marker} [{level.upper()}] [{category}] {message}"

        if details:
            if isinstance(details, dict):
                formatted += f"\n    Details: {details}"
            else:
                formatted += f"\n    {details}"

        return formatted

    def log(self, level, category, message, details=None, project_id=None, user=None):
        """
        Log message to both database and files.

        Args:
            level: debug, info, success, warning, error, critical
            category: auth, api, project, incept, render, system, etc.
            message: Log message
            details: Additional details (dict or string)
            project_id: Related project ID (optional)
            user: Username (optional)
        """
        # Format message
        formatted = self._format_message(level, category, message, details)

        # Write to main log file
        self._write_to_file(self.main_log_file, formatted)

        # Write to category-specific log file
        if category == 'auth':
            self._write_to_file(self.auth_log_file, formatted)
        elif category in ['api', 'render']:
            self._write_to_file(self.api_log_file, formatted)

        # Write errors to error log
        if level in ['error', 'critical']:
            self._write_to_file(self.error_log_file, formatted)

        # Write to database
        try:
            database.add_system_log(
                category=category,
                action=message,
                status=level,
                details=str(details) if details else None,
                project_id=project_id
            )
        except Exception as e:
            print(f"Failed to write to database: {e}", file=sys.stderr)

        # Print to console for immediate visibility
        if level in ['error', 'critical', 'warning']:
            print(formatted, file=sys.stderr)
        elif os.getenv('DEBUG'):
            print(formatted)

    def debug(self, category, message, **kwargs):
        """Log debug message."""
        self.log('debug', category, message, **kwargs)

    def info(self, category, message, **kwargs):
        """Log info message."""
        self.log('info', category, message, **kwargs)

    def success(self, category, message, **kwargs):
        """Log success message."""
        self.log('success', category, message, **kwargs)

    def warning(self, category, message, **kwargs):
        """Log warning message."""
        self.log('warning', category, message, **kwargs)

    def error(self, category, message, **kwargs):
        """Log error message."""
        self.log('error', category, message, **kwargs)

    def critical(self, category, message, **kwargs):
        """Log critical message."""
        self.log('critical', category, message, **kwargs)

    def log_exception(self, category, message, exc=None, **kwargs):
        """Log exception with full traceback."""
        if exc is None:
            exc = sys.exc_info()[1]

        tb = traceback.format_exc() if exc else None

        self.log(
            'error',
            category,
            f"{message}: {exc}",
            details=tb,
            **kwargs
        )

    def log_request(self, method, path, status_code, user=None, duration_ms=None, **kwargs):
        """Log HTTP request."""
        details = {
            'method': method,
            'path': path,
            'status_code': status_code,
            'user': user,
            'duration_ms': duration_ms
        }
        details.update(kwargs)

        level = 'info' if status_code < 400 else 'error'
        self.log(level, 'api', f"{method} {path} -> {status_code}", details=details)


# Global logger instance
logger = InceptionLogger()


def log_function_call(category='system'):
    """Decorator to log function calls with arguments and results."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.debug(
                category,
                f"Calling {func_name}",
                details={'args': str(args)[:200], 'kwargs': str(kwargs)[:200]}
            )

            try:
                result = func(*args, **kwargs)
                logger.debug(category, f"Completed {func_name}")
                return result
            except Exception as e:
                logger.log_exception(category, f"Error in {func_name}", exc=e)
                raise

        return wrapper
    return decorator
