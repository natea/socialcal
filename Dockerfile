FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
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

# Install Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Create and switch to a non-root user
RUN useradd -m -s /bin/bash app
RUN mkdir -p /app /app/staticfiles /app/media
RUN chown -R app:app /app

# Set up app directory
WORKDIR /app

# Set environment variables
ENV PATH="/home/app/.local/bin:${PATH}"
ENV PYTHONPATH="/home/app/.local/lib/python3.11/site-packages:${PYTHONPATH}"

# Switch to non-root user
USER app

# Install Python dependencies
COPY --chown=app:app requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Copy project
COPY --chown=app:app . .

# Create a script to run startup commands
RUN echo '#!/bin/bash\n\
export PATH="/home/app/.local/bin:$PATH"\n\
python manage.py collectstatic --no-input\n\
python manage.py migrate\n\
exec gunicorn socialcal.wsgi:application \
    --bind=0.0.0.0:$PORT \
    --workers=2 \
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