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
RUN mkdir -p /app/staticfiles /app/media /app/static && \
    chown -R app:app /app && \
    chmod -R 755 /app/staticfiles /app/static

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

# Ensure static files directory has proper permissions
RUN chmod -R 755 /app/static /app/staticfiles

# Switch to app user for remaining operations
USER app

# Copy entrypoint script
COPY --chown=app:app docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Set the default command
CMD ["/app/docker-entrypoint.sh"]