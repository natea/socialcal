# Build stage
FROM python:3.11-slim as builder

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

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

# Install Crawl4AI setup and browsers
RUN crawl4ai-setup

# Final stage
FROM python:3.11-slim

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    xvfb \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DISPLAY=:99 \
    DBUS_SESSION_BUS_ADDRESS=/dev/null

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Create and switch to a non-root user
RUN useradd -m -s /bin/bash app
RUN mkdir -p /app /app/staticfiles /app/media
RUN chown -R app:app /app

# Copy Crawl4AI and Playwright data to app user's home
RUN mkdir -p /home/app/.crawl4ai /home/app/.cache && \
    cp -r /root/.crawl4ai/* /home/app/.crawl4ai/ && \
    cp -r /root/.cache/ms-playwright /home/app/.cache/ && \
    chown -R app:app /home/app/.crawl4ai /home/app/.cache

# Set up X11 directories with proper permissions
RUN mkdir -p /tmp/.X11-unix && \
    chmod 1777 /tmp/.X11-unix

# Copy project files
COPY --chown=app:app . .

# Run migrations and collect static files
RUN python manage.py collectstatic --noinput
RUN python manage.py migrate

# Create a script to run startup commands
RUN echo '#!/bin/bash\n\
Xvfb :99 -ac -screen 0 1280x1024x24 -nolisten tcp &\n\
sleep 2\n\
exec gunicorn socialcal.wsgi:application \
    --bind=0.0.0.0:$PORT \
    --workers=$WEB_CONCURRENCY \
    --threads=2 \
    --worker-class=gthread \
    --worker-tmp-dir=/dev/shm \
    --timeout=30 \
    --keep-alive=2 \
    --log-file=- \
    --access-logfile=- \
    --error-logfile=- \
    --log-level=info\n'\
> /app/start.sh && chmod +x /app/start.sh

# Switch to non-root user
USER app

# Set the default command
CMD ["/app/start.sh"]