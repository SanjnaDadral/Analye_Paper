release: python manage.py migrate --noinput
web: gunicorn paper_analyzer.wsgi:application --workers 1 --timeout 120 --max-requests 1000 --bind 0.0.0.0:$PORT
