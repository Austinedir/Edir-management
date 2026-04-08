web: gunicorn edir_project.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
worker: celery -A edir_project worker --loglevel=info --concurrency=2
beat: celery -A edir_project beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
