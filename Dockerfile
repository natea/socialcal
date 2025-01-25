# Build stage
FROM python:3.11-slim as builder

# Install build dependencies with caching
RUN rm -f /etc/apt/apt.conf.d/docker-clean && \
    echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y \
    gcc \
    python3-dev

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Configure pip to use Render's PyPI mirror and caching
RUN pip config set global.index-url https://pypi.render.com/simple/ \
    && pip config set global.trusted-host pypi.render.com \
    && pip config set global.cache-dir /opt/pip-cache

# Install Python dependencies
COPY requirements.txt .
RUN --mount=type=cache,target=/opt/pip-cache \
    pip install --no-cache-dir -r requirements.txt

# Install Crawl4AI setup and browsers
RUN crawl4ai-setup

# Final stage
FROM python:3.11-slim

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy Crawl4AI and Playwright data from builder
COPY --from=builder /root/.crawl4ai /root/.crawl4ai
COPY --from=builder /root/.cache/ms-playwright /root/.cache/ms-playwright

# Install system dependencies with caching
RUN rm -f /etc/apt/apt.conf.d/docker-clean && \
    echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y \
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
    gnupg

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

# Set up app directory
WORKDIR /app

# Set environment variables
ENV PATH="/opt/venv/bin:${PATH}"
ENV PYTHONPATH="/opt/venv/lib/python3.11/site-packages:${PYTHONPATH}"
ENV DISPLAY=:99
ENV PYTHONUNBUFFERED=1
ENV DBUS_SESSION_BUS_ADDRESS=/dev/null

# Switch to non-root user
USER app

# Copy project
COPY --chown=app:app . .

# Create a script to run startup commands
RUN echo '#!/bin/bash\n\
Xvfb :99 -ac -screen 0 1280x1024x24 -nolisten tcp &\n\
sleep 2\n\
python manage.py collectstatic --no-input\n\
python manage.py migrate\n\
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

# Run the startup script
CMD ["/app/start.sh"]