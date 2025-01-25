#!/bin/bash
set -e

# Start Xvfb
Xvfb :99 -ac -screen 0 1280x1024x24 -nolisten tcp &

# Wait for database and check Redis
python << END
import sys
import time
import psycopg2
import os
import dj_database_url
import redis
from urllib.parse import urlparse

# Check database connection
db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("DATABASE_URL not set")
    sys.exit(1)

db_config = dj_database_url.parse(db_url)

for i in range(30):
    try:
        psycopg2.connect(
            dbname=db_config["NAME"],
            user=db_config["USER"],
            password=db_config["PASSWORD"],
            host=db_config["HOST"],
            port=db_config["PORT"],
        )
        print("Database connection successful")
        break
    except psycopg2.OperationalError:
        print("Waiting for database...")
        time.sleep(1)

# Check Redis connection
redis_url = os.getenv("REDIS_URL")
if redis_url:
    try:
        url = urlparse(redis_url)
        r = redis.Redis(
            host=url.hostname,
            port=url.port,
            password=url.password,
            ssl=url.scheme == "rediss",
            socket_timeout=5,
        )
        r.ping()
        print("Redis connection successful")
    except Exception as e:
        print(f"Warning: Redis connection failed - {str(e)}")
else:
    print("Warning: REDIS_URL not set")
END

# Run migrations
python manage.py migrate --noinput

# Create default site
python manage.py shell -c "from django.contrib.sites.models import Site;Site.objects.get_or_create(id=1, defaults={'domain': 'socialcal.onrender.com', 'name': 'SocialCal'})"

# Check OpenAI API key
openai_key="$OPENAI_API_KEY"
if [ -n "$openai_key" ]; then
    echo "OpenAI API key is set (length: ${#openai_key} characters)"
    if [ ${#openai_key} -lt 20 ]; then
        echo "Warning: OpenAI API key seems too short. Please verify it's correct."
    fi
else
    echo "Warning: OpenAI API key is not set. Event extraction will use basic mode."
fi

# Start gunicorn
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
    --log-level=info
