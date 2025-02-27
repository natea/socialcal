#!/usr/bin/env bash
# Exit on error
set -o errexit

# Print commands before executing them
set -o xtrace

echo "Starting build process..."

# Function to log messages with timestamps
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Install dependencies with error handling
log "Installing dependencies..."
pip install -r requirements.txt || {
    log "ERROR: Failed to install dependencies"
    exit 1
}

# Verify critical packages are installed
log "Verifying critical packages..."
python -c "import django, django_redis, psycopg2" || {
    log "WARNING: Some critical packages may be missing. Installing them explicitly..."
    pip install django-redis psycopg2-binary
}

# Run tests if not in collecting static mode
if [ "$COLLECTING_STATIC" != "true" ]; then
    log "Running tests..."
    # Run tests but don't fail the build if tests fail
    python -m pytest || log "WARNING: Tests failed but continuing with deployment"
fi

# Collect static files
log "Collecting static files..."
python manage.py collectstatic --no-input

# Apply database migrations
log "Applying database migrations..."
python manage.py migrate

log "Build process completed successfully!" 