# Build stage
FROM python:3.11-slim as builder

# Install system dependencies required for building Python packages
RUN DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -y \
    build-essential \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# Copy requirements
COPY requirements.txt .

# Install dependencies with caching
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Install and setup Crawl4AI in builder stage
RUN pip install crawl4ai && \
    mkdir -p /root/.crawl4ai && \
    crawl4ai-setup

# Start new stage for runtime
FROM python:3.11-slim

# Install runtime system dependencies
RUN DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -y \
    libpq-dev \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libx11-6 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libxshmfence1 \
    xvfb \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Create and switch to a non-root user
RUN useradd -m -s /bin/bash app

# Set work directory and create necessary directories
WORKDIR /app
RUN mkdir -p /app/staticfiles /app/media && \
    chown -R app:app /app

# Create virtual environment
COPY --from=builder /opt/venv /opt/venv

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DISPLAY=:99 \
    DBUS_SESSION_BUS_ADDRESS=/dev/null \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=socialcal.settings.production

# Create necessary directories for app user
RUN mkdir -p /home/app/.crawl4ai /home/app/.cache/ms-playwright && \
    chown -R app:app /home/app

# Copy Crawl4AI data from builder
COPY --from=builder --chown=app:app /root/.crawl4ai/ /home/app/.crawl4ai/
COPY --from=builder --chown=app:app /root/.cache/ms-playwright/ /home/app/.cache/ms-playwright/

# Set up X11 directory
USER root
RUN mkdir -p /tmp/.X11-unix && \
    chmod 1777 /tmp/.X11-unix

# Copy project files and set permissions
COPY --chown=app:app . .

# Switch to app user for remaining operations
USER app

# Create initialization script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Start Xvfb\n\
Xvfb :99 -ac -screen 0 1280x1024x24 -nolisten tcp &\n\
\n\
# Wait for database\n\
python << END\n\
import sys\n\
import time\n\
import psycopg2\n\
import os\n\
import dj_database_url\n\
import redis\n\
from urllib.parse import urlparse\n\
\n\
# Check database connection\n\
db_url = os.getenv("DATABASE_URL")\n\
if not db_url:\n\
    print("DATABASE_URL not set")\n\
    sys.exit(1)\n\
\n\
db_config = dj_database_url.parse(db_url)\n\
\n\
for i in range(30):\n\
    try:\n\
        psycopg2.connect(\n\
            dbname=db_config["NAME"],\n\
            user=db_config["USER"],\n\
            password=db_config["PASSWORD"],\n\
            host=db_config["HOST"],\n\
            port=db_config["PORT"],\n\
        )\n\
        print("Database connection successful")\n\
        break\n\
    except psycopg2.OperationalError:\n\
        print("Waiting for database...")\n\
        time.sleep(1)\n\
\n\
# Check Redis connection\n\
redis_url = os.getenv("REDIS_URL")\n\
if redis_url:\n\
    try:\n\
        url = urlparse(redis_url)\n\
        r = redis.Redis(\n\
            host=url.hostname,\n\
            port=url.port,\n\
            password=url.password,\n\
            ssl=url.scheme == "rediss",\n\
            socket_timeout=5,\n\
        )\n\
        r.ping()\n\
        print("Redis connection successful")\n\
    except Exception as e:\n\
        print(f"Warning: Redis connection failed - {str(e)}")\n\
else:\n\
    print("Warning: REDIS_URL not set")\n\
END\n\
\n\
# Run migrations\n\
python manage.py migrate --noinput\n\
\n\
# Create default site\n\
python manage.py shell -c "\
from django.contrib.sites.models import Site;\
Site.objects.get_or_create(id=1, defaults={\"domain\": \"socialcal.onrender.com\", \"name\": \"SocialCal\"})\
"\n\
\n\
# Check OpenAI API key\n\
if [ -n "$OPENAI_API_KEY" ]; then\n\
    echo "OpenAI API key is set"\n\
else\n\
    echo "Warning: OpenAI API key is not set"\n\
fi\n\
\n\
# Start gunicorn\n\
exec gunicorn socialcal.wsgi:application \
    --bind=0.0.0.0:$PORT \
    --workers=${WEB_CONCURRENCY:-4} \
    --threads=4 \
    --worker-class=gthread \
    --worker-tmp-dir=/dev/shm \
    --timeout=120 \
    --log-file=- \
    --access-logfile=- \
    --error-logfile=- \
    --log-level=info\n\
' > /app/start.sh && chmod +x /app/start.sh

# Set the default command
CMD ["/app/start.sh"]