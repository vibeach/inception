#!/bin/bash
# Inception Local Startup Script
# This script sets up and starts the Inception dashboard locally

set -e  # Exit on error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "INCEPTION - Local Startup"
echo "=========================================="

# Check if .env exists
if [ ! -f ".env" ]; then
    echo ""
    echo "No .env file found. Running interactive setup..."
    echo ""
    python3 setup_env.py

    if [ ! -f ".env" ]; then
        echo "Error: Setup was cancelled or failed."
        exit 1
    fi
fi

# Load environment variables
echo ""
echo "Loading environment variables from .env..."
set -a  # Export all variables
source .env
set +a

# Verify required variables
REQUIRED_VARS=("ANTHROPIC_API_KEY" "GITHUB_TOKEN" "RENDER_API_KEY" "DASHBOARD_PASSWORD" "SECRET_KEY")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo ""
    echo "Error: Missing required environment variables:"
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Please run: python3 setup_env.py"
    exit 1
fi

echo "✓ All required environment variables loaded"

# Check if Python dependencies are installed
echo ""
echo "Checking Python dependencies..."
if ! python3 -c "import flask" 2>/dev/null; then
    echo "Installing Python dependencies..."
    pip3 install -r requirements.txt
else
    echo "✓ Dependencies already installed"
fi

# Initialize database
echo ""
echo "Initializing database..."
python3 -c "import database; database.init_db()"
echo "✓ Database initialized"

# Check if there are any projects
PROJECT_COUNT=$(sqlite3 inception.db "SELECT COUNT(*) FROM projects;" 2>/dev/null || echo "0")
echo ""
echo "Current projects in database: $PROJECT_COUNT"

if [ "$PROJECT_COUNT" -eq 0 ]; then
    echo ""
    echo "No projects found. You can add projects through the web interface."
fi

# Set local development defaults
export DASHBOARD_HOST=${DASHBOARD_HOST:-"0.0.0.0"}
export DASHBOARD_PORT=${DASHBOARD_PORT:-"5000"}
export EMBEDDED_PROCESSOR=${EMBEDDED_PROCESSOR:-"1"}

echo ""
echo "=========================================="
echo "Starting Inception Dashboard"
echo "=========================================="
echo ""
echo "Dashboard URL: http://localhost:${DASHBOARD_PORT}"
echo "Password: (from DASHBOARD_PASSWORD)"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start the dashboard
python3 dashboard.py
