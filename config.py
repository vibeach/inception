#!/usr/bin/env python3
"""
Inception Configuration
Multi-project self-improvement system
"""

import os

# Persistent data directory (use /data on Render, local dir otherwise)
DATA_DIR = os.getenv("DATA_DIR", os.path.dirname(__file__))

# Database path
DATABASE_PATH = os.path.join(DATA_DIR, "inception.db")

# Dashboard settings
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "change-me-in-production")
DASHBOARD_HOST = os.getenv("DASHBOARD_HOST", "0.0.0.0")
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "5000"))
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")

# AI API settings (Claude API)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_CODE_OAUTH_TOKEN = os.getenv("CLAUDE_CODE_OAUTH_TOKEN", "")

# GitHub settings (for git operations)
DEFAULT_GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# Render API settings (for managing deployments)
RENDER_API_KEY = os.getenv("RENDER_API_KEY", "")
RENDER_OWNER_ID = os.getenv("RENDER_OWNER_ID", "")
RENDER_SERVICE_ID = os.getenv("RENDER_SERVICE_ID", "")

# Embedded processor (auto-start processor in dashboard process)
EMBEDDED_PROCESSOR = os.getenv("EMBEDDED_PROCESSOR", "1" if os.getenv("RENDER") else "0") == "1"
