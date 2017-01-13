web: newrelic-admin run-program gunicorn eleos.wsgi --log-file -
worker: celery worker --app=eleos -E --loglevel=info
