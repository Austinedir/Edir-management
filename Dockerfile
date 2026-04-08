FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=edir_project.settings

WORKDIR /app

# System packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc libjpeg-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Create directories
RUN mkdir -p /app/media /app/staticfiles /app/static

# Build-time: make migrations using SQLite (no real DB needed)
RUN SECRET_KEY=build-only-not-real \
    DATABASE_URL=sqlite:////tmp/build.db \
    ALLOWED_HOSTS=* \
    DEBUG=True \
    REDIS_URL="" \
    python manage.py makemigrations --noinput \
    && echo "makemigrations OK"

# Build-time: collect static files
RUN SECRET_KEY=build-only-not-real \
    DATABASE_URL=sqlite:////tmp/build.db \
    ALLOWED_HOSTS=* \
    DEBUG=True \
    REDIS_URL="" \
    python manage.py collectstatic --noinput \
    && echo "collectstatic OK"

EXPOSE 8000

# Start script: migrate (against real DB) then start gunicorn
CMD ["sh", "-c", "\
    echo '=== Running migrations ===' && \
    python manage.py migrate --noinput && \
    echo '=== Starting gunicorn ===' && \
    gunicorn edir_project.wsgi:application \
        --bind 0.0.0.0:${PORT:-8000} \
        --workers 2 \
        --timeout 120 \
        --log-level info \
        --access-logfile - \
        --error-logfile - \
    "]
