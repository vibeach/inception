#!/bin/bash
# Inception Startup Script for Render

# Set data directory to persistent disk
export DATA_DIR=${DATA_DIR:-/data}

# Create data directory if it doesn't exist
mkdir -p $DATA_DIR

# Initialize database
python -c "import database; database.init_db()"

# Start the Flask app with Gunicorn
# - 2 workers for parallel request handling
# - Embedded processor will run in background thread
# - 120s timeout for long-running Claude API calls
exec gunicorn dashboard:app \
    --bind 0.0.0.0:${PORT:-5000} \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
